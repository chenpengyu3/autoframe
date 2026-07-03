"""Detect resource-like API groups and safe CRUD lifecycle candidates."""

from typing import Optional

from autoframe.scanner.models import DiscoveredEndpoint, DiscoveredResource
from autoframe.utils.data_generator import generate_from_schema, random_string


ACTION_TO_OPERATION = {
    "create": "create",
    "add": "create",
    "save": "create",
    "insert": "create",
    "new": "create",
    "list": "read",
    "page": "read",
    "query": "read",
    "search": "read",
    "detail": "read",
    "get": "read",
    "find": "read",
    "update": "update",
    "edit": "update",
    "modify": "update",
    "patch": "update",
    "delete": "delete",
    "remove": "delete",
}

READ_ACTIONS = {"list", "page", "query", "search", "detail", "get", "find"}
WRITE_ACTIONS = {
    "create", "add", "save", "insert", "new",
    "update", "edit", "modify", "patch",
    "delete", "remove",
}
RELATIONSHIP_CREATE_ACTIONS = {"add", "attach", "bind", "link", "move"}
NON_RESOURCE_SEGMENTS = {"api", "v1", "v2", "v3", "admin", "auth", "oauth", "actuator"}
ACTION_ONLY_SEGMENTS = {
    "active", "advice", "all", "analysis", "approve", "ask", "ask_multi", "calendar",
    "check_limit", "check_new", "check_quality", "check_sensitive", "cleanup",
    "code_custom_analyze", "code_file_analyze", "code_recognize", "confirm_payment",
    "delete_face_user", "disable", "download", "due", "email", "enable",
    "extract_feature", "feature_usage", "generate", "generate_similar",
    "handwriting_to_text", "health", "hotspots", "hours", "login", "login_by_face",
    "login_by_phone", "logout", "maintenance_status", "notification", "package_stats",
    "payment_callback", "pending", "photo_search", "ping", "predict", "ranking",
    "recharge", "refresh", "register", "reject", "reset_password", "retention",
    "revenue_trend", "roles", "score", "search", "send", "send_login_code",
    "send_test_email", "send_weekly_report", "set_face", "stats", "status", "stream",
    "submit", "test_learning_reminder", "test_paper_restore", "token", "token_usage",
    "trigger_learning_reminder", "tts", "usage_status", "user_trend", "user_value",
    "verify_identity", "verify_payment", "vip_funnel", "warn", "weekly",
    "weekly_pattern", "wordcloud",
}


def detect_crud_resources(endpoints: list[DiscoveredEndpoint]) -> list[DiscoveredResource]:
    """Group trusted endpoints into broad resources, marking safe CRUD tests.

    The scanner reports broad "resource candidates" so business APIs are not
    under-counted, but destructive lifecycle tests only use resources marked
    testable=True.
    """
    grouped: dict[str, dict[str, object]] = {}

    trusted = [ep for ep in endpoints if ep.source in {"openapi", "source"}]

    for ep in trusted:
        base_path, path_action, has_id_param = _classify_path(ep.path)
        if not base_path or base_path == "/":
            continue

        group = grouped.setdefault(base_path, {"endpoints": [], "operations": set()})
        group["endpoints"].append((ep, path_action, has_id_param))

        for method in [m.upper() for m in ep.methods]:
            operation = _operation_for(method, path_action, has_id_param)
            if operation:
                group["operations"].add(operation)

    resources: list[DiscoveredResource] = []
    for base_path, group in grouped.items():
        ep_list = group["endpoints"]
        create_ep = None
        read_ep = None
        update_ep = None
        delete_ep = None
        supported_operations: set[str] = set()

        for ep, path_action, has_id_param in ep_list:
            methods = [m.upper() for m in ep.methods]

            for method in methods:
                if method == "POST" and path_action in RELATIONSHIP_CREATE_ACTIONS:
                    continue
                operation = _operation_for(method, path_action, has_id_param)
                if operation == "create" and create_ep is None:
                    create_ep = ep
                    supported_operations.add(operation)
                elif operation == "read" and read_ep is None:
                    read_ep = ep
                    supported_operations.add(operation)
                elif operation == "update" and update_ep is None:
                    update_ep = ep
                    supported_operations.add(operation)
                elif operation == "delete" and delete_ep is None:
                    delete_ep = ep
                    supported_operations.add(operation)

        operations = sorted(supported_operations)
        if not operations:
            continue

        resource_name = _extract_resource_name(base_path)
        has_id_read_or_update = _is_id_endpoint(read_ep) or _is_id_endpoint(update_ep)
        testable = bool(create_ep and has_id_read_or_update)
        if not _looks_like_resource(resource_name, operations, ep_list, testable):
            continue
        confidence = _confidence(operations, testable)

        create_body = {}
        update_body = {}
        if create_ep and create_ep.request_schema:
            create_body = generate_from_schema(create_ep.request_schema)
        elif create_ep:
            create_body = {"name": f"test_{resource_name}_{random_string(6)}"}

        if update_ep and update_ep.request_schema:
            update_body = generate_from_schema(update_ep.request_schema)
        elif update_ep:
            update_body = {"name": f"updated_{resource_name}_{random_string(6)}"}

        read_template = read_ep.path if read_ep else f"{base_path}/{{id}}"
        update_template = update_ep.path if update_ep else f"{base_path}/{{id}}"

        resources.append(DiscoveredResource(
            name=resource_name,
            base_path=base_path,
            create_endpoint=create_ep,
            read_endpoint=read_ep,
            update_endpoint=update_ep,
            delete_endpoint=delete_ep,
            id_field=_detect_id_field(create_ep),
            create_body=create_body,
            update_body=update_body,
            read_path_template=read_template,
            update_path_template=update_template,
            skip_update=update_ep is None,
            skip_delete_verify=True,
            operations=operations,
            confidence=confidence,
            testable=testable,
        ))

    return _dedupe_resources(resources)


def _classify_path(path: str) -> tuple[str, Optional[str], bool]:
    """Return base path, action suffix, and whether the path has an ID segment."""
    segments = [s for s in path.strip("/").split("/") if s]
    base_segments: list[str] = []
    action: Optional[str] = None
    has_id_param = False

    for seg in segments:
        normalized = _normalize_segment(seg)
        if _is_id_segment(seg):
            has_id_param = True
            break
        if normalized in ACTION_TO_OPERATION:
            action = normalized
            break
        base_segments.append(seg)

    if not base_segments:
        return "", action, has_id_param

    return "/" + "/".join(base_segments), action, has_id_param


def _extract_base_path(path: str) -> str:
    """Extract base path by removing {id} segments.

    /api/users/{id} -> /api/users
    /api/users/{userId}/orders/{orderId} -> /api/users/{userId}/orders
    """
    segments = path.strip("/").split("/")
    result = []
    for seg in segments:
        if "{" in seg and "}" in seg:
            break
        result.append(seg)
    return "/" + "/".join(result) if result else ""


def _extract_resource_name(base_path: str) -> str:
    """Extract resource name from base path.

    /api/users -> users
    /api/v1/orders -> orders
    """
    segments = [
        _normalize_segment(s)
        for s in base_path.strip("/").split("/")
        if s and _normalize_segment(s) not in NON_RESOURCE_SEGMENTS
    ]
    if not segments:
        return "resource"
    if len(segments) == 1:
        return segments[0]
    return "/".join(segments[-2:])


def _operation_for(method: str, action: Optional[str], has_id_param: bool) -> Optional[str]:
    method = method.upper()
    if action:
        operation = ACTION_TO_OPERATION.get(action)
        if operation == "delete" and method not in {"DELETE", "POST"}:
            return None
        if operation in {"create", "update"} and method not in {"POST", "PUT", "PATCH"}:
            return None
        if operation == "read" and method not in {"GET", "POST"}:
            return None
        return operation

    if method == "POST" and not has_id_param:
        return "create"
    if method == "GET":
        return "read"
    if method in {"PUT", "PATCH"}:
        return "update"
    if method == "DELETE":
        return "delete"
    return None


def _is_id_segment(segment: str) -> bool:
    lowered = segment.lower()
    return (
        ("{" in segment and "}" in segment)
        or lowered.startswith(":")
        or lowered in {"id", "{id}", "<id>"}
        or lowered.endswith("id}") 
        or lowered.endswith("_id}")
    )


def _is_id_endpoint(endpoint: Optional[DiscoveredEndpoint]) -> bool:
    return bool(endpoint and any(_is_id_segment(seg) for seg in endpoint.path.strip("/").split("/")))


def _normalize_segment(segment: str) -> str:
    return segment.strip("{}<>:").replace("-", "_").lower()


def _looks_like_resource(
    resource_name: str,
    operations: list[str],
    ep_list: list[tuple[DiscoveredEndpoint, Optional[str], bool]],
    testable: bool,
) -> bool:
    if testable:
        return True

    operation_set = set(operations)
    has_id_endpoint = any(has_id for _, _, has_id in ep_list)
    has_write = bool(operation_set & {"create", "update", "delete"})
    has_read = "read" in operation_set
    endpoint_count = len(ep_list)
    normalized_name = _normalize_segment(resource_name)

    if has_id_endpoint and has_write:
        return True
    if has_read and has_write:
        return True
    if endpoint_count >= 3 and has_write:
        return True
    if normalized_name in ACTION_ONLY_SEGMENTS and not has_id_endpoint:
        return False
    return len(operation_set) >= 2 and has_write


def _confidence(operations: list[str], testable: bool) -> str:
    if testable or len(operations) >= 3:
        return "high"
    if len(operations) >= 2 or any(op in operations for op in ("create", "update", "delete")):
        return "medium"
    return "low"


def _detect_id_field(endpoint: Optional[DiscoveredEndpoint]) -> str:
    """Try to detect the ID field name from response schema."""
    if not endpoint or not endpoint.response_schema:
        return "id"

    properties = endpoint.response_schema.get("properties", {})

    # Common ID field names
    for field_name in ["id", "Id", "ID", "_id", "uuid", "UUID"]:
        if field_name in properties:
            return field_name

    # Check for nested ID in common patterns
    for field_name, field_def in properties.items():
        if isinstance(field_def, dict) and field_def.get("type") == "object":
            inner_props = field_def.get("properties", {})
            if "id" in inner_props:
                return f"{field_name}.id"

    return "id"


def _dedupe_resources(resources: list[DiscoveredResource]) -> list[DiscoveredResource]:
    result: dict[str, DiscoveredResource] = {}
    for resource in resources:
        existing = result.get(resource.base_path)
        if not existing:
            result[resource.base_path] = resource
            continue

        existing.create_endpoint = existing.create_endpoint or resource.create_endpoint
        existing.read_endpoint = existing.read_endpoint or resource.read_endpoint
        existing.update_endpoint = existing.update_endpoint or resource.update_endpoint
        existing.delete_endpoint = existing.delete_endpoint or resource.delete_endpoint
        existing.skip_update = existing.update_endpoint is None
        existing.operations = sorted(set(existing.operations) | set(resource.operations))
        existing.testable = existing.testable or resource.testable
        existing.confidence = _confidence(existing.operations, existing.testable)

    return sorted(
        result.values(),
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r.confidence, 3),
            r.base_path,
        ),
    )
