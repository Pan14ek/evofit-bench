"""Wait for the application's readiness endpoint before starting a workload."""

import argparse
import time

import httpx


def wait_until_ready(base_url: str, timeout_seconds: float = 60.0) -> None:
    """Poll readiness until healthy or raise a useful timeout error."""
    deadline = time.monotonic() + timeout_seconds
    url = f"{base_url.rstrip('/')}/health/ready"
    last_error = "readiness endpoint returned a non-success status"

    with httpx.Client(timeout=2.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
                response.raise_for_status()
                return
            except httpx.HTTPError as error:
                last_error = str(error)
                time.sleep(1.0)

    raise TimeoutError(f"Application did not become ready at {url}: {last_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args()
    wait_until_ready(args.url, args.timeout_seconds)
    print(f"Application is ready at {args.url.rstrip('/')}/health/ready")
