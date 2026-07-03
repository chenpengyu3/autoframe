from autoframe.plugins.base import TestModule


class DatabaseMatrixTestModule(TestModule):
    @property
    def name(self) -> str:
        return "database_matrix"

    @property
    def description(self) -> str:
        return "Database matrix testing - one pytest case per table, column, key, index, and constraint"
