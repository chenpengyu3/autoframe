from autoframe.plugins.base import TestModule


class ValidationTestModule(TestModule):
    @property
    def name(self) -> str:
        return "validation"

    @property
    def description(self) -> str:
        return "Input validation testing - invalid params, malformed IDs, malformed JSON"
