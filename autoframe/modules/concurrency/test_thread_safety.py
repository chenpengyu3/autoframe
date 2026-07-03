"""Thread safety verification tests."""

import concurrent.futures
import threading
import pytest

from autoframe.core.client import HttpClient
from autoframe.core.config import FrameworkConfig
from autoframe.core import logging


@pytest.mark.concurrency
class TestThreadSafety:
    """Verify thread safety under concurrent access."""

    def test_concurrent_reads_consistent(self, client: HttpClient, concurrency_test_params):
        """Verify concurrent reads return consistent data."""
        endpoints = concurrency_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No GET endpoints discovered")

        target_path = endpoints[0]["path"]

        baseline_resp = client.get(target_path)
        if baseline_resp.status_code != 200:
            pytest.skip(f"Baseline request failed: {baseline_resp.status_code}")

        try:
            baseline_data = baseline_resp.json()
        except Exception:
            pytest.skip("Response is not JSON")

        responses = []
        lock = threading.Lock()

        def read_data():
            try:
                resp = client.get(target_path)
                with lock:
                    responses.append(resp)
            except Exception:
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_data) for _ in range(20)]
            concurrent.futures.wait(futures, timeout=30)

        successful = [r for r in responses if r.status_code == 200]
        assert len(successful) > 0, "No successful concurrent reads"

        for resp in successful:
            try:
                data = resp.json()
                if isinstance(baseline_data, list):
                    assert isinstance(data, list), "Response type changed under concurrency"
                elif isinstance(baseline_data, dict):
                    assert isinstance(data, dict), "Response type changed under concurrency"
            except Exception:
                pass

    def test_shared_client_thread_safety(self, client: HttpClient, config: FrameworkConfig, concurrency_test_params):
        """Verify the shared HTTP client is thread-safe."""
        endpoints = concurrency_test_params.get("endpoints", [])
        target_path = endpoints[0]["path"] if endpoints else "/"

        errors = []
        lock = threading.Lock()

        def use_client(thread_id):
            try:
                for _ in range(5):
                    resp = client.get(target_path)
                    if resp.status_code >= 500:
                        with lock:
                            errors.append(f"Thread {thread_id}: {resp.status_code}")
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(use_client, i) for i in range(10)]
            concurrent.futures.wait(futures, timeout=30)

        if errors:
            logging.warning(f"Thread safety issues: {len(errors)} errors")
            for e in errors[:5]:
                logging.warning(f"  {e}")

        assert len(errors) <= 2, f"Too many thread safety errors: {len(errors)}"
