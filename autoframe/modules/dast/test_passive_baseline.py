"""Passive dynamic security baseline checks."""

import re

import pytest

from autoframe.core.client import HttpClient


DEBUG_PATHS = (
    "/actuator/env",
    "/actuator/heapdump",
    "/actuator/threaddump",
    "/actuator/configprops",
    "/actuator/beans",
    "/env",
    "/debug",
    "/trace",
    "/metrics",
    "/server-status",
)

STACK_TRACE_PATTERNS = (
    "java.lang.",
    "org.springframework.",
    "traceback (most recent call last)",
    "stacktrace",
    "exception:",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|secret|access[_-]?token|refresh[_-]?token)\s*[:=]\s*['\"]?[^'\"\s,}]{8,}"),
    re.compile(r"(?i)jdbc:[a-z]+://"),
    re.compile(r"(?i)mysql://|postgres://|mongodb://"),
)


@pytest.mark.dast
class TestPassiveBaseline:
    def test_common_debug_endpoints_are_not_public(self, client: HttpClient):
        public = []
        for path in DEBUG_PATHS:
            response = client.get(path)
            if response.status_code == 200:
                public.append(path)

        assert not public, "Debug/management endpoints are publicly readable:\n" + "\n".join(public)

    def test_error_pages_do_not_expose_stack_traces(self, client: HttpClient):
        probes = (
            "/__autoframe_error_probe__",
            "/api/__autoframe_error_probe__",
            "/api/users/not-a-valid-id",
        )
        failures = []
        for path in probes:
            response = client.get(path)
            body = response.text.lower()
            if any(pattern in body for pattern in STACK_TRACE_PATTERNS):
                failures.append(f"GET {path}: stack trace pattern exposed")

        assert not failures, "Stack traces exposed in error responses:\n" + "\n".join(failures)

    def test_public_responses_do_not_expose_secret_patterns(self, client: HttpClient, api_test_params):
        endpoints = [
            endpoint for endpoint in api_test_params.get("endpoints", [])
            if endpoint.get("method") == "GET" and "{" not in endpoint.get("path", "")
        ]
        if not endpoints:
            pytest.skip("No concrete public/safe GET endpoints discovered")

        failures = []
        for endpoint in endpoints[:20]:
            response = client.get(endpoint["path"])
            if response.status_code >= 400:
                continue
            text = response.text[:20000]
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                failures.append(f"GET {endpoint['path']}: sensitive pattern exposed")

        assert not failures, "Sensitive values exposed in responses:\n" + "\n".join(failures)
