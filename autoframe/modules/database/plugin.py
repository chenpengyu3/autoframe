from autoframe.plugins.base import TestModule


class DatabaseTestModule(TestModule):
    @property
    def name(self) -> str:
        return "database"

    @property
    def description(self) -> str:
        return "Database testing - connections, queries, integrity"
