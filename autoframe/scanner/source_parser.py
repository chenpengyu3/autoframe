"""Parse source code to discover API routes."""

import re
from pathlib import Path

from autoframe.scanner.models import DiscoveredEndpoint

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "target", "build", "dist"}


def parse_spring_boot_routes(project_path: str) -> list[DiscoveredEndpoint]:
    """Parse Spring Boot Java source files for route annotations."""
    endpoints = []
    root = Path(project_path)
    context_prefix = _spring_context_prefix(root)

    java_files = _source_files(root, "*.java")
    java_type_schemas = _build_java_type_schemas(java_files)
    _add_spring_actuator_endpoints(endpoints, root, context_prefix)

    for jf in java_files:
        try:
            content = jf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        base_paths = [""]
        class_match = re.search(r"@RequestMapping\s*(?:\((.*?)\))?\s*(?:public\s+)?class\s+", content, re.S)
        if class_match:
            base_paths = _extract_annotation_paths(class_match.group(1) or "") or [""]

        for match in re.finditer(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\((.*?)\))?", content, re.S):
            annotation = match.group(1)
            args = match.group(2) or ""

            if annotation == "RequestMapping" and "class" in content[match.end():match.end() + 80]:
                continue

            paths = _extract_annotation_paths(args) or [""]
            methods = _spring_methods(annotation, args)
            consumes = _extract_spring_content_types(args, "consumes")
            produces = _extract_spring_content_types(args, "produces")

            for base_path in base_paths:
                for path in paths:
                    full_path = _join_paths(context_prefix, _join_paths(base_path, path))
                    following = _following_route_source(content, match.end())
                    kind = _infer_endpoint_kind(full_path, produces, following)
                    if kind == "sse" and "text/event-stream" not in produces:
                        produces.append("text/event-stream")
                    if kind == "download" and not produces:
                        produces.append("application/octet-stream")
                    metadata = {
                        "source_file": str(jf),
                        "multipart": "MultipartFile" in following,
                        "download": kind == "download",
                    }
                    if metadata["multipart"] and "multipart/form-data" not in consumes:
                        consumes.append("multipart/form-data")
                    request_schema = _infer_spring_request_schema(following, java_type_schemas)
                    if request_schema and not consumes and kind == "http":
                        consumes.append("application/json")
                    for method in methods:
                        _add_endpoint(
                            endpoints,
                            full_path,
                            method,
                            kind=kind,
                            consumes=consumes,
                            produces=produces,
                            request_schema=request_schema,
                            metadata=metadata,
                        )

        for match in re.finditer(r"@(MessageMapping|SubscribeMapping)\s*(?:\((.*?)\))?", content, re.S):
            args = match.group(2) or ""
            for path in _extract_annotation_paths(args) or [""]:
                _add_endpoint(
                    endpoints,
                    _join_paths(context_prefix, path),
                    "WS",
                    kind="websocket",
                    metadata={"source_file": str(jf), "spring_mapping": match.group(1)},
                )

        if any(marker in content for marker in ("@QueryMapping", "@MutationMapping", "@SchemaMapping")):
            _add_endpoint(
                endpoints,
                _join_paths(context_prefix, "/graphql"),
                "POST",
                kind="graphql",
                consumes=["application/json"],
                produces=["application/json"],
                metadata={"source_file": str(jf)},
            )

    return _dedupe(endpoints)


def parse_python_routes(project_path: str) -> list[DiscoveredEndpoint]:
    """Parse Python source files for route decorators (Flask/FastAPI)."""
    endpoints = []
    root = Path(project_path)

    py_files = _source_files(root, "*.py")
    include_prefixes: list[str] = []

    for pf in py_files:
        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        include_prefixes.extend(_python_include_router_prefixes(content))
        prefixes = _python_router_prefixes(content)

        for match in re.finditer(r"@([A-Za-z_]\w*)\.(get|post|put|patch|delete|route|websocket)\s*\((.*?)\)", content, re.S):
            receiver = match.group(1)
            decorator = match.group(2).lower()
            args = match.group(3) or ""
            paths = _extract_python_paths(args)
            if not paths:
                continue

            if decorator == "websocket":
                methods = ["WS"]
                kind = "websocket"
            elif decorator == "route":
                methods = _extract_python_methods(args) or ["GET"]
                kind = "http"
            else:
                methods = [decorator.upper()]
                kind = "http"

            prefix = prefixes.get(receiver, "")
            for path in paths:
                full_path = _join_paths(prefix, path)
                following = _following_route_source(content, match.end())
                consumes = ["multipart/form-data"] if ("UploadFile" in following or "File(" in following) else []
                candidates = [full_path]
                if receiver != "app":
                    candidates.extend(_join_paths(p, full_path) for p in include_prefixes)
                for candidate in dict.fromkeys(candidates):
                    endpoint_kind = _infer_endpoint_kind(candidate, [], following) if kind == "http" else kind
                    produces = ["text/event-stream"] if endpoint_kind == "sse" else []
                    for method in methods:
                        _add_endpoint(
                            endpoints,
                            candidate,
                            method,
                            kind=endpoint_kind,
                            consumes=consumes,
                            produces=produces,
                            metadata={"source_file": str(pf), "multipart": bool(consumes)},
                        )

        for match in re.finditer(r"@(?:socketio|sio)\.on\s*\((.*?)\)", content, re.S):
            args = match.group(1) or ""
            namespace = _extract_named_path(args, "namespace") or "/socket.io"
            _add_endpoint(
                endpoints,
                namespace,
                "WS",
                kind="websocket",
                metadata={"source_file": str(pf), "socketio": True},
            )

        for match in re.finditer(r"\.register\s*\(\s*[rRuUbBfF]*[\"']([^\"']+)[\"']", content):
            base = _normalize_path(match.group(1))
            for method in ("GET", "POST"):
                _add_endpoint(endpoints, base, method, metadata={"source_file": str(pf), "django_router": True})
            for method in ("GET", "PUT", "PATCH", "DELETE"):
                _add_endpoint(
                    endpoints,
                    _join_paths(base, "{id}"),
                    method,
                    metadata={"source_file": str(pf), "django_router": True},
                )

        if _contains_python_graphql(content):
            _add_endpoint(
                endpoints,
                "/graphql",
                "POST",
                kind="graphql",
                consumes=["application/json"],
                produces=["application/json"],
                metadata={"source_file": str(pf)},
            )

        for match in re.finditer(r"(?:path|re_path)\s*\(\s*[rRuUbBfF]*[\"']([^\"']+)[\"']", content):
            path = "/" + match.group(1).strip("^$")
            path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", path)
            if "include(" not in content[match.end():match.end() + 120]:
                _add_endpoint(endpoints, path, "GET", metadata={"source_file": str(pf), "django_url": True})

    return _dedupe(endpoints)


def parse_routes(project_path: str, project_type: str) -> list[DiscoveredEndpoint]:
    """Parse routes based on detected project type."""
    if project_type == "spring_boot":
        return parse_spring_boot_routes(project_path)
    elif project_type in ("fastapi", "flask", "django"):
        return parse_python_routes(project_path)
    return _dedupe(parse_spring_boot_routes(project_path) + parse_python_routes(project_path))


def _source_files(root: Path, pattern: str) -> list[Path]:
    files = []
    for path in root.rglob(pattern):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _spring_context_prefix(root: Path) -> str:
    resources_dir = root / "src" / "main" / "resources"
    if not resources_dir.exists():
        return ""

    keys = (
        "server.servlet.context-path",
        "server.context-path",
        "spring.mvc.servlet.path",
    )
    for path in list(resources_dir.glob("application*.properties")) + list(resources_dir.glob("application*.yml")) + list(resources_dir.glob("application*.yaml")):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for key in keys:
            prop_match = re.search(rf"^{re.escape(key)}\s*=\s*(\S+)", content, re.M)
            if prop_match:
                return _normalize_path(prop_match.group(1))

            yaml_key = key.split(".")[-1]
            yaml_match = re.search(rf"^\s*{re.escape(yaml_key)}\s*:\s*[\"']?([^\"'\s#]+)", content, re.M)
            if yaml_match and yaml_match.group(1).startswith("/"):
                return _normalize_path(yaml_match.group(1))
    return ""


def _add_spring_actuator_endpoints(endpoints: list[DiscoveredEndpoint], root: Path, context_prefix: str):
    build_files = [root / "pom.xml", root / "build.gradle", root / "build.gradle.kts"]
    content_parts = []
    for path in build_files:
        if path.exists():
            try:
                content_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    content = "\n".join(content_parts)
    if "spring-boot-starter-actuator" not in content:
        return

    for path in ("/actuator/health", "/actuator/info", "/actuator/metrics", "/actuator/env"):
        _add_endpoint(
            endpoints,
            _join_paths(context_prefix, path),
            "GET",
            kind="actuator",
            tags=["actuator"],
            metadata={"spring_actuator": True},
        )


def _spring_methods(annotation: str, args: str) -> list[str]:
    direct = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }
    if annotation in direct:
        return [direct[annotation]]

    methods = re.findall(r"RequestMethod\.([A-Z]+)", args)
    return sorted(set(methods)) or ["GET"]


def _extract_spring_content_types(args: str, name: str) -> list[str]:
    match = re.search(rf"{name}\s*=\s*(\{{[^}}]+\}}|[A-Za-z0-9_.]+|[\"'][^\"']+[\"'])", args, re.S)
    if not match:
        return []
    raw = match.group(1)
    values = re.findall(r"[\"']([^\"']+)[\"']", raw)
    constants = re.findall(r"MediaType\.([A-Z0-9_]+)_VALUE", raw)
    for constant in constants:
        values.append(constant.lower().replace("_", "/").replace("application/json", "application/json"))
    normalized = []
    for value in values:
        normalized.append(_normalize_content_type(value))
    return sorted(set(v for v in normalized if v))


def _extract_annotation_paths(args: str) -> list[str]:
    if not args:
        return [""]

    named = re.search(r"(?:value|path)\s*=\s*(\{[^}]+\}|[\"'][^\"']+[\"'])", args, re.S)
    target = named.group(1) if named else args
    paths = re.findall(r"[\"']([^\"']*)[\"']", target)
    return [_normalize_path(p) for p in paths if _looks_like_path(p)]


def _following_route_source(content: str, start: int, limit: int = 4000) -> str:
    snippet = content[start:start + limit]
    next_route = re.search(
        r"\n\s*@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping|"
        r"MessageMapping|SubscribeMapping|QueryMapping|MutationMapping|[A-Za-z_]\w*\."
        r"(?:get|post|put|patch|delete|route|websocket))\b",
        snippet,
    )
    if next_route:
        return snippet[:next_route.start()]
    return snippet


def _build_java_type_schemas(java_files: list[Path]) -> dict[str, dict]:
    schemas = {}
    for path in java_files:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        class_match = re.search(r"\b(?:class|record)\s+([A-Za-z_][A-Za-z0-9_]*)\b(?:[^{]*)\{", content)
        if not class_match:
            continue

        type_name = class_match.group(1)
        body = content[class_match.end():]
        properties = {}
        required = []

        record_args = ""
        if re.search(rf"\brecord\s+{re.escape(type_name)}\s*\(", content):
            record_args = _balanced_parentheses_text(content, content.find("(", class_match.start()))
            for item in _split_java_parameters(record_args):
                parts = item.strip().split()
                if len(parts) >= 2:
                    field_type, field_name = parts[-2], parts[-1]
                    properties[field_name] = _java_type_to_schema(field_type, field_name)

        for field_match in re.finditer(
            r"((?:@\w+(?:\([^)]*\))?\s*)*)"
            r"(?:private|protected|public)\s+"
            r"([A-Za-z_][A-Za-z0-9_<>?,.\s]*)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)",
            body,
        ):
            annotations = field_match.group(1) or ""
            field_type = field_match.group(2).strip()
            field_name = field_match.group(3)
            if field_name in {"serialVersionUID"}:
                continue
            properties[field_name] = _java_type_to_schema(field_type, field_name)
            if any(marker in annotations for marker in ("@NotNull", "@NotBlank", "@NotEmpty")):
                required.append(field_name)

        if properties:
            schema = {"type": "object", "properties": properties}
            if required:
                schema["required"] = sorted(set(required))
            schemas[type_name] = schema
    return schemas


def _infer_spring_request_schema(following_source: str, java_type_schemas: dict[str, dict]) -> dict | None:
    request_body_match = re.search(
        r"@RequestBody(?:\s*\([^)]*\))?\s+"
        r"(?:(?:@Valid|@Validated)\s+)?"
        r"([A-Za-z_][A-Za-z0-9_<>?,.\s]*)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        following_source,
    )
    if not request_body_match:
        return None

    body_type = " ".join(request_body_match.group(1).split())
    variable_name = request_body_match.group(2)

    if body_type.startswith("Map") or "Map<" in body_type:
        value_type = "Object"
        generic_match = re.search(r"Map\s*<\s*[^,>]+\s*,\s*([^>]+)>", body_type)
        if generic_match:
            value_type = generic_match.group(1).strip()
        properties = {}
        for field_match in re.finditer(rf"\b{re.escape(variable_name)}\.get\s*\(\s*[\"']([^\"']+)[\"']\s*\)", following_source):
            field_name = field_match.group(1)
            properties[field_name] = _java_type_to_schema(value_type, field_name)
        if not properties:
            properties = _fallback_body_properties(following_source)
        return {"type": "object", "properties": properties} if properties else {"type": "object", "properties": {}}

    simple_type = body_type.split(".")[-1].split("<", 1)[0].strip()
    if simple_type in java_type_schemas:
        return java_type_schemas[simple_type]

    return {"type": "object", "properties": _fallback_body_properties(following_source)}


def _fallback_body_properties(source: str) -> dict:
    likely_names = sorted(set(re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_]{1,40})[\"']", source)))
    ignored = {
        "success", "error", "message", "data", "code", "status", "token",
        "GET", "POST", "PUT", "PATCH", "DELETE",
    }
    properties = {}
    for name in likely_names[:20]:
        if name in ignored:
            continue
        properties[name] = _java_type_to_schema("Object", name)
    return properties


def _java_type_to_schema(java_type: str, field_name: str = "") -> dict:
    normalized = java_type.lower().replace("java.lang.", "").strip()
    field_lower = field_name.lower()
    if "email" in field_lower:
        return {"type": "string", "format": "email"}
    if field_lower == "id" or field_lower.endswith("id") or field_lower.endswith("_id"):
        return {"type": "integer"}
    if any(token in normalized for token in ("int", "integer", "long", "short", "byte")):
        return {"type": "integer"}
    if any(token in normalized for token in ("double", "float", "bigdecimal", "decimal")):
        return {"type": "number"}
    if "bool" in normalized:
        return {"type": "boolean"}
    if any(token in normalized for token in ("list", "set", "collection", "[]")):
        return {"type": "array", "items": {"type": "string"}}
    if any(token in normalized for token in ("map", "object")):
        return {"type": "string"}
    return {"type": "string"}


def _balanced_parentheses_text(content: str, open_index: int) -> str:
    if open_index < 0 or open_index >= len(content) or content[open_index] != "(":
        return ""
    depth = 0
    for index in range(open_index, len(content)):
        char = content[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return content[open_index + 1:index]
    return ""


def _split_java_parameters(text: str) -> list[str]:
    parts = []
    current = []
    depth = 0
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _infer_endpoint_kind(path: str, produces: list[str], following_source: str) -> str:
    lowered = path.lower()
    if "graphql" in lowered:
        return "graphql"
    if any("text/event-stream" in value for value in produces) or "SseEmitter" in following_source or "EventSourceResponse" in following_source:
        return "sse"
    if lowered.startswith("/actuator"):
        return "actuator"
    if (
        any(token in lowered for token in ("download", "export"))
        or "ResponseEntity<byte[]>" in following_source
        or "byte[]" in following_source
        or any(value in produces for value in ("application/octet-stream", "application/pdf"))
    ):
        return "download"
    return "http"


def _python_router_prefixes(content: str) -> dict[str, str]:
    prefixes: dict[str, str] = {"app": ""}
    for match in re.finditer(r"([A-Za-z_]\w*)\s*=\s*APIRouter\s*\((.*?)\)", content, re.S):
        prefixes[match.group(1)] = _extract_named_path(match.group(2), "prefix") or ""
    for match in re.finditer(r"([A-Za-z_]\w*)\s*=\s*Blueprint\s*\((.*?)\)", content, re.S):
        prefixes[match.group(1)] = _extract_named_path(match.group(2), "url_prefix") or ""
    return prefixes


def _python_include_router_prefixes(content: str) -> list[str]:
    prefixes = []
    for match in re.finditer(r"\.include_router\s*\((.*?)\)", content, re.S):
        prefix = _extract_named_path(match.group(1), "prefix")
        if prefix:
            prefixes.append(prefix)
    return prefixes


def _contains_python_graphql(content: str) -> bool:
    indicators = (
        "GraphQLRouter",
        "graphene",
        "strawberry",
        "ariadne",
        "GraphQLView",
    )
    return any(indicator in content for indicator in indicators)


def _extract_named_path(args: str, name: str) -> str:
    match = re.search(rf"{name}\s*=\s*[\"']([^\"']*)[\"']", args)
    return _normalize_path(match.group(1)) if match else ""


def _extract_python_paths(args: str) -> list[str]:
    paths = re.findall(r"[rRuUbBfF]*[\"']([^\"']*)[\"']", args)
    return [_normalize_path(p) for p in paths if _looks_like_path(p)]


def _extract_python_methods(args: str) -> list[str]:
    methods_match = re.search(r"methods\s*=\s*\[([^\]]+)\]", args, re.S)
    if not methods_match:
        return []
    return sorted({m.upper() for m in re.findall(r"[\"']([A-Za-z]+)[\"']", methods_match.group(1))})


def _looks_like_path(value: str) -> bool:
    return value == "" or value.startswith("/")


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    path = path.strip()
    path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", path)
    path = re.sub(r":([A-Za-z_]\w*)", r"{\1}", path)
    return path if path.startswith("/") else f"/{path}"


def _normalize_content_type(value: str) -> str:
    if "/" in value:
        return value.lower()
    mapping = {
        "application_json": "application/json",
        "multipart_form_data": "multipart/form-data",
        "text_event_stream": "text/event-stream",
        "text_plain": "text/plain",
    }
    return mapping.get(value.lower(), value.lower().replace("_", "/"))


def _join_paths(base_path: str, path: str) -> str:
    base_path = _normalize_path(base_path)
    path = _normalize_path(path)
    if not base_path:
        return path or "/"
    if not path:
        return base_path
    return f"{base_path.rstrip('/')}/{path.lstrip('/')}"


def _add_endpoint(
    endpoints: list[DiscoveredEndpoint],
    path: str,
    method: str,
    *,
    kind: str = "http",
    consumes: list[str] | None = None,
    produces: list[str] | None = None,
    tags: list[str] | None = None,
    request_schema: dict | None = None,
    metadata: dict | None = None,
):
    path = _normalize_path(path)
    method = method.upper()
    existing = next((e for e in endpoints if e.path == path and method in e.methods), None)
    if existing:
        existing.kind = existing.kind if existing.kind != "http" else kind
        existing.consumes = sorted(set(existing.consumes) | set(consumes or []))
        existing.produces = sorted(set(existing.produces) | set(produces or []))
        existing.tags = sorted(set(existing.tags) | set(tags or []))
        existing.request_schema = existing.request_schema or request_schema
        existing.metadata.update(metadata or {})
        return
    endpoints.append(DiscoveredEndpoint(
        path=path,
        methods=[method],
        source="source",
        kind=kind,
        consumes=consumes or [],
        produces=produces or [],
        request_schema=request_schema,
        tags=tags or [],
        metadata=metadata or {},
    ))


def _dedupe(endpoints: list[DiscoveredEndpoint]) -> list[DiscoveredEndpoint]:
    result: list[DiscoveredEndpoint] = []
    for ep in endpoints:
        for method in ep.methods or ["GET"]:
            _add_endpoint(
                result,
                ep.path,
                method,
                kind=ep.kind,
                consumes=ep.consumes,
                produces=ep.produces,
                tags=ep.tags,
                request_schema=ep.request_schema,
                metadata=ep.metadata,
            )
    return result
