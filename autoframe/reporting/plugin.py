"""Pytest plugin for report collection."""

from autoframe.reporting.collector import collector


def pytest_configure(config):
    config.pluginmanager.register(collector, "autoframe_report_collector")
