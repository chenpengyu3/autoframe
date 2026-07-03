"""Estimate route discovery coverage from source declarations."""

from __future__ import annotations

import re
from pathlib import Path

from autoframe.scanner.models import DiscoveredEndpoint
from autoframe.scanner.source_parser import _source_files


SPRING_ROUTE_ANNOTATIONS = (
    "GetMapping",
    "PostMapping",
    "PutMapping",
    "DeleteMapping",
    "PatchMapping",
    "RequestMapping",
    "MessageMapping",
    "SubscribeMapping",
    "QueryMapping",
    "MutationMapping",
)


def audit_scan_coverage(
    project_path: str | None,
    project_type: str,
    endpoints: list[DiscoveredEndpoint],
) -> dict:
    """Return a conservative coverage estimate for discovered source routes."""
    if not project_path:
        return _empty("No project source path provided")

    root = Path(project_path)
    if not root.exists():
        return _empty("Project source path does not exist")

    if project_type == "spring_boot":
        candidates = _count_spring_route_candidates(root)
    elif project_type in {"fastapi", "flask", "django"}:
        candidates = _count_python_route_candidates(root)
    else:
        candidates = _count_spring_route_candidates(root) + _count_python_route_candidates(root)

    parsed = _count_parsed_source_routes(endpoints)
    if candidates <= 0:
        percent = 100.0 if parsed == 0 else 100.0
    else:
        percent = min(parsed / candidates * 100.0, 100.0)

    return {
        "candidate_routes": candidates,
        "parsed_source_routes": parsed,
        "estimated_percent": round(percent, 2),
        "meets_95_percent": percent >= 95.0,
        "estimated_missing": max(candidates - parsed, 0),
        "notes": _coverage_notes(project_type),
    }


def _empty(reason: str) -> dict:
    return {
        "candidate_routes": 0,
        "parsed_source_routes": 0,
        "estimated_percent": None,
        "meets_95_percent": None,
        "estimated_missing": 0,
        "not_applicable": True,
        "notes": [reason],
    }


def _count_spring_route_candidates(root: Path) -> int:
    count = 0
    annotation_pattern = re.compile(r"@(" + "|".join(SPRING_ROUTE_ANNOTATIONS) + r")\b")
    class_mapping_pattern = re.compile(r"@RequestMapping\s*(?:\([^)]*\))?\s*(?:public\s+)?class\s+", re.S)

    for path in _source_files(root, "*.java"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        annotations = annotation_pattern.findall(content)
        class_mappings = class_mapping_pattern.findall(content)
        count += max(len(annotations) - len(class_mappings), 0)

    return count


def _count_python_route_candidates(root: Path) -> int:
    count = 0
    decorator_pattern = re.compile(
        r"@[A-Za-z_]\w*\.(?:get|post|put|patch|delete|route|websocket)\s*\(",
        re.S,
    )
    django_url_pattern = re.compile(r"(?:path|re_path)\s*\(")
    drf_router_pattern = re.compile(r"\.register\s*\(")

    for path in _source_files(root, "*.py"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        count += len(decorator_pattern.findall(content))
        count += len(django_url_pattern.findall(content))
        count += len(drf_router_pattern.findall(content))

    return count


def _count_parsed_source_routes(endpoints: list[DiscoveredEndpoint]) -> int:
    ignored_kinds = {"actuator"}
    return sum(
        1
        for endpoint in endpoints
        if endpoint.source == "source" and endpoint.kind not in ignored_kinds
    )


def _coverage_notes(project_type: str) -> list[str]:
    notes = [
        "Coverage is estimated from static source route declarations.",
        "Dynamic runtime routes, gateway routes, and profile-conditional routes may still require OpenAPI or runtime checks.",
    ]
    if project_type == "spring_boot":
        notes.append("Spring class-level @RequestMapping prefixes are excluded from the denominator.")
    return notes
