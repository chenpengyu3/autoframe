import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging


@pytest.mark.fault_tolerance
class TestDegradation:
    """Service degradation tests under stress."""

    def test_service_survives_rapid_requests(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the service survives rapid-fire requests without crashing."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        rapid_requests = fault_test_params.get("rapid_requests", 100)
        target_path = endpoints[0].get("path", "/")

        results = {"success": 0, "failure": 0, "errors": []}
        lock = threading.Lock()

        def rapid_request():
            try:
                response = client.get(target_path)
                with lock:
                    if response.status_code < 500:
                        results["success"] += 1
                    else:
                        results["failure"] += 1
                        results["errors"].append(
                            f"Status {response.status_code}"
                        )
            except Exception as e:
                with lock:
                    results["failure"] += 1
                    results["errors"].append(str(e))

        logging.info(
            f"Sending {rapid_requests} rapid requests to {target_path}"
        )
        start = time.time()

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(rapid_request) for _ in range(rapid_requests)
            ]
            for future in as_completed(futures):
                future.result()

        elapsed = time.time() - start
        success_rate = results["success"] / rapid_requests

        logging.info(
            f"Rapid requests: {results['success']}/{rapid_requests} succeeded "
            f"({success_rate:.1%}) in {elapsed:.2f}s"
        )

        # Service should handle at least 80% of rapid requests
        assert success_rate >= 0.80, (
            f"Service degraded under rapid requests: "
            f"{success_rate:.1%} success rate. "
            f"Errors: {results['errors'][:5]}"
        )

    def test_service_recovers_after_errors(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the service recovers after experiencing errors."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        recovery_wait = fault_test_params.get("recovery_wait_seconds", 5)
        rapid_requests = fault_test_params.get("rapid_requests", 100)
        target_path = endpoints[0].get("path", "/")

        # Phase 1: Send rapid requests to potentially stress the service
        logging.info("Phase 1: Stressing the service with rapid requests")

        def stress_request():
            try:
                client.get(target_path)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(stress_request) for _ in range(rapid_requests)
            ]
            for future in as_completed(futures):
                future.result()

        # Phase 2: Wait for recovery
        logging.info(f"Phase 2: Waiting {recovery_wait}s for recovery")
        time.sleep(recovery_wait)

        # Phase 3: Verify service is still functional
        logging.info("Phase 3: Verifying service recovery")
        recovery_results = []
        for i in range(10):
            try:
                response = client.get(target_path)
                recovery_results.append(response.status_code < 500)
            except Exception:
                recovery_results.append(False)
            time.sleep(0.1)

        recovery_rate = sum(recovery_results) / len(recovery_results)
        logging.info(
            f"Recovery: {sum(recovery_results)}/{len(recovery_results)} "
            f"requests succeeded ({recovery_rate:.1%})"
        )

        assert recovery_rate >= 0.90, (
            f"Service failed to recover after stress: "
            f"{recovery_rate:.1%} success rate"
        )
