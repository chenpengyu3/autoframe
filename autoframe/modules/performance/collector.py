import time
import threading
from dataclasses import dataclass, field
from typing import List


@dataclass
class Stats:
    """Statistical summary of collected metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def p99_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[min(index, len(sorted_times) - 1)]

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def requests_per_second(self) -> float:
        if self.total_time == 0:
            return 0.0
        return self.total_requests / self.total_time


@dataclass
class PerformanceResult:
    """Complete performance test result."""
    stats: Stats
    duration: float
    concurrency_level: int
    test_name: str


class PerformanceCollector:
    """Thread-safe performance metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = Stats()
        self._start_time = None
        self._end_time = None

    def record_success(self, response_time: float):
        """Record a successful request."""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.response_times.append(response_time)

    def record_failure(self, error_message: str, response_time: float = 0.0):
        """Record a failed request."""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            self._stats.error_messages.append(error_message)
            if response_time > 0:
                self._stats.response_times.append(response_time)

    def start(self):
        """Mark the start of collection."""
        self._start_time = time.time()

    def finish(self, concurrency_level: int = 1, test_name: str = "") -> PerformanceResult:
        """Finish collection and return results."""
        self._end_time = time.time()
        duration = self._end_time - (self._start_time or self._end_time)
        self._stats.total_time = duration
        return PerformanceResult(
            stats=self._stats,
            duration=duration,
            concurrency_level=concurrency_level,
            test_name=test_name,
        )
