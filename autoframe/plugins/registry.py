"""Plugin discovery and registration."""

import importlib
import pkgutil
from pathlib import Path
from typing import Optional

from autoframe.core.context import TestContext
from autoframe.plugins.base import TestModule


class PluginRegistry:
    def __init__(self):
        self._modules: dict[str, TestModule] = {}

    def register(self, module: TestModule):
        self._modules[module.name] = module

    def get(self, name: str) -> Optional[TestModule]:
        return self._modules.get(name)

    def all_modules(self) -> list[TestModule]:
        return list(self._modules.values())

    def enabled_modules(self, context: TestContext) -> list[TestModule]:
        return [m for m in self._modules.values() if m.enabled(context)]

    def discover(self):
        modules_package = Path(__file__).parent.parent / "modules"
        if not modules_package.exists():
            return

        for finder, name, ispkg in pkgutil.iter_modules([str(modules_package)]):
            if not ispkg:
                continue
            try:
                mod = importlib.import_module(f"autoframe.modules.{name}.plugin")
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, TestModule)
                        and attr is not TestModule
                    ):
                        instance = attr()
                        self.register(instance)
            except (ImportError, AttributeError):
                continue


registry = PluginRegistry()
