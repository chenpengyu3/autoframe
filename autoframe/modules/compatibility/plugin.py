from autoframe.plugins.base import TestModule


class CompatibilityTestModule(TestModule):
    @property
    def name(self) -> str:
        return "compatibility"

    @property
    def description(self) -> str:
        return "HTTP compatibility testing - HEAD, OPTIONS, content negotiation"
