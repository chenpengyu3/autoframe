import time
import threading

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.modules.performance.collector import PerformanceCollector
from autoframe.utils.helpers import find_accessible_get_endpoint


@pytest.mark.performance
class TestLoad:
    """Sustained load tests."""

    def test_sustained_load(
        self, client: HttpClient, config, api_test_params: dict
    ):
        """Run sustained load for duration_seconds, validate rps and error rate."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        target_path = find_accessible_get_endpoint(client, endpoints)
        if not target_path:
            pytest.skip("No accessible GET endpoints (all require auth or not found)")

        perf_config = config.performance
        duration_seconds = perf_config.load_test.duration_seconds
        concurrency = perf_config.load_test.users
        min_rps = config.thresholds.min_throughput_rps
        max_error_rate = config.thresholds.max_error_rate_percent / 100.0

        collector = PerformanceCollector()
        stop_event = threading.Event()

        def send_request():
            start = time.time()
            try:
                response = client.get(target_path)
                elapsed = time.time() - start
                if response.status_code < 400:
                    collector.record_success(elapsed)
                else:
                    collector.record_failure(
                        f"Status {response.status_code}", elapsed
                    )
            except Exception as e:
                elapsed = time.time() - start
                collector.record_failure(str(e), elapsed)

        def worker():
            while not stop_event.is_set():
                send_request()

        logging.info(
            f"Starting sustained load test: {concurrency} threads, "
            f"{duration_seconds}s duration"
        )
        collector.start()

        threads = []
        for _ in range(concurrency):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)

        time.sleep(duration_seconds)
        stop_event.set()

        for t in threads:
            t.join(timeout=10)

        result = collector.finish(
            concurrency_level=concurrency, test_name="sustained_load"
        )

        logging.info(
            f"Sustained load result: "
            f"total={result.stats.total_requests}, "
            f"rps={result.stats.requests_per_second:.1f}, "
            f"error_rate={result.stats.error_rate:.2%}, "
            f"avg={result.stats.avg_response_time:.3f}s"
        )

        assert result.stats.requests_per_second >= min_rps, (
            f"RPS {result.stats.requests_per_second:.1f} "
            f"below minimum {min_rps}"
        )
        assert result.stats.error_rate <= max_error_rate, (
            f"Error rate {result.stats.error_rate:.2%} "
            f"exceeds threshold {max_error_rate:.2%}"
        )
