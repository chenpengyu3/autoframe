"""Generate API functional test parameters from discovered endpoints."""

from autoframe.generator.base import BaseTestGenerator


class ApiTestGenerator(BaseTestGenerator):
    """Produces parameters for API functional tests."""

    def generate(self) -> dict:
        endpoints = []
        for ep in self.project.endpoints:
            if not ep.safe_to_call:
                continue
            for method in (ep.methods or ["GET"]):
                endpoints.append({
                    "path": ep.path,
                    "method": method.upper(),
                    "auth_required": ep.auth_required,
                    "parameters": ep.parameters or [],
                    "request_schema": ep.request_schema,
                    "response_schema": ep.response_schema,
                    "tags": ep.tags or [],
                    "source": ep.source,
                    "verified": ep.verified,
                    "status_code": ep.status_code,
                    "kind": ep.kind,
                    "consumes": ep.consumes,
                    "produces": ep.produces,
                    "metadata": ep.metadata,
                })

        return {
            "endpoints": endpoints,
            "health_endpoints": self.project.health_endpoints or [],
        }
