"""Path traversal and suspicious file probe tests."""

import pytest

from autoframe.core.client import HttpClient


TRAVERSAL_PAYLOADS = (
    "../etc/passwd",
    "..\\..\\windows\\win.ini",
    "%2e%2e%2fetc%2fpasswd",
)


@pytest.mark.security
class TestPathTraversal:
    def test_path_traversal_query_params_do_not_leak_files(self, client: HttpClient, api_test_params):
        endpoints = [
            endpoint for endpoint in api_test_params.get("endpoints", [])
            if endpoint.get("method") == "GET" and "{" not in endpoint.get("path", "")
        ][:10]
        if not endpoints:
            pytest.skip("No concrete safe GET endpoints discovered")

        failures = []
        leak_markers = ("root:x:", "[fonts]", "boot loader", "for 16-bit app support")
        for endpoint in endpoints:
            for payload in TRAVERSAL_PAYLOADS:
                response = client.get(endpoint["path"], params={"file": payload, "path": payload})
                body = response.text.lower()
                if any(marker in body for marker in leak_markers):
                    failures.append(f"GET {endpoint['path']} leaked file content for {payload}")

        assert not failures, "Path traversal leaks detected:\n" + "\n".join(failures)

    def test_sensitive_static_files_are_not_public(self, client: HttpClient):
        paths = (
            "/.env",
            "/application.properties",
            "/application.yml",
            "/config/application.yml",
            "/WEB-INF/web.xml",
            "/actuator/logfile",
        )
        public = []
        for path in paths:
            response = client.get(path)
            if response.status_code == 200 and any(token in response.text.lower() for token in ("password", "secret", "spring.datasource", "jdbc:")):
                public.append(path)

        assert not public, "Sensitive static/config files are public:\n" + "\n".join(public)

