"""Enterprise observability and management endpoint checks."""

import pytest

from autoframe.core.client import HttpClient


SENSITIVE_ACTUATOR_SUFFIXES = (
    "/env",
    "/beans",
    "/configprops",
    "/heapdump",
    "/threaddump",
    "/logfile",
    "/shutdown",
)


@pytest.mark.enterprise
class TestObservability:
    """Health, readiness, and management endpoint safety checks."""

    def test_health_endpoints_do_not_server_error(self, client: HttpClient, discovered_project):
        health_endpoints = discovered_project.health_endpoints or []
        if not health_endpoints:
            pytest.skip("No health-like endpoints discovered")

        failures = []
        for path in health_endpoints[:10]:
            response = client.get(path)
            if response.status_code >= 500:
                failures.append(f"GET {path}: {response.status_code}")

        assert not failures, "Health endpoint failures:\n" + "\n".join(failures)

    def test_sensitive_actuator_endpoints_are_not_public(self, client: HttpClient, discovered_endpoints):
        actuator_endpoints = [
            ep for ep in discovered_endpoints
            if ep.kind == "actuator" and ep.methods == ["GET"]
        ]
        sensitive = [
            ep for ep in actuator_endpoints
            if ep.path.lower().endswith(SENSITIVE_ACTUATOR_SUFFIXES)
        ]
        if not sensitive:
            return

        public = []
        for endpoint in sensitive:
            response = client.get(endpoint.path)
            if response.status_code == 200:
                public.append(endpoint.path)

        assert not public, (
            "Sensitive actuator endpoints should not be publicly readable:\n"
            + "\n".join(public)
        )

    def test_trace_headers_are_consistent_when_present(self, client: HttpClient, api_test_params):
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            return

        trace_headers = ("x-request-id", "x-correlation-id", "traceparent")
        seen = []
        for endpoint in endpoints[:10]:
            response = client.get(endpoint["path"])
            present = [h for h in trace_headers if h in response.headers]
            if present:
                seen.extend(present)

        if not seen:
            return

        assert all(header in trace_headers for header in seen)
