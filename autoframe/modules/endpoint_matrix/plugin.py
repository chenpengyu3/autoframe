from autoframe.plugins.base import TestModule


class EndpointMatrixTestModule(TestModule):
    @property
    def name(self) -> str:
        return "endpoint_matrix"

    @property
    def description(self) -> str:
        return "Dynamic matrix testing - one pytest case per endpoint, safe GET, special endpoint, and CRUD candidate"
