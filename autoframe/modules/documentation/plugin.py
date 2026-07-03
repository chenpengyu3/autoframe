from autoframe.plugins.base import TestModule


class DocumentationTestModule(TestModule):
    @property
    def name(self) -> str:
        return "documentation"

    @property
    def description(self) -> str:
        return "API documentation testing - OpenAPI and Swagger endpoint behavior"
