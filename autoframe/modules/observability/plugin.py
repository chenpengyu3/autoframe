from autoframe.plugins.base import TestModule


class ObservabilityTestModule(TestModule):
    @property
    def name(self) -> str:
        return "observability"

    @property
    def description(self) -> str:
        return "Observability testing - health, errors, operational response signals"
