"""Test result collector using pytest hooks."""

import inspect
import time
from datetime import datetime
from typing import Optional

import pytest

from autoframe.reporting.models import TestReport, ModuleResult, TestCaseResult, PerformanceMetrics
from autoframe.core.client import metrics as global_metrics


class ReportCollector:
    def __init__(self):
        self.report = TestReport()
        self._current_module: Optional[ModuleResult] = None
        self._module_start_times: dict[str, float] = {}
        self._session_start: float = 0
        self._test_docstrings: dict[str, str] = {}

    def pytest_sessionstart(self, session):
        self.report = TestReport()
        self._current_module = None
        self._module_start_times = {}
        self._test_docstrings = {}
        global_metrics.clear()
        self._session_start = time.perf_counter()
        self.report.start_time = datetime.now()

    def pytest_collection_modifyitems(self, config, items):
        for item in items:
            if hasattr(item, 'obj') and item.obj:
                doc = inspect.getdoc(item.obj)
                if doc:
                    self._test_docstrings[item.nodeid] = doc

    def pytest_runtest_logreport(self, report):
        if report.when not in {"call", "setup"}:
            return

        if report.when == "setup" and not (report.failed or report.skipped):
            return

        module_name = self._extract_module_name(report.nodeid)

        if module_name not in self._module_start_times:
            self._module_start_times[module_name] = time.perf_counter()

        if self._current_module is None or self._current_module.name != module_name:
            if self._current_module and self._current_module.name in self._module_start_times:
                elapsed = (time.perf_counter() - self._module_start_times[self._current_module.name]) * 1000
                self._current_module.duration_ms = elapsed
            self._current_module = ModuleResult(name=module_name)
            self.report.modules.append(self._current_module)

        duration_ms = report.duration * 1000

        if report.skipped:
            status = "skipped"
            self._current_module.skipped += 1
        elif report.failed:
            status = "failed"
            if report.when == "setup":
                status = "error"
                self._current_module.errors += 1
            else:
                self._current_module.failed += 1
        else:
            status = "passed"
            self._current_module.passed += 1

        test_name = report.nodeid.split("::")[-1]
        docstring = self._test_docstrings.get(report.nodeid, "")

        test_case = TestCaseResult(
            name=test_name, module=module_name, status=status,
            duration_ms=duration_ms, description=docstring,
        )

        if report.failed and report.longreprtext:
            test_case.error_message = report.longreprtext[:500]
            test_case.error_traceback = report.longreprtext

        self._current_module.test_cases.append(test_case)

    def pytest_sessionfinish(self, session, exitstatus):
        elapsed = (time.perf_counter() - self._session_start) * 1000
        self.report.end_time = datetime.now()
        self.report.total_duration_ms = elapsed

        if self._current_module and self._current_module.name in self._module_start_times:
            mod_elapsed = (time.perf_counter() - self._module_start_times[self._current_module.name]) * 1000
            self._current_module.duration_ms = mod_elapsed

        if global_metrics.records:
            times = [r.elapsed_ms for r in global_metrics.records]
            timestamps = [r.timestamp for r in global_metrics.records]
            time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
            rps = global_metrics.count / time_span if time_span > 0 else 0
            self.report.performance = PerformanceMetrics(
                avg_response_time_ms=global_metrics.avg_response_time_ms,
                p50_response_time_ms=global_metrics.p50_response_time_ms,
                p90_response_time_ms=global_metrics.p90_response_time_ms,
                p99_response_time_ms=global_metrics.p99_response_time_ms,
                max_response_time_ms=global_metrics.max_response_time_ms,
                min_response_time_ms=global_metrics.min_response_time_ms,
                total_requests=global_metrics.count,
                requests_per_second=rps,
                error_rate_percent=global_metrics.error_rate,
                response_time_distribution=sorted(times)[:1000],
            )

    def _extract_module_name(self, nodeid: str) -> str:
        parts = nodeid.split("/")
        for i, part in enumerate(parts):
            if part == "modules" and i + 1 < len(parts):
                return parts[i + 1]
        return "unknown"


collector = ReportCollector()
