"""Concurrency test module plugin registration."""

from autoframe.plugins.base import TestModule


class ConcurrencyTestModule(TestModule):
    @property
    def name(self) -> str:
        return "concurrency"

    @property
    def description(self) -> str:
        return "Concurrency testing - race conditions, thread safety, concurrent requests"
