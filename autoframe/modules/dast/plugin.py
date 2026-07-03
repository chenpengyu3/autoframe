from autoframe.plugins.base import TestModule


class DastTestModule(TestModule):
    @property
    def name(self) -> str:
        return "dast"

    @property
    def description(self) -> str:
        return "Passive DAST baseline - debug endpoints, stack traces, sensitive response leakage"
