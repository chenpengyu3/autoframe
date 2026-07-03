"""Base class for all test parameter generators."""

from abc import ABC, abstractmethod

from autoframe.scanner.models import DiscoveredProject


class BaseTestGenerator(ABC):
    """Abstract base for generators that turn scan results into test parameters."""

    def __init__(self, project: DiscoveredProject):
        self.project = project

    @abstractmethod
    def generate(self) -> dict:
        """Generate test parameters for the module."""
        ...
