"""Generate fault-tolerance test parameters from discovered endpoints."""

from autoframe.generator.base import BaseTestGenerator


class FaultTestGenerator(BaseTestGenerator):
    """Produces parameters for fault-tolerance and resilience tests."""

    def __init__(
        self,
        project,
        *,
        timeout_seconds: int = 10,
        rapid_requests: int = 30,
        recovery_wait_seconds: int = 3,
    ):
        super().__init__(project)
        self.timeout_seconds = timeout_seconds
        self.rapid_requests = rapid_requests
        self.recovery_wait_seconds = recovery_wait_seconds

    def generate(self) -> dict:
        get_endpoints = []
        for ep in self.project.endpoints:
            if not ep.safe_to_call:
                continue
            methods_upper = [m.upper() for m in (ep.methods or ["GET"])]
            if "GET" in methods_upper:
                get_endpoints.append({
                    "path": ep.path,
                    "method": "GET",
                    "auth_required": ep.auth_required,
                    "parameters": ep.parameters or [],
                    "kind": ep.kind,
                    "produces": ep.produces,
                })

        return {
            "endpoints": get_endpoints,
            "health_endpoints": self.project.health_endpoints or [],
            "timeout_seconds": self.timeout_seconds,
            "rapid_requests": self.rapid_requests,
            "recovery_wait_seconds": self.recovery_wait_seconds,
        }
