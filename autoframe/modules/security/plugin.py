from autoframe.plugins.base import TestModule


class SecurityTestModule(TestModule):
    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Security testing - SQL injection, XSS, headers, auth bypass"
