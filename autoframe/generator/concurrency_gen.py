"""Generate concurrency test parameters from discovered endpoints and resources."""

from autoframe.generator.base import BaseTestGenerator
from autoframe.scanner.schema_data_generator import generate_endpoint_body


def _write_risk_score(path: str) -> int:
    lowered = path.lower()
    high_risk = (
        "auth", "login", "logout", "register", "password", "payment",
        "recharge", "callback", "admin", "delete", "remove", "mail",
        "email", "face", "upload", "download", "voice", "ai", "generate",
        "report", "predict", "recognize", "maintenance",
    )
    preferred = ("category", "folder", "card", "favorite", "note")
    score = 50
    score += sum(20 for token in high_risk if token in lowered)
    score -= sum(10 for token in preferred if token in lowered)
    return score


class ConcurrencyTestGenerator(BaseTestGenerator):
    """Produces parameters for concurrent-access tests."""

    def __init__(self, project, *, max_threads: int = 10):
        super().__init__(project)
        self.max_threads = max_threads

    def generate(self) -> dict:
        get_endpoints = []
        write_endpoints = []

        for ep in self.project.endpoints:
            methods_upper = [m.upper() for m in (ep.methods or ["GET"])]
            for method in methods_upper:
                if ep.source not in {"openapi", "source"}:
                    continue
                if method == "GET" and not ep.safe_to_call:
                    continue
                if method in ("POST", "PUT", "PATCH") and not ep.request_schema:
                    continue
                entry = {
                    "path": ep.path,
                    "method": method,
                    "auth_required": ep.auth_required,
                    "parameters": ep.parameters or [],
                    "request_schema": ep.request_schema,
                    "request_body": generate_endpoint_body(ep) if ep.request_schema else {},
                    "risk_score": _write_risk_score(ep.path),
                    "kind": ep.kind,
                    "consumes": ep.consumes,
                    "produces": ep.produces,
                }
                if method == "GET":
                    get_endpoints.append(entry)
                elif method in ("POST", "PUT", "PATCH"):
                    write_endpoints.append(entry)

        write_endpoints.sort(key=lambda item: (item.get("risk_score", 100), item.get("path", "")))

        # Resources provide write-targets for write-concurrency tests.
        crud_resources = []
        for res in self.project.resources:
            if not res.testable:
                continue
            crud_resources.append({
                "name": res.name,
                "base_path": res.base_path,
                "create_path": res.create_endpoint.path if res.create_endpoint else res.base_path,
                "create_body": res.create_body or {"name": f"concurrent_{res.name}"},
                "id_field": res.id_field or "id",
            })

        return {
            "endpoints": get_endpoints,
            "write_endpoints": write_endpoints,
            "crud_resources": crud_resources,
            "max_threads": self.max_threads,
        }
