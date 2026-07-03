"""Generate security test parameters from discovered endpoints and payload libraries."""

from autoframe.generator.base import BaseTestGenerator
from autoframe.scanner.schema_data_generator import SECURITY_PAYLOADS


class SecurityTestGenerator(BaseTestGenerator):
    """Produces parameters for security tests (injection, XSS, headers, etc.)."""

    def generate(self) -> dict:
        endpoints = []
        protected_endpoints = []

        for ep in self.project.endpoints:
            for method in (ep.methods or ["GET"]):
                method_upper = method.upper()
                entry = {
                    "path": ep.path,
                    "method": method_upper,
                    "auth_required": ep.auth_required,
                    "parameters": ep.parameters or [],
                    "request_schema": ep.request_schema,
                    "accepts_params": self._infer_accepts_params(ep),
                    "safe_to_call": ep.safe_to_call,
                    "verified": ep.verified,
                    "kind": ep.kind,
                    "consumes": ep.consumes,
                    "produces": ep.produces,
                    "metadata": ep.metadata,
                }
                if ep.safe_to_call:
                    endpoints.append(entry)
                if ep.auth_required:
                    protected_endpoints.append(entry)

        return {
            "endpoints": endpoints,
            "protected_endpoints": protected_endpoints,
            "sql_injection": SECURITY_PAYLOADS.get("sql_injection", []),
            "xss": SECURITY_PAYLOADS.get("xss", []),
            "path_traversal": SECURITY_PAYLOADS.get("path_traversal", []),
            "command_injection": SECURITY_PAYLOADS.get("command_injection", []),
            "security_headers": SECURITY_PAYLOADS.get("security_headers", {
                "required": [],
                "recommended": [],
            }),
        }

    @staticmethod
    def _infer_accepts_params(ep) -> bool:
        """Infer whether an endpoint likely accepts query or body parameters."""
        # Endpoints with declared parameters obviously accept params
        if ep.parameters:
            return True
        # POST/PUT/PATCH endpoints accept body params
        methods_upper = [m.upper() for m in (ep.methods or [])]
        if any(m in methods_upper for m in ("POST", "PUT", "PATCH")):
            return True
        # Endpoints with request_schema accept params
        if ep.request_schema:
            return True
        # GET endpoints with path variables (e.g., /users/{id}) accept params
        if "{" in ep.path or ":" in ep.path:
            return True
        return False
