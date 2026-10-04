"""FastAPI application composition for the A0 monolith."""

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.routing import Match

from app.api import experiment, health, metrics, notifications, reports, tasks, users
from app.config import get_settings
from app.observability.logging import configure_logging
from app.observability.metrics import (
    business_operation_failures_total,
    business_rule_rejections_total,
    http_request_duration_seconds,
    http_requests_total,
    http_responses_total,
)
from app.observability.tracing import configure_tracing, span
from app.services.errors import BusinessError, ConflictError, InvalidRequestError, NotFoundError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure process-wide structured logging and optional tracing."""
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing()
    yield


app = FastAPI(title="EvoFitBench A0", version=get_settings().app_version, lifespan=lifespan)
app.include_router(users.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(experiment.router)


def classify_traffic(path: str) -> str:
    """Classify a route into a small stable set of traffic categories."""
    if path.startswith("/api/v1/"):
        return "business"
    if path.startswith("/health/") or path == "/metrics":
        return "operational"
    if path.startswith("/internal/experiment/"):
        return "experiment"
    return "unmatched"


def operation_for_request(request: Request) -> str:
    """Resolve a bounded route template even in exception handlers."""
    route = request.scope.get("route")
    if route is not None:
        return _api_path(getattr(route, "path", "unmatched"))
    for candidate in app.routes:
        match, _ = candidate.matches(request.scope)
        if match is Match.FULL:
            return _api_path(getattr(candidate, "path", "unmatched"))
    return "unmatched"


def _api_path(path: str) -> str:
    """Add the public API prefix omitted by nested router route objects."""
    if path.startswith(("/users", "/tasks", "/notifications", "/reports")):
        return f"/api/v1{path}"
    return path


@app.middleware("http")
async def observe_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Add request IDs, HTTP metrics, tracing, and structured access logs."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    status_code = 500
    route_path = "unmatched"
    traffic_class = "unmatched"
    request_path = request.url.path
    try:
        with span("http.request"):
            response = await call_next(request)
            status_code = response.status_code
            route = request.scope.get("route")
            if route is not None:
                route_path = _api_path(getattr(route, "path", route_path))
                traffic_class = classify_traffic(route_path)
            response.headers["X-Request-ID"] = request_id
            return response
    finally:
        duration = time.perf_counter() - started
        http_requests_total.labels(
            method=request.method, path=route_path, traffic_class=traffic_class
        ).inc()
        http_responses_total.labels(
            method=request.method,
            path=route_path,
            status_class=f"{status_code // 100}xx",
            traffic_class=traffic_class,
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method, path=route_path, traffic_class=traffic_class
        ).observe(duration)
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request_path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    """Map expected business errors to the stable JSON error envelope."""
    if isinstance(exc, NotFoundError):
        code, status_code = "not_found", 404
    elif isinstance(exc, ConflictError):
        code, status_code = "conflict", 409
    elif isinstance(exc, InvalidRequestError):
        code, status_code = "invalid_request", 400
    else:
        code, status_code = "business_error", 400
    operation = operation_for_request(request)
    reason = "invalid_transition" if code == "conflict" and "Transition" in str(exc) else code
    if reason not in {"not_found", "conflict", "invalid_transition", "validation"}:
        reason = "validation"
    business_rule_rejections_total.labels(operation=operation, reason=reason).inc()
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": str(exc)}}
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Normalize framework and operational errors into the JSON error envelope."""
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        error = detail
    else:
        error = {"code": "http_error", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation details without internal stack traces."""
    operation = operation_for_request(request)
    business_rule_rejections_total.labels(operation=operation, reason="validation").inc()
    details = [
        {"location": error["loc"], "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": details,
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    """Map remaining database uniqueness/relation conflicts to a safe response."""
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "conflict", "message": "Database constraint conflict"}},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and return a non-sensitive error envelope."""
    logger.exception(
        "Unhandled request failure",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    operation = operation_for_request(request)
    business_operation_failures_total.labels(operation=operation).inc()
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Unexpected server error"}},
    )
