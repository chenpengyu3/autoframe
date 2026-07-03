from autoframe.plugins.base import TestModule


class ContractTestModule(TestModule):
    @property
    def name(self) -> str:
        return "contract"

    @property
    def description(self) -> str:
        return "Contract testing - OpenAPI presence, operation coverage, response declarations"
