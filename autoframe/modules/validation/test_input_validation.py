"""Input validation and malformed request tests."""

import pytest

from autoframe.core.client import HttpClient
from autoframe.utils.helpers import dispatch_request


def _concrete_get_endpoints(api_test_params, limit: int = 20):
    endpoints = []
    for endpoint in api_test_params.get("endpoints", []):
        if endpoint.get("method") != "GET":
            continue
        path = endpoint.get("path", "")
        if "{" in path or "<" in path:
            continue
        endpoints.append(endpoint)
        if len(endpoints) >= limit:
            break
    return endpoints


@pytest.mark.validation
class TestInputValidation:
    def test_invalid_query_values_do_not_server_error(self, client: HttpClient, api_test_params):
        endpoints = _concrete_get_endpoints(api_test_params)
        if not endpoints:
            pytest.skip("No concrete safe GET endpoints discovered")

        failures = []
        for endpoint in endpoints:
            response = client.get(
                endpoint["path"],
                params={"__autoframe_invalid": "'\"><invalid>"},
            )
            if response.status_code >= 500:
                failures.append(f"GET {endpoint['path']}: {response.status_code}")

        assert not failures, "Invalid query values caused server errors:\n" + "\n".join(failures)

    def test_templated_id_paths_reject_invalid_ids_cleanly(self, client: HttpClient, discovered_endpoints):
        candidates = []
        for endpoint in discovered_endpoints:
            if "GET" not in endpoint.methods or "{" not in endpoint.path:
                continue
            candidates.append(endpoint)
            if len(candidates) >= 20:
                break
        if not candidates:
            pytest.skip("No templated GET ID endpoints discovered")

        failures = []
        for endpoint in candidates:
            path = endpoint.path
            while "{" in path and "}" in path:
                start = path.index("{")
                end = path.index("}", start)
                path = path[:start] + "not-a-valid-id" + path[end + 1:]
            response = client.get(path)
            if response.status_code >= 500:
                failures.append(f"GET {path}: {response.status_code}")

        assert not failures, "Invalid ID values caused server errors:\n" + "\n".join(failures)

    def test_malformed_json_write_endpoints_do_not_server_error(self, client: HttpClient, discovered_endpoints):
        candidates = []
        for endpoint in discovered_endpoints:
            methods = {m.upper() for m in endpoint.methods}
            if not methods & {"POST", "PUT", "PATCH"}:
                continue
            if "{" in endpoint.path or endpoint.kind != "http":
                continue
            if "application/json" not in endpoint.consumes and not endpoint.request_schema:
                continue
            candidates.append(endpoint)
            if len(candidates) >= 10:
                break
        if not candidates:
            pytest.skip("No JSON write endpoints with reliable request contract discovered")

        failures = []
        for endpoint in candidates:
            method = next(m for m in endpoint.methods if m.upper() in {"POST", "PUT", "PATCH"})
            response = dispatch_request(
                client,
                method,
                endpoint.path,
                content="{ malformed json",
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 500:
                failures.append(f"{method} {endpoint.path}: {response.status_code}")

        assert not failures, "Malformed JSON caused server errors:\n" + "\n".join(failures)
