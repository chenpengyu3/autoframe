"""Runtime observability signal tests."""

import pytest

from autoframe.core.client import HttpClient


@pytest.mark.observability
class TestRuntimeSignals:
    def test_health_endpoints_are_fast_and_stable(self, client: HttpClient, discovered_project):
        health_endpoints = discovered_project.health_endpoints or []
        if not health_endpoints:
            pytest.skip("No health-like endpoints discovered")

        failures = []
        for path in health_endpoints[:10]:
            response = client.get(path)
            elapsed_ms = response.elapsed.total_seconds() * 1000
            if response.status_code >= 500:
                failures.append(f"GET {path}: {response.status_code}")
            if elapsed_ms > 3000:
                failures.append(f"GET {path}: slow health response {elapsed_ms:.1f}ms")

        assert not failures, "Health endpoint signal failures:\n" + "\n".join(failures)

    def test_operational_headers_do_not_leak_sensitive_values(self, client: HttpClient, api_test_params):
        endpoints = [
            endpoint for endpoint in api_test_params.get("endpoints", [])
            if endpoint.get("method") == "GET" and "{" not in endpoint.get("path", "")
        ]
        if not endpoints:
            pytest.skip("No concrete safe GET endpoints discovered")

        sensitive_tokens = ("password", "secret", "token=", "jdbc:", "mysql://", "postgres://")
        failures = []
        for endpoint in endpoints[:10]:
            response = client.get(endpoint["path"])
            header_text = " ".join(f"{k}: {v}" for k, v in response.headers.items()).lower()
            if any(token in header_text for token in sensitive_tokens):
                failures.append(f"GET {endpoint['path']}: sensitive-looking header value")

        assert not failures, "Sensitive operational header leakage:\n" + "\n".join(failures)

    def test_error_response_shape_is_stable(self, client: HttpClient):
        response = client.get("/__autoframe_nonexistent_path__")
        assert response.status_code in (400, 401, 403, 404, 405), (
            f"Expected stable client error for unknown path, got {response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert "text/html" not in content_type or len(response.text) < 5000, (
            "Unknown path returned a large HTML error page"
        )
