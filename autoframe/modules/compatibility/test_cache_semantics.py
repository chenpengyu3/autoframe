"""HTTP cache and conditional request compatibility tests."""

import pytest

from autoframe.core.client import HttpClient


def _safe_gets(api_test_params, limit: int = 10):
    result = []
    for endpoint in api_test_params.get("endpoints", []):
        if endpoint.get("method") != "GET":
            continue
        path = endpoint.get("path", "")
        if "{" in path or "<" in path:
            continue
        result.append(path)
        if len(result) >= limit:
            break
    return result


@pytest.mark.compatibility
class TestCacheSemantics:
    def test_cache_control_headers_are_parseable_when_present(self, client: HttpClient, api_test_params):
        paths = _safe_gets(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths:
            response = client.get(path)
            value = response.headers.get("cache-control")
            if not value:
                continue
            directives = [part.strip() for part in value.split(",")]
            if any(not directive for directive in directives):
                failures.append(f"GET {path}: malformed Cache-Control '{value}'")

        assert not failures, "Malformed Cache-Control headers:\n" + "\n".join(failures)

    def test_conditional_get_headers_do_not_server_error(self, client: HttpClient, api_test_params):
        paths = _safe_gets(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths:
            response = client.get(path, headers={"If-None-Match": '"autoframe-probe"'})
            if response.status_code >= 500:
                failures.append(f"GET {path} If-None-Match: {response.status_code}")
            response = client.get(path, headers={"If-Modified-Since": "Wed, 21 Oct 2015 07:28:00 GMT"})
            if response.status_code >= 500:
                failures.append(f"GET {path} If-Modified-Since: {response.status_code}")

        assert not failures, "Conditional GET caused server errors:\n" + "\n".join(failures)

    def test_gzip_accept_encoding_does_not_server_error(self, client: HttpClient, api_test_params):
        paths = _safe_gets(api_test_params)
        if not paths:
            pytest.skip("No safe concrete GET endpoints discovered")

        failures = []
        for path in paths:
            response = client.get(path, headers={"Accept-Encoding": "gzip, deflate"})
            if response.status_code >= 500:
                failures.append(f"GET {path}: {response.status_code}")

        assert not failures, "Compressed response negotiation caused server errors:\n" + "\n".join(failures)

