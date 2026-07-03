from autoframe.plugins.base import TestModule


class SpringMatrixTestModule(TestModule):
    @property
    def name(self) -> str:
        return "spring_matrix"

    @property
    def description(self) -> str:
        return "Spring Boot matrix testing - one pytest case per controller, route method, service, repository, entity, and Spring concern"
