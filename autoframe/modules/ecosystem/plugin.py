from autoframe.plugins.base import TestModule


class EcosystemTestModule(TestModule):
    @property
    def name(self) -> str:
        return "ecosystem"

    @property
    def description(self) -> str:
        return "External ecosystem checks - optional integrations with Schemathesis, k6, ZAP, RESTler, Docker, Java, and Python tooling"
