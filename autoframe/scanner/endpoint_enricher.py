"""Probe and enrich discovered endpoints."""

from copy import deepcopy
import re

import httpx

from autoframe.scanner.models import DiscoveredEndpoint


def probe_endpoints(base_url: str, endpoints: list[DiscoveredEndpoint], timeout: float = 5.0) -> list[DiscoveredEndpoint]:
    """Probe endpoints to verify they exist and detect auth requirements.

    Read-only endpoints are actively checked. Mutating endpoints discovered
    from OpenAPI/source are kept as metadata for CRUD tests, but the scanner
    does not POST/PUT/DELETE during discovery.
    """
    base_url = base_url.rstrip("/")
    enriched = []

    for ep in endpoints:
        for method in ep.methods or ["GET"]:
            item = _clone_for_method(ep, method)

            if item.kind == "websocket" or method.upper() == "WS":
                if item.source in {"openapi", "source"}:
                    enriched.append(item)
                continue

            if _has_path_template(item.path) or method.upper() not in {"GET", "HEAD", "OPTIONS"}:
                if item.source in {"openapi", "source"}:
                    enriched.append(item)
                continue

            try:
                resp = httpx.request(method, f"{base_url}{item.path}", timeout=timeout)
            except Exception:
                if item.source in {"openapi", "source"}:
                    enriched.append(item)
                continue

            item.status_code = resp.status_code
            item.auth_required = resp.status_code in (401, 403)
            item.verified = _is_known_endpoint_status(resp.status_code)
            item.safe_to_call = _is_safe_runtime_status(resp.status_code)

            if resp.status_code == 200:
                try:
                    body = resp.json()
                    if isinstance(body, dict):
                        item.response_schema = _infer_schema_from_value(body)
                except Exception:
                    pass

            if item.verified or item.source in {"openapi", "source"}:
                enriched.append(item)

    return _dedupe_endpoints(enriched)


def probe_untested_paths(base_url: str, known_paths: set[str], timeout: float = 3.0) -> list[DiscoveredEndpoint]:
    """Probe common read-only paths to find untested endpoints.

    This is intentionally conservative: brute-force discovery must never
    invent CRUD resources or perform writes against an unknown service.
    """
    base_url = base_url.rstrip("/")
    discovered = []

    common_resources = [
        "users", "user", "items", "item", "products", "product",
        "orders", "order", "categories", "category", "tags", "tag",
        "comments", "comment", "posts", "post", "files", "file",
        "settings", "config", "admin", "dashboard", "notifications",
        "messages", "message", "conversations", "chat", "sessions",
        "reports", "report", "stats", "statistics", "analytics",
        "health", "status", "info", "version",
    ]

    api_prefixes = ["/api", "/api/v1", "/v1", ""]
    standard_read_paths = [
        "/graphql",
        "/actuator/health",
        "/actuator/info",
        "/actuator/metrics",
        "/actuator/env",
        "/health",
        "/healthz",
        "/ready",
        "/readyz",
        "/live",
        "/livez",
        "/metrics",
        "/api/health",
        "/api/status",
    ]

    for path in standard_read_paths:
        if path in known_paths:
            continue
        try:
            resp = httpx.get(f"{base_url}{path}", timeout=timeout)
            if _is_positive_probe_status(resp.status_code):
                discovered.append(DiscoveredEndpoint(
                    path=path,
                    methods=["GET"],
                    source="probe",
                    auth_required=resp.status_code in (401, 403),
                    verified=True,
                    status_code=resp.status_code,
                    safe_to_call=resp.status_code < 400,
                    kind=_kind_from_path(path),
                ))
                known_paths.add(path)
        except Exception:
            continue

    for prefix in api_prefixes:
        for resource in common_resources:
            path = f"{prefix}/{resource}"
            if path in known_paths:
                continue

            try:
                resp = httpx.get(f"{base_url}{path}", timeout=timeout)
                if _is_positive_probe_status(resp.status_code):
                    ep = DiscoveredEndpoint(
                        path=path,
                        methods=["GET"],
                        source="probe",
                        auth_required=resp.status_code in (401, 403),
                        verified=True,
                        status_code=resp.status_code,
                        safe_to_call=resp.status_code < 400,
                        kind=_kind_from_path(path),
                    )
                    discovered.append(ep)
                    known_paths.add(path)

            except Exception:
                continue

    return _dedupe_endpoints(discovered)


def _clone_for_method(endpoint: DiscoveredEndpoint, method: str) -> DiscoveredEndpoint:
    item = deepcopy(endpoint)
    item.methods = [method.upper()]
    return item


def _has_path_template(path: str) -> bool:
    return bool(re.search(r"\{[^}]+\}|<[^>]+>|:[A-Za-z_]\w*", path))


def _is_known_endpoint_status(status_code: int) -> bool:
    return 200 <= status_code < 400 or status_code in (400, 401, 403, 405)


def _is_safe_runtime_status(status_code: int) -> bool:
    return 200 <= status_code < 400 or status_code in (401, 403)


def _is_positive_probe_status(status_code: int) -> bool:
    # Do not treat 401/403 as positive for brute-force probes: many secured
    # Spring apps authenticate before route matching, which makes unknown paths
    # look protected and creates false endpoints.
    return 200 <= status_code < 400 or status_code == 405


def _kind_from_path(path: str) -> str:
    lowered = path.lower()
    if "graphql" in lowered:
        return "graphql"
    if lowered.startswith("/actuator"):
        return "actuator"
    if any(token in lowered for token in ("download", "export")):
        return "download"
    return "http"


def _dedupe_endpoints(endpoints: list[DiscoveredEndpoint]) -> list[DiscoveredEndpoint]:
    deduped: dict[tuple[str, str], DiscoveredEndpoint] = {}
    for ep in endpoints:
        for method in ep.methods or ["GET"]:
            key = (ep.path, method.upper())
            if key not in deduped:
                item = _clone_for_method(ep, method)
                deduped[key] = item
                continue

            existing = deduped[key]
            existing.verified = existing.verified or ep.verified
            existing.safe_to_call = existing.safe_to_call or ep.safe_to_call
            existing.auth_required = existing.auth_required or ep.auth_required
            existing.status_code = existing.status_code or ep.status_code
            existing.parameters.extend(p for p in ep.parameters if p not in existing.parameters)
            existing.tags = sorted(set(existing.tags) | set(ep.tags))
            existing.consumes = sorted(set(existing.consumes) | set(ep.consumes))
            existing.produces = sorted(set(existing.produces) | set(ep.produces))
            existing.metadata.update(ep.metadata)
            if existing.kind == "http" and ep.kind != "http":
                existing.kind = ep.kind
            existing.request_schema = existing.request_schema or ep.request_schema
            existing.response_schema = existing.response_schema or ep.response_schema

    return list(deduped.values())


def _infer_schema_from_value(value: dict, max_depth: int = 3) -> dict:
    """Infer a simple JSON schema from a sample value."""
    if max_depth <= 0:
        return {"type": "object"}

    properties = {}
    for key, val in value.items():
        if isinstance(val, str):
            properties[key] = {"type": "string"}
        elif isinstance(val, bool):
            properties[key] = {"type": "boolean"}
        elif isinstance(val, int):
            properties[key] = {"type": "integer"}
        elif isinstance(val, float):
            properties[key] = {"type": "number"}
        elif isinstance(val, list):
            properties[key] = {"type": "array"}
        elif isinstance(val, dict):
            properties[key] = _infer_schema_from_value(val, max_depth - 1)
        elif val is None:
            properties[key] = {"type": "string"}

    return {"type": "object", "properties": properties}
