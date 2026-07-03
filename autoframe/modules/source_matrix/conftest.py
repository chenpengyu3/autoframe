"""Dynamic pytest case generation for project source inventory."""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "target", "build", "dist"}
SOURCE_SUFFIXES = {".java", ".py", ".properties", ".yml", ".yaml", ".xml", ".toml", ".gradle", ".kts"}
JAVA_TYPE_PATTERN = re.compile(r"\b(class|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)")
JAVA_ANNOTATION_PATTERN = re.compile(r"@(RestController|Controller|Service|Repository|Component|Configuration|Entity)\b")
JAVA_ROUTE_PATTERN = re.compile(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\((.*?)\))?", re.S)
PYTHON_ROUTE_PATTERN = re.compile(r"@([A-Za-z_]\w*)\.(get|post|put|patch|delete|route|websocket)\s*\((.*?)\)", re.S)


def _project_root() -> Path | None:
    path = os.environ.get("AUTOFRAME_PROJECT_PATH")
    if not path:
        return None
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return None
    return root


def _is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _source_files(root: Path) -> list[dict]:
    cases = []
    for path in root.rglob("*"):
        if not path.is_file() or _is_skipped(path):
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES and path.name not in {"pom.xml", "requirements.txt", "package.json"}:
            continue
        cases.append({"root": root, "path": path, "relative": _relative(root, path), "suffix": path.suffix.lower()})
    return cases


def _java_file_cases(root: Path) -> list[dict]:
    return [
        {"root": root, "path": path, "relative": _relative(root, path), "content": _read(path)}
        for path in root.rglob("*.java")
        if path.is_file() and not _is_skipped(path)
    ]


def _java_type_cases(root: Path) -> list[dict]:
    cases = []
    for item in _java_file_cases(root):
        content = item["content"]
        package_match = re.search(r"^\s*package\s+([A-Za-z_][A-Za-z0-9_.]*);", content, re.M)
        for match in JAVA_TYPE_PATTERN.finditer(content):
            cases.append(
                {
                    **item,
                    "kind": match.group(1),
                    "name": match.group(2),
                    "package": package_match.group(1) if package_match else "",
                }
            )
    return cases


def _java_component_cases(root: Path) -> list[dict]:
    cases = []
    for item in _java_file_cases(root):
        content = item["content"]
        type_match = JAVA_TYPE_PATTERN.search(content)
        for match in JAVA_ANNOTATION_PATTERN.finditer(content):
            cases.append(
                {
                    **item,
                    "annotation": match.group(1),
                    "name": type_match.group(2) if type_match else "",
                    "line": content[:match.start()].count("\n") + 1,
                }
            )
    return cases


def _route_annotation_cases(root: Path) -> list[dict]:
    cases = []
    for path in root.rglob("*.java"):
        if not path.is_file() or _is_skipped(path):
            continue
        content = _read(path)
        for match in JAVA_ROUTE_PATTERN.finditer(content):
            cases.append(
                {
                    "root": root,
                    "path": path,
                    "relative": _relative(root, path),
                    "language": "java",
                    "annotation": match.group(1),
                    "args": match.group(2) or "",
                    "line": content[:match.start()].count("\n") + 1,
                }
            )

    for path in root.rglob("*.py"):
        if not path.is_file() or _is_skipped(path):
            continue
        content = _read(path)
        for match in PYTHON_ROUTE_PATTERN.finditer(content):
            cases.append(
                {
                    "root": root,
                    "path": path,
                    "relative": _relative(root, path),
                    "language": "python",
                    "annotation": match.group(2).upper(),
                    "args": match.group(3) or "",
                    "line": content[:match.start()].count("\n") + 1,
                }
            )
    return cases


def _config_property_cases(root: Path) -> list[dict]:
    cases = []
    patterns = ("application*.properties", "application*.yml", "application*.yaml", ".env", "*.env")
    for pattern in patterns:
        for path in root.rglob(pattern):
            if not path.is_file() or _is_skipped(path):
                continue
            for line_no, line in enumerate(_read(path).splitlines(), start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("---"):
                    continue
                if path.suffix.lower() == ".properties" or "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                else:
                    key = stripped.split(":", 1)[0].strip() if ":" in stripped else stripped
                if key:
                    cases.append({"path": path, "relative": _relative(root, path), "line": line_no, "key": key, "value": stripped})
    return cases


def _dependency_cases(root: Path) -> list[dict]:
    cases = []
    pom = root / "pom.xml"
    if pom.exists():
        try:
            tree = ET.parse(pom)
            namespace = ""
            if tree.getroot().tag.startswith("{"):
                namespace = tree.getroot().tag.split("}", 1)[0] + "}"
            for dep in tree.findall(f".//{namespace}dependency"):
                group_id = dep.findtext(f"{namespace}groupId") or ""
                artifact_id = dep.findtext(f"{namespace}artifactId") or ""
                scope = dep.findtext(f"{namespace}scope") or "compile"
                cases.append(
                    {
                        "path": pom,
                        "relative": "pom.xml",
                        "ecosystem": "maven",
                        "group": group_id.strip(),
                        "name": artifact_id.strip(),
                        "scope": scope.strip(),
                    }
                )
        except ET.ParseError:
            cases.append({"path": pom, "relative": "pom.xml", "ecosystem": "maven", "group": "", "name": "", "scope": "parse_error"})

    for req in (root / "requirements.txt",):
        if req.exists():
            for line in _read(req).splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                name = re.split(r"[<>=!~\[]", stripped, 1)[0].strip()
                cases.append({"path": req, "relative": "requirements.txt", "ecosystem": "python", "group": "", "name": name, "scope": "runtime"})
    return cases


def _case_id(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, dict):
        label = "_".join(
            str(value.get(key, ""))
            for key in ("relative", "annotation", "name", "key", "line")
            if value.get(key)
        )
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", label)[:180] or "case"
    return str(value)


def _parametrize_or_skip(metafunc, fixture_name: str, values: list, reason: str):
    if values:
        metafunc.parametrize(fixture_name, values, ids=[_case_id(value) for value in values])
    else:
        metafunc.parametrize(fixture_name, [pytest.param(None, marks=pytest.mark.skip(reason=reason))])


def pytest_generate_tests(metafunc):
    root = _project_root()

    if "source_file_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "source_file_case",
            _source_files(root) if root else [],
            "No project source files discovered",
        )

    if "java_file_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "java_file_case",
            _java_file_cases(root) if root else [],
            "No Java source files discovered",
        )

    if "java_type_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "java_type_case",
            _java_type_cases(root) if root else [],
            "No Java types discovered",
        )

    if "java_component_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "java_component_case",
            _java_component_cases(root) if root else [],
            "No Spring component annotations discovered",
        )

    if "route_annotation_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "route_annotation_case",
            _route_annotation_cases(root) if root else [],
            "No route annotations discovered",
        )

    if "config_property_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "config_property_case",
            _config_property_cases(root) if root else [],
            "No source configuration properties discovered",
        )

    if "dependency_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "dependency_case",
            _dependency_cases(root) if root else [],
            "No dependency manifest entries discovered",
        )
