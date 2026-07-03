"""Dynamic pytest case generation for Spring Boot source inventory."""

import os
import re
from pathlib import Path

import pytest


SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "target", "build", "dist"}
TYPE_PATTERN = re.compile(r"\b(class|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)")
ROUTE_PATTERN = re.compile(
    r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\((.*?)\))?",
    re.S,
)
METHOD_PATTERN = re.compile(
    r"(?:public|protected|private)\s+[A-Za-z_][A-Za-z0-9_<>, ?.\[\]]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.S,
)
FIELD_PATTERN = re.compile(
    r"((?:@\w+(?:\([^)]*\))?\s*)*)"
    r"(?:private|protected|public)\s+"
    r"([A-Za-z_][A-Za-z0-9_<>?,.\s]*)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)",
    re.S,
)


def _root() -> Path | None:
    path = os.environ.get("AUTOFRAME_PROJECT_PATH")
    if not path:
        return None
    root = Path(path)
    return root if root.exists() and root.is_dir() else None


def _is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _java_files(root: Path) -> list[dict]:
    cases = []
    for path in root.rglob("*.java"):
        if path.is_file() and not _is_skipped(path):
            content = _read(path)
            type_match = TYPE_PATTERN.search(content)
            package_match = re.search(r"^\s*package\s+([A-Za-z_][A-Za-z0-9_.]*);", content, re.M)
            cases.append(
                {
                    "root": root,
                    "path": path,
                    "relative": _relative(root, path),
                    "content": content,
                    "kind": type_match.group(1) if type_match else "",
                    "name": type_match.group(2) if type_match else path.stem,
                    "package": package_match.group(1) if package_match else "",
                }
            )
    return cases


def _annotation_cases(root: Path, annotations: tuple[str, ...]):
    cases = []
    pattern = re.compile(r"@(" + "|".join(re.escape(item) for item in annotations) + r")\b")
    for item in _java_files(root):
        for match in pattern.finditer(item["content"]):
            cases.append({**item, "annotation": match.group(1), "line": item["content"][:match.start()].count("\n") + 1})
    return cases


def _controller_cases(root: Path):
    return _annotation_cases(root, ("RestController", "Controller"))


def _service_cases(root: Path):
    return _annotation_cases(root, ("Service", "Component"))


def _repository_cases(root: Path):
    cases = _annotation_cases(root, ("Repository",))
    for item in _java_files(root):
        if re.search(r"\binterface\s+\w+\s+extends\s+\w*Repository\b", item["content"]):
            cases.append({**item, "annotation": "RepositoryInterface", "line": 1})
    return cases


def _entity_cases(root: Path):
    return _annotation_cases(root, ("Entity", "Table", "Embeddable", "MappedSuperclass"))


def _route_method_cases(root: Path):
    cases = []
    for item in _java_files(root):
        content = item["content"]
        for match in ROUTE_PATTERN.finditer(content):
            following = content[match.end():match.end() + 1200]
            method_match = METHOD_PATTERN.search(following)
            cases.append(
                {
                    **item,
                    "annotation": match.group(1),
                    "args": match.group(2) or "",
                    "method_name": method_match.group(1) if method_match else "",
                    "line": content[:match.start()].count("\n") + 1,
                }
            )
    return cases


def _entity_field_cases(root: Path):
    cases = []
    entity_files = {case["path"] for case in _entity_cases(root)}
    for item in _java_files(root):
        if item["path"] not in entity_files:
            continue
        for match in FIELD_PATTERN.finditer(item["content"]):
            field_name = match.group(3)
            if field_name == "serialVersionUID":
                continue
            cases.append(
                {
                    **item,
                    "field_annotations": match.group(1) or "",
                    "field_type": " ".join(match.group(2).split()),
                    "field_name": field_name,
                    "line": item["content"][:match.start()].count("\n") + 1,
                }
            )
    return cases


def _transactional_method_cases(root: Path):
    return _method_annotation_cases(root, "Transactional")


def _scheduled_method_cases(root: Path):
    return _method_annotation_cases(root, "Scheduled")


def _method_annotation_cases(root: Path, annotation: str):
    cases = []
    pattern = re.compile(rf"@{annotation}\b(?:\([^)]*\))?", re.S)
    for item in _java_files(root):
        for match in pattern.finditer(item["content"]):
            following = item["content"][match.end():match.end() + 800]
            method_match = METHOD_PATTERN.search(following)
            cases.append(
                {
                    **item,
                    "annotation": annotation,
                    "method_name": method_match.group(1) if method_match else "",
                    "line": item["content"][:match.start()].count("\n") + 1,
                }
            )
    return cases


def _injection_cases(root: Path):
    cases = []
    for item in _java_files(root):
        content = item["content"]
        for match in re.finditer(r"@(Autowired|Resource|Inject)\b", content):
            following = content[match.end():match.end() + 400]
            field_match = FIELD_PATTERN.search(following)
            cases.append(
                {
                    **item,
                    "annotation": match.group(1),
                    "field_name": field_match.group(3) if field_match else "",
                    "line": content[:match.start()].count("\n") + 1,
                }
            )
    return cases


def _case_id(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, dict):
        pieces = [
            value.get("relative", ""),
            value.get("annotation", ""),
            value.get("method_name", ""),
            value.get("field_name", ""),
            value.get("line", ""),
        ]
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", "_".join(str(piece) for piece in pieces if piece))[:180] or "case"
    return str(value)


def _parametrize_or_skip(metafunc, fixture_name: str, values: list, reason: str):
    if values:
        metafunc.parametrize(fixture_name, values, ids=[_case_id(value) for value in values])
    else:
        metafunc.parametrize(fixture_name, [None], ids=[reason])


def pytest_generate_tests(metafunc):
    root = _root()
    if "spring_controller_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_controller_case", _controller_cases(root) if root else [], "No Spring controllers discovered")
    if "spring_route_method_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_route_method_case", _route_method_cases(root) if root else [], "No Spring route methods discovered")
    if "spring_service_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_service_case", _service_cases(root) if root else [], "No Spring services/components discovered")
    if "spring_repository_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_repository_case", _repository_cases(root) if root else [], "No Spring repositories discovered")
    if "spring_entity_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_entity_case", _entity_cases(root) if root else [], "No JPA entities discovered")
    if "spring_entity_field_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_entity_field_case", _entity_field_cases(root) if root else [], "No JPA entity fields discovered")
    if "spring_transactional_method_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_transactional_method_case", _transactional_method_cases(root) if root else [], "No transactional methods discovered")
    if "spring_scheduled_method_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_scheduled_method_case", _scheduled_method_cases(root) if root else [], "No scheduled methods discovered")
    if "spring_injection_case" in metafunc.fixturenames:
        _parametrize_or_skip(metafunc, "spring_injection_case", _injection_cases(root) if root else [], "No field injection annotations discovered")
