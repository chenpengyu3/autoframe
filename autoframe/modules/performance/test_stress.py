import time
import threading

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging
from autoframe.modules.performance.collector import PerformanceCollector
from autoframe.utils.helpers import find_accessible_get_endpoint


@pytest.mark.performance
class TestStress:
    """Staged stress tests - gradually increase load."""

    def test_staged_stress(
        self, client: HttpClient, config, api_test_params: dict
    ):
        """Gradually increase concurrent users per stage and measure degradation."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        target_path = find_accessible_get_endpoint(client, endpoints)
        if not target_path:
            pytest.skip("No accessible GET endpoints (all require auth or not found)")

        perf_config = config.performance
        stages = perf_config.stress_test.stages
        stage_duration = perf_config.stress_test.step_duration_seconds
        max_error_rate = config.thresholds.max_error_rate_percent / 100.0

        stage_results = []

        for num_users in stages:
            logging.info(f"Stress stage: {num_users} concurrent users")
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

            collector.start()
            threads = []
            for _ in range(num_users):
                t = threading.Thread(target=worker)
                t.start()
                threads.append(t)

            time.sleep(stage_duration)
            stop_event.set()

            for t in threads:
                t.join(timeout=10)

            result = collector.finish(
                concurrency_level=num_users, test_name=f"stress_{num_users}_users"
            )
            stage_results.append(result)

            logging.info(
                f"  Stage {num_users} users: "
                f"rps={result.stats.requests_per_second:.1f}, "
                f"avg={result.stats.avg_response_time:.3f}s, "
                f"error_rate={result.stats.error_rate:.2%}"
            )

        # Validate that the system doesn't completely break under stress
        for result in stage_results:
            assert result.stats.error_rate <= max_error_rate, (
                f"Stage {result.concurrency_level} users: error rate "
                f"{result.stats.error_rate:.2%} exceeds threshold "
                f"{max_error_rate:.2%}"
            )

        # Check for graceful degradation
        if len(stage_results) >= 2:
            first_error_rate = stage_results[0].stats.error_rate
            last_error_rate = stage_results[-1].stats.error_rate
            if first_error_rate > 0:
                degradation_ratio = last_error_rate / max(first_error_rate, 0.001)
                logging.info(
                    f"Degradation ratio (last/first error rate): "
                    f"{degradation_ratio:.2f}"
                )
