"""HTTP protocol compatibility tests."""

import pytest

from autoframe.core.client import HttpClient


def _safe_concrete_paths(api_test_params, limit: int = 12) -> list[str]:
    paths = []
    for endpoint in api_test_params.get("endpoints", []):
        if endpoint.get("method") != "GET":
            continue
        path = endpoint.get("path", "")
        if "{" in path or "<" in path:
            continue
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


@pytest.mark.compatibility
class TestHttpSemantics:
    def test_head_on_get_endpoints_no_server_error(self, client: HttpClient, api_test_params):
        paths = _safe_concrete_paths(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths:
            response = client.head(path)
            if response.status_code >= 500:
                failures.append(f"HEAD {path}: {response.status_code}")

        assert not failures, "HEAD requests caused server errors:\n" + "\n".join(failures)

    def test_accept_header_variants_do_not_server_error(self, client: HttpClient, api_test_params):
        paths = _safe_concrete_paths(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths[:8]:
            for accept in ("application/json", "text/plain", "*/*"):
                response = client.get(path, headers={"Accept": accept})
                if response.status_code >= 500:
                    failures.append(f"GET {path} Accept={accept}: {response.status_code}")

        assert not failures, "Accept negotiation caused server errors:\n" + "\n".join(failures)

    def test_options_on_discovered_paths_no_server_error(self, client: HttpClient, api_test_params):
        paths = _safe_concrete_paths(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths:
            response = client.options(path)
            if response.status_code >= 500:
                failures.append(f"OPTIONS {path}: {response.status_code}")

        assert not failures, "OPTIONS requests caused server errors:\n" + "\n".join(failures)
