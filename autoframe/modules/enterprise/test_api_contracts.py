"""Enterprise API contract and protocol checks."""

import pytest

from autoframe.core.client import HttpClient


@pytest.mark.enterprise
class TestApiContracts:
    """Cross-cutting API behavior expected in production services."""

    def test_options_requests_do_not_server_error(self, client: HttpClient, api_test_params):
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No safe runtime endpoints discovered")

        failures = []
        for endpoint in endpoints[:10]:
            path = endpoint["path"]
            try:
                response = client.options(path)
            except Exception as exc:
                failures.append(f"OPTIONS {path}: {type(exc).__name__}: {exc}")
                continue
            if response.status_code >= 500:
                failures.append(f"OPTIONS {path}: {response.status_code}")

        assert not failures, "OPTIONS contract failures:\n" + "\n".join(failures)

    def test_cors_preflight_is_not_dangerously_open(self, client: HttpClient, api_test_params):
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No safe runtime endpoints discovered")

        risky = []
        checked = 0
        for endpoint in endpoints[:10]:
            path = endpoint["path"]
            method = endpoint.get("method", "GET")
            response = client.options(
                path,
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": method,
                },
            )
            if response.status_code >= 500:
                risky.append(f"Preflight {path}: server error {response.status_code}")
                continue

            allow_origin = response.headers.get("access-control-allow-origin", "")
            allow_credentials = response.headers.get("access-control-allow-credentials", "")
            if allow_origin == "*" and allow_credentials.lower() == "true":
                risky.append(f"Preflight {path}: wildcard origin with credentials")
            checked += 1

        if not checked:
            pytest.skip("No CORS preflight responses available")

        assert not risky, "Risky CORS behavior:\n" + "\n".join(risky)

    def test_json_endpoints_declare_reasonable_content_type(self, client: HttpClient, api_test_params):
        endpoints = [
            ep for ep in api_test_params.get("endpoints", [])
            if ep.get("method") == "GET" and ep.get("kind") in (None, "http", "actuator")
        ]
        if not endpoints:
            pytest.skip("No GET endpoints available")

        failures = []
        for endpoint in endpoints[:20]:
            response = client.get(endpoint["path"])
            if response.status_code >= 400:
                continue
            text = response.text.strip()
            content_type = response.headers.get("content-type", "").lower()
            if text.startswith(("{", "[")) and "json" not in content_type:
                failures.append(f"{endpoint['path']}: JSON-looking body has content-type {content_type!r}")

        assert not failures, "Content-Type contract failures:\n" + "\n".join(failures)
