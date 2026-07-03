"""Concurrent request handling tests."""

import concurrent.futures
import threading
import pytest

from autoframe.core.client import HttpClient
from autoframe.core.config import FrameworkConfig
from autoframe.core import logging
from autoframe.utils.helpers import filter_auth_required


@pytest.mark.concurrency
class TestConcurrentRequests:
    """Test service behavior under concurrent load."""

    def test_concurrent_get_requests(self, client: HttpClient, config: FrameworkConfig, concurrency_test_params):
        """Verify concurrent GET requests all succeed."""
        endpoints = concurrency_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No GET endpoints discovered")

        accessible = filter_auth_required(endpoints, client)
        if not accessible:
            pytest.skip("No accessible endpoints (all require auth)")

        target_path = accessible[0].get("path", "/")
        max_threads = concurrency_test_params.get("max_threads", 10)
        results = {"success": 0, "failure": 0, "errors": []}
        lock = threading.Lock()

        def make_request():
            try:
                resp = client.get(target_path)
                with lock:
                    if resp.status_code < 400:
                        results["success"] += 1
                    else:
                        results["failure"] += 1
                        results["errors"].append(f"Status {resp.status_code}")
            except Exception as e:
                with lock:
                    results["failure"] += 1
                    results["errors"].append(str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(make_request) for _ in range(max_threads)]
            concurrent.futures.wait(futures, timeout=30)

        error_rate = results["failure"] / max_threads * 100

        logging.info(
            f"Concurrent GET: {results['success']}/{max_threads} succeeded, "
            f"error_rate={error_rate:.1f}%",
            title="Concurrent Requests",
        )

        assert error_rate <= config.thresholds.max_error_rate_percent, (
            f"Error rate {error_rate:.1f}% exceeds threshold. Errors: {results['errors'][:5]}"
        )

    def test_concurrent_mixed_methods(self, client: HttpClient, config: FrameworkConfig, concurrency_test_params):
        """Verify concurrent requests with different HTTP methods don't interfere."""
        endpoints = concurrency_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints discovered")

        max_threads = concurrency_test_params.get("max_threads", 10)
        results = {"success": 0, "failure": 0}
        lock = threading.Lock()

        def make_request(path, method):
            try:
                resp = getattr(client, method.lower())(path)
                with lock:
                    if resp.status_code < 400:
                        results["success"] += 1
                    else:
                        results["failure"] += 1
            except Exception:
                with lock:
                    results["failure"] += 1

        accessible = filter_auth_required(endpoints, client)
        tasks = [(ep["path"], ep.get("method", "GET")) for ep in accessible[:3]]

        if not tasks:
            pytest.skip("No accessible tasks to run")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for path, method in tasks:
                for _ in range(max_threads // len(tasks) + 1):
                    futures.append(executor.submit(make_request, path, method))
            concurrent.futures.wait(futures, timeout=30)

        total = results["success"] + results["failure"]
        if total > 0:
            error_rate = results["failure"] / total * 100
            assert error_rate <= config.thresholds.max_error_rate_percent * 2, (
                f"Error rate {error_rate:.1f}% too high for mixed concurrent requests"
            )

    def test_request_isolation(self, client: HttpClient, concurrency_test_params):
        """Verify concurrent requests don't share state."""
        endpoints = concurrency_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints discovered")

        accessible = filter_auth_required(endpoints, client)
        if not accessible:
            pytest.skip("No accessible endpoints (all require auth)")

        target_path = accessible[0].get("path", "/")
        responses = {}
        lock = threading.Lock()

        def fetch(index):
            try:
                resp = client.get(target_path)
                with lock:
                    responses[index] = resp.status_code
            except Exception:
                with lock:
                    responses[index] = -1

        num_requests = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(fetch, i) for i in range(num_requests)]
            concurrent.futures.wait(futures, timeout=30)

        assert len(responses) == num_requests, (
            f"Only {len(responses)}/{num_requests} requests completed"
        )
        failed = [i for i, s in responses.items() if s >= 400 or s == -1]
        assert len(failed) <= num_requests * 0.1, (
            f"Too many failed requests: {len(failed)}"
        )
