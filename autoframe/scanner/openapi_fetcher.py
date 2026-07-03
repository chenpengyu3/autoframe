"""Fetch and parse OpenAPI/Swagger specs from running services."""

from typing import Optional
import httpx

from autoframe.scanner.models import DiscoveredEndpoint

OPENAPI_URLS = [
    "/v3/api-docs",
    "/v3/api-docs/swagger-config",
    "/swagger.json",
    "/openapi.json",
    "/api-docs",
    "/api/v1/spec",
]


def fetch_openapi_spec(base_url: str, timeout: float = 5.0) -> Optional[dict]:
    """Try to fetch an OpenAPI spec from common URLs."""
    base_url = base_url.rstrip("/")

    for path in OPENAPI_URLS:
        try:
            resp = httpx.get(f"{base_url}{path}", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and ("openapi" in data or "swagger" in data or "paths" in data):
                    return data
        except Exception:
            continue

    return None


def parse_openapi_endpoints(spec: dict) -> list[DiscoveredEndpoint]:
    """Parse an OpenAPI spec into DiscoveredEndpoint objects."""
    endpoints = []
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
            operation = path_item.get(method)
            if not operation:
                continue

            parameters = []
            request_schema = None
            response_schema = None
            tags = operation.get("tags", [])
            consumes = []
            produces = []

            # Collect parameters
            op_params = list(path_item.get("parameters", [])) + list(operation.get("parameters", []))
            for p in op_params:
                parameters.append({
                    "name": p.get("name", ""),
                    "in": p.get("in", "query"),
                    "type": p.get("schema", {}).get("type", "string"),
                    "required": p.get("required", False),
                })

            # Request body schema
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                consumes = list(content.keys())
                if json_content:
                    request_schema = json_content.get("schema", {})
                    request_schema = _maybe_resolve_schema(spec, request_schema)
                elif "multipart/form-data" in content:
                    request_schema = content["multipart/form-data"].get("schema", {})
                    request_schema = _maybe_resolve_schema(spec, request_schema)

            # Response schema (use 200/201 response)
            responses = operation.get("responses", {})
            for status in ["200", "201", "204"]:
                if status in responses:
                    resp_content = responses[status].get("content", {})
                    produces = list(resp_content.keys())
                    json_resp = resp_content.get("application/json", {})
                    if json_resp:
                        response_schema = json_resp.get("schema", {})
                        response_schema = _maybe_resolve_schema(spec, response_schema)
                    break

            endpoints.append(DiscoveredEndpoint(
                path=path,
                methods=[method.upper()],
                parameters=parameters,
                request_schema=request_schema,
                response_schema=response_schema,
                tags=list(set(tags)),
                source="openapi",
                kind=_infer_openapi_kind(path, consumes, produces, tags),
                consumes=consumes,
                produces=produces,
                metadata={"operation_id": operation.get("operationId", "")},
            ))

    return endpoints


def _maybe_resolve_schema(spec: dict, schema: dict | None) -> dict | None:
    if not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if ref:
        return _resolve_ref(spec, ref)
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        items = schema["items"]
        if "$ref" in items:
            schema = dict(schema)
            schema["items"] = _resolve_ref(spec, items["$ref"])
    return schema


def _infer_openapi_kind(path: str, consumes: list[str], produces: list[str], tags: list[str]) -> str:
    lowered = path.lower()
    tag_text = " ".join(tags).lower()
    if "graphql" in lowered or "graphql" in tag_text:
        return "graphql"
    if "text/event-stream" in produces:
        return "sse"
    if lowered.startswith("/actuator") or "actuator" in tag_text:
        return "actuator"
    if (
        any(token in lowered or token in tag_text for token in ("download", "export"))
        or any(value in produces for value in ("application/octet-stream", "application/pdf"))
    ):
        return "download"
    return "http"


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref pointer in the OpenAPI spec."""
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    current = spec
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, {})
        else:
            return {}
    return current if isinstance(current, dict) else {}
