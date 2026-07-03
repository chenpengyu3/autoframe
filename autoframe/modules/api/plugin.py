from autoframe.plugins.base import TestModule


class ApiTestModule(TestModule):
    @property
    def name(self) -> str:
        return "api"

    @property
    def description(self) -> str:
        return "API/Functional testing - endpoints, schemas, CRUD operations"
