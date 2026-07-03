from autoframe.plugins.base import TestModule


class EnterpriseTestModule(TestModule):
    @property
    def name(self) -> str:
        return "enterprise"

    @property
    def description(self) -> str:
        return "Enterprise checks - scan coverage, API contracts, CORS, observability, upload/download metadata"
