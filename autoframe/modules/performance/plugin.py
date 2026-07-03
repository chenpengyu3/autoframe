from autoframe.plugins.base import TestModule


class PerformanceTestModule(TestModule):
    @property
    def name(self) -> str:
        return "performance"

    @property
    def description(self) -> str:
        return "Performance testing - load, stress, response time, throughput"
