"""TestModule abstract base class for plugin system."""

from abc import ABC, abstractmethod
from typing import Optional

from autoframe.core.context import TestContext


class TestModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def marker(self) -> str:
        return self.name

    def enabled(self, context: TestContext) -> bool:
        return self.name in context.config.test_suite.modules

    def setup(self, context: TestContext):
        pass

    def teardown(self, context: TestContext):
        pass

    def pytest_markers(self) -> dict[str, str]:
        return {}
