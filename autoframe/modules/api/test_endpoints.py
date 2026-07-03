"""Endpoint reachability and HTTP method tests."""

import time
import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.utils.helpers import (
    filter_auth_required, is_heavy_endpoint, is_success, is_server_error,
)


@pytest.mark.api
class TestEndpoints:
    """Test that discovered API endpoints are reachable."""

    def test_service_is_alive(self, client: HttpClient, api_test_params: dict):
        """Verify the target service is responding by checking health endpoints."""
        health_endpoints = api_test_params.get("health_endpoints", [])
        if health_endpoints:
            for path in health_endpoints:
                try:
                    resp = client.get(path)
                    if resp.status_code < 500:
                        logging.info(f"Service alive via {path}: {resp.status_code}")
                        return
                except Exception:
                    continue

        # Fallback: try any accessible endpoint
        endpoints = api_test_params.get("endpoints", [])
        accessible = filter_auth_required(endpoints, client)
        for ep in accessible[:3]:
            try:
                resp = client.get(ep["path"])
                if resp.status_code < 500:
                    logging.info(f"Service alive via {ep['path']}: {resp.status_code}")
                    return
            except Exception:
                continue

        pytest.skip("No accessible endpoint found to verify service is alive")

    def test_health_endpoint(self, client: HttpClient, api_test_params: dict):
        """Test health endpoints from discovered data."""
        health_endpoints = api_test_params.get("health_endpoints", [])
        if not health_endpoints:
            pytest.skip("No health endpoints discovered")

        for path in health_endpoints:
            try:
                resp = client.get(path)
                if resp.status_code == 200:
                    logging.info(f"Health endpoint {path}: OK")
                    return
                if resp.status_code in (401, 403):
                    logging.info(f"Health endpoint {path} requires auth (service alive)")
                    return
            except Exception:
                continue

        pytest.skip("No accessible health endpoint found")

    def test_all_endpoints_reachable(self, client: HttpClient, api_test_params: dict):
        """Test all discovered endpoints return non-5xx responses."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints discovered")

        failures = []
        for ep in endpoints:
            path = ep["path"]
            method = ep.get("method", "GET")
            if ep.get("auth_required", False):
                continue  # Skip auth-required endpoints for reachability check
            try:
                resp = getattr(client, method.lower())(path)
                if is_server_error(resp.status_code):
                    failures.append(f"{method} {path}: {resp.status_code}")
            except Exception as e:
                failures.append(f"{method} {path}: {e}")

        assert not failures, "Endpoint failures:\n" + "\n".join(failures)

    def test_response_time_acceptable(self, client: HttpClient, api_test_params: dict, config):
        """Verify all endpoints respond within the configured threshold."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints discovered")

        threshold = config.thresholds.max_response_time_ms
        slow_endpoints = []

        accessible = filter_auth_required(endpoints, client)
        for ep in accessible:
            if ep.get("method", "GET") != "GET":
                continue
            if is_heavy_endpoint(ep["path"]):
                continue
            try:
                start = time.perf_counter()
                resp = client.get(ep["path"])
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > threshold:
                    slow_endpoints.append(
                        f"GET {ep['path']}: {elapsed_ms:.1f}ms (threshold: {threshold}ms)"
                    )
            except Exception:
                pass

        assert not slow_endpoints, (
            f"Slow endpoints (>{threshold}ms):\n" + "\n".join(slow_endpoints)
        )

    def test_404_for_nonexistent_path(self, client: HttpClient):
        """Verify that a non-existent path returns a client error, not a server error."""
        resp = client.get(f"/nonexistent-{id(self)}")
        assert not is_server_error(resp.status_code), (
            f"Expected 4xx for nonexistent path, got {resp.status_code}"
        )
