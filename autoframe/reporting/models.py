"""Report data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TestCaseResult:
    name: str
    module: str
    status: str
    duration_ms: float = 0.0
    description: str = ""
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None


@dataclass
class ModuleResult:
    name: str
    description: str = ""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    test_cases: list[TestCaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100


@dataclass
class PerformanceMetrics:
    avg_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p90_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    total_requests: int = 0
    requests_per_second: float = 0.0
    error_rate_percent: float = 0.0
    response_time_distribution: list[float] = field(default_factory=list)


@dataclass
class TestReport:
    title: str = "AutoFrame Test Report"
    environment: str = "dev"
    service_name: str = ""
    service_type: str = ""
    service_url: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    modules: list[ModuleResult] = field(default_factory=list)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    @property
    def total_passed(self) -> int:
        return sum(m.passed for m in self.modules)

    @property
    def total_failed(self) -> int:
        return sum(m.failed for m in self.modules)

    @property
    def total_skipped(self) -> int:
        return sum(m.skipped for m in self.modules)

    @property
    def total_errors(self) -> int:
        return sum(m.errors for m in self.modules)

    @property
    def total_tests(self) -> int:
        return sum(m.total for m in self.modules)

    @property
    def overall_pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.total_passed / self.total_tests * 100
