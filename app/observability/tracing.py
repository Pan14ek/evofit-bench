"""Optional OpenTelemetry setup and span helper."""

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.config import get_settings

_configured = False


def configure_tracing() -> None:
    """Configure SDK and OTLP export only when an endpoint is supplied."""
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "evofit-bench"}))
    endpoint = get_settings().otel_exporter_otlp_endpoint
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    _configured = True


@contextmanager
def span(name: str) -> Iterator[None]:
    """Create an OpenTelemetry span without coupling callers to the SDK."""
    with trace.get_tracer("evofit-bench").start_as_current_span(name):
        yield
