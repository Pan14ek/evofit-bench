"""Start Uvicorn from the same environment-backed settings as the application."""

import argparse

import uvicorn

from app.config import get_settings


def run(reload: bool = False) -> None:
    """Run the single A0 process using configured host and port."""
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=reload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true")
    arguments = parser.parse_args()
    run(reload=arguments.reload)
