from autoframe.plugins.base import TestModule


class SourceQualityTestModule(TestModule):
    @property
    def name(self) -> str:
        return "source_quality"

    @property
    def description(self) -> str:
        return "Source quality testing - manifests, configuration hygiene, CI/container metadata"
