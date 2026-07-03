"""Response payload size and distribution tests."""

import pytest

from autoframe.core.client import HttpClient
from autoframe.utils.helpers import is_heavy_endpoint


@pytest.mark.performance
class TestPayloadSize:
    def test_non_heavy_responses_are_reasonably_sized(self, client: HttpClient, api_test_params):
        endpoints = [
            endpoint for endpoint in api_test_params.get("endpoints", [])
            if endpoint.get("method") == "GET"
            and "{" not in endpoint.get("path", "")
            and not is_heavy_endpoint(endpoint.get("path", ""))
        ][:20]
        if not endpoints:
            pytest.skip("No non-heavy concrete GET endpoints discovered")

        failures = []
        for endpoint in endpoints:
            response = client.get(endpoint["path"])
            size = len(response.content or b"")
            if size > 2_000_000:
                failures.append(f"GET {endpoint['path']}: {size} bytes")

        assert not failures, "Unexpectedly large non-heavy responses:\n" + "\n".join(failures)

    def test_repeated_light_endpoint_latency_is_stable(self, client: HttpClient, api_test_params):
        endpoint = None
        for candidate in api_test_params.get("endpoints", []):
            path = candidate.get("path", "")
            if candidate.get("method") == "GET" and "{" not in path and not is_heavy_endpoint(path):
                endpoint = candidate
                break
        if not endpoint:
            pytest.skip("No light concrete GET endpoint discovered")

        timings = []
        for _ in range(5):
            response = client.get(endpoint["path"])
            timings.append(response.elapsed.total_seconds() * 1000)

        if min(timings) <= 0:
            pytest.skip("No valid timing data collected")
        assert max(timings) / min(timings) < 20, (
            f"Latency variance too high for {endpoint['path']}: {timings}"
        )

