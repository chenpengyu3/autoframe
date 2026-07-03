from autoframe.plugins.base import TestModule


class FaultToleranceTestModule(TestModule):
    @property
    def name(self) -> str:
        return "fault_tolerance"

    @property
    def description(self) -> str:
        return "Fault tolerance testing - timeouts, degradation, recovery"
