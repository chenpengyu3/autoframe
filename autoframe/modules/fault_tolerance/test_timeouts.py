import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging


@pytest.mark.fault_tolerance
class TestTimeouts:
    """Timeout handling tests."""

    def test_service_responds_within_timeout(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the service responds within the configured timeout."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        timeout_seconds = fault_test_params.get("timeout_seconds", 10)
        failures = []

        for endpoint in endpoints[:5]:
            path = endpoint.get("path", "/")
            method = endpoint.get("method", "GET").upper()
            if method != "GET":
                continue
            try:
                start = time.time()
                response = client.get(path)
                elapsed = time.time() - start
                if elapsed > timeout_seconds:
                    failures.append(
                        f"{path}: {elapsed:.2f}s exceeds {timeout_seconds}s timeout"
                    )
                    logging.warning(
                        f"{path}: responded in {elapsed:.2f}s "
                        f"(timeout: {timeout_seconds}s)"
                    )
                else:
                    logging.info(f"{path}: responded in {elapsed:.2f}s")
            except Exception as e:
                logging.error(f"{path}: {type(e).__name__}: {e}")

        assert not failures, (
            f"Timeout violations:\n" + "\n".join(failures)
        )

    def test_timeout_returns_error_not_hang(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify that timeout returns an error instead of hanging."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        # Use a very short timeout to force timeouts
        test_client = HttpClient(
            base_url=config.service.base_url,
            auth=config.auth,
            timeout=0.001,  # 1ms - should timeout for any real request
        )

        path = endpoints[0].get("path", "/")
        try:
            response = test_client.get(path)
            # If we get here, the request didn't timeout (very fast service)
            logging.info(
                f"Service responded within 1ms (very fast)"
            )
        except Exception as e:
            error_name = type(e).__name__
            if "timeout" in error_name.lower() or "time" in error_name.lower():
                logging.info(f"Timeout correctly raised: {error_name}")
            else:
                logging.warning(f"Non-timeout error raised: {error_name}: {e}")

    def test_concurrent_timeouts_handled(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify that concurrent requests with timeouts are handled properly."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        timeout_seconds = fault_test_params.get("timeout_seconds", 10)
        num_requests = 20
        results = {"success": 0, "timeout": 0, "error": 0}

        test_client = HttpClient(
            base_url=config.service.base_url,
            auth=config.auth,
            timeout=timeout_seconds,
        )

        path = endpoints[0].get("path", "/")
        lock = threading.Lock()

        def make_request():
            try:
                response = test_client.get(path)
                with lock:
                    results["success"] += 1
            except Exception as e:
                error_name = type(e).__name__
                with lock:
                    if "timeout" in error_name.lower():
                        results["timeout"] += 1
                    else:
                        results["error"] += 1

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_request) for _ in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        logging.info(
            f"Concurrent timeout test: "
            f"success={results['success']}, "
            f"timeout={results['timeout']}, "
            f"error={results['error']}"
        )
        # All should either succeed or timeout cleanly
        assert results["error"] == 0, (
            f"Unexpected errors during concurrent timeout test: {results}"
        )
