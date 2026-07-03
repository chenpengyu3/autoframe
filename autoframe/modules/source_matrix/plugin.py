from autoframe.plugins.base import TestModule


class SourceMatrixTestModule(TestModule):
    @property
    def name(self) -> str:
        return "source_matrix"

    @property
    def description(self) -> str:
        return "Source matrix testing - one pytest case per source file, Java type, route annotation, config property, and dependency"
