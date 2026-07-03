import time
import threading

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.modules.performance.collector import PerformanceCollector
from autoframe.utils.helpers import find_accessible_get_endpoint


@pytest.mark.performance
class TestThroughput:
    """Throughput measurement tests."""

    def test_throughput_measurement(
        self, client: HttpClient, config, api_test_params: dict
    ):
        """Measure requests per second over a time window."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        target_path = find_accessible_get_endpoint(client, endpoints)
        if not target_path:
            pytest.skip("No accessible GET endpoints (all require auth or not found)")

        perf_config = config.performance
        concurrency = perf_config.load_test.users
        measurement_duration = perf_config.load_test.duration_seconds
        min_throughput = config.thresholds.min_throughput_rps

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
            f"Starting throughput measurement: {concurrency} threads, "
            f"{measurement_duration}s window"
        )
        collector.start()

        threads = []
        for _ in range(concurrency):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)

        time.sleep(measurement_duration)
        stop_event.set()

        for t in threads:
            t.join(timeout=10)

        result = collector.finish(
            concurrency_level=concurrency, test_name="throughput"
        )

        rps = result.stats.requests_per_second
        logging.info(
            f"Throughput result: {rps:.1f} req/s "
            f"({result.stats.total_requests} requests in "
            f"{result.duration:.1f}s, "
            f"avg_latency={result.stats.avg_response_time:.3f}s, "
            f"p99_latency={result.stats.p99_response_time:.3f}s)"
        )

        assert rps >= min_throughput, (
            f"Throughput {rps:.1f} req/s below minimum {min_throughput} req/s"
        )
