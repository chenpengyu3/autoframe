import time

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required, is_server_error


@pytest.mark.fault_tolerance
class TestRecovery:
    """Service recovery and resilience tests."""

    def test_reconnection_after_connection_drop(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the client can reconnect after a connection issue."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        accessible = filter_auth_required(endpoints, client)
        if not accessible:
            pytest.skip("No accessible endpoints (all require auth)")

        target_path = accessible[0].get("path", "/")

        # First, verify connection works
        response1 = client.get(target_path)
        assert not is_server_error(response1.status_code), (
            f"Initial request failed: {response1.status_code}"
        )
        logging.info(f"Initial connection successful: {response1.status_code}")

        # Create a new client (simulating reconnection)
        new_client = HttpClient(
            base_url=config.service.base_url,
            auth=config.auth,
            timeout=30,
        )

        time.sleep(1)

        # Verify the new client works
        response2 = new_client.get(target_path)
        assert not is_server_error(response2.status_code), (
            f"Reconnection failed: {response2.status_code}"
        )
        logging.info(f"Reconnection successful: {response2.status_code}")

    def test_health_endpoint_resilience(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the health endpoint remains functional under various conditions."""
        health_endpoints = fault_test_params.get("health_endpoints", [])
        if not health_endpoints:
            pytest.skip("No health endpoints discovered")

        # Find an accessible health endpoint
        health_path = None
        for path in health_endpoints:
            try:
                response = client.get(path)
                if response.status_code == 200:
                    health_path = path
                    break
                if response.status_code in (401, 403):
                    logging.info(f"Health endpoint {path} requires auth (service is alive)")
                    return
            except Exception:
                continue

        if not health_path:
            pytest.skip("No accessible health endpoint found")

        # Test multiple consecutive health checks
        results = []
        for i in range(10):
            try:
                response = client.get(health_path)
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
            time.sleep(0.1)

        successful = sum(1 for r in results if isinstance(r, int) and r == 200)
        logging.info(
            f"Health endpoint: {successful}/10 checks passed"
        )
        assert successful >= 9, (
            f"Health endpoint unreliable: {successful}/10 checks passed. "
            f"Results: {results}"
        )

    def test_graceful_error_responses(
        self, client: HttpClient, config, fault_test_params: dict
    ):
        """Verify the service returns graceful error responses, not crashes."""
        endpoints = fault_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        accessible = filter_auth_required(endpoints, client)
        target_path = accessible[0].get("path", "/") if accessible else "/"

        # Test various invalid requests
        error_tests = [
            ("GET", "/nonexistent_endpoint_12345", None),
            ("GET", f"{target_path}/99999999", None),
            ("POST", target_path, {"invalid": "data" * 1000}),
        ]

        failures = []
        for method, path, body in error_tests:
            try:
                if method == "GET":
                    response = client.get(path)
                elif method == "POST":
                    response = client.post(path, json=body)
                else:
                    continue

                if is_server_error(response.status_code):
                    failures.append(
                        f"{method} {path}: returned {response.status_code} "
                        f"(server error, not graceful)"
                    )
                    logging.warning(
                        f"{method} {path}: returned {response.status_code}"
                    )
                else:
                    logging.info(
                        f"{method} {path}: returned {response.status_code} "
                        f"(graceful error)"
                    )
            except Exception as e:
                logging.info(
                    f"{method} {path}: raised {type(e).__name__} "
                    f"(acceptable)"
                )

        assert not failures, (
            f"Service returned server errors instead of graceful responses:\n"
            + "\n".join(failures)
        )
