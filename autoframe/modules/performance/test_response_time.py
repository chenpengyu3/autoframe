import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.modules.performance.collector import PerformanceCollector
from autoframe.utils.helpers import find_accessible_get_endpoint


@pytest.mark.performance
class TestResponseTime:
    """Benchmark response times under concurrent load."""

    def test_response_time_benchmark(
        self, client: HttpClient, config, api_test_params: dict
    ):
        """Send N requests concurrently and validate response time thresholds."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        target_path = find_accessible_get_endpoint(client, endpoints)
        if not target_path:
            pytest.skip("No accessible GET endpoints (all require auth or not found)")

        perf_config = config.performance
        num_requests = perf_config.response_time.sample_size
        concurrency = perf_config.response_time.concurrency
        max_avg_time = config.thresholds.max_response_time_ms / 1000.0
        max_p99_time = config.thresholds.max_p99_latency_ms / 1000.0
        max_error_rate = config.thresholds.max_error_rate_percent / 100.0

        collector = PerformanceCollector()
        collector.start()

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

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(send_request) for _ in range(num_requests)]
            for future in as_completed(futures):
                future.result()

        result = collector.finish(
            concurrency_level=concurrency, test_name="response_time_benchmark"
        )

        logging.info(
            f"Response time benchmark: "
            f"avg={result.stats.avg_response_time:.3f}s, "
            f"p99={result.stats.p99_response_time:.3f}s, "
            f"error_rate={result.stats.error_rate:.2%}, "
            f"rps={result.stats.requests_per_second:.1f}"
        )

        assert result.stats.avg_response_time <= max_avg_time, (
            f"Average response time {result.stats.avg_response_time:.3f}s "
            f"exceeds threshold {max_avg_time}s"
        )
        assert result.stats.p99_response_time <= max_p99_time, (
            f"P99 response time {result.stats.p99_response_time:.3f}s "
            f"exceeds threshold {max_p99_time}s"
        )
        assert result.stats.error_rate <= max_error_rate, (
            f"Error rate {result.stats.error_rate:.2%} "
            f"exceeds threshold {max_error_rate:.2%}"
        )
