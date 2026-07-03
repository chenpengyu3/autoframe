from types import SimpleNamespace

from autoframe.core.client import RequestMetrics, metrics
from autoframe.reporting.collector import ReportCollector


def _report(nodeid: str, when: str, *, failed=False, skipped=False, duration=0.01):
    return SimpleNamespace(
        nodeid=nodeid,
        when=when,
        failed=failed,
        skipped=skipped,
        duration=duration,
        longreprtext="",
    )


def test_collector_does_not_count_successful_setup_as_test_case():
    collector = ReportCollector()
    nodeid = "autoframe/modules/api/test_endpoints.py::TestEndpoints::test_service_is_alive"

    collector.pytest_runtest_logreport(_report(nodeid, "setup"))
    collector.pytest_runtest_logreport(_report(nodeid, "call"))

    assert collector.report.total_tests == 1
    assert collector.report.total_passed == 1
    assert collector.report.modules[0].total == 1


def test_collector_keeps_setup_skip_as_skipped_test_case():
    collector = ReportCollector()
    nodeid = "autoframe/modules/contract/test_openapi_contracts.py::test_spec"

    collector.pytest_runtest_logreport(_report(nodeid, "setup", skipped=True))

    assert collector.report.total_tests == 1
    assert collector.report.total_skipped == 1


def test_collector_resets_state_at_session_start():
    collector = ReportCollector()
    nodeid = "autoframe/modules/api/test_endpoints.py::test_old"
    collector.pytest_runtest_logreport(_report(nodeid, "call"))
    metrics.record(RequestMetrics(method="GET", url="/old", status_code=200, elapsed_ms=1.0))

    collector.pytest_sessionstart(SimpleNamespace())

    assert collector.report.total_tests == 0
    assert collector.report.modules == []
    assert metrics.count == 0
