"""Generated source inventory matrix tests."""

import re

import pytest


CONFLICT_MARKER_PATTERN = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.M)


@pytest.mark.source_matrix
class TestSourceMatrix:
    def test_source_file_inventory_matrix(self, source_file_case):
        path = source_file_case["path"]
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert path.exists() and path.is_file()
        assert content.strip(), f"Source-like file is empty: {source_file_case['relative']}"
        assert not CONFLICT_MARKER_PATTERN.search(content), (
            f"Merge conflict marker found in {source_file_case['relative']}"
        )

    def test_java_package_declaration_matrix(self, java_file_case):
        relative = java_file_case["relative"]
        content = java_file_case["content"]
        if "/src/main/java/" not in f"/{relative}" and "/src/test/java/" not in f"/{relative}":
            return

        has_package = re.search(r"^\s*package\s+[A-Za-z_][A-Za-z0-9_.]*;", content, re.M)
        assert has_package, f"Java source file is missing package declaration: {relative}"

    def test_java_type_declaration_matrix(self, java_type_case):
        content = java_type_case["content"]
        name = java_type_case["name"]
        kind = java_type_case["kind"]
        assert kind in {"class", "interface", "enum", "record"}
        assert re.search(rf"\b{kind}\s+{re.escape(name)}\b", content), (
            f"Java type declaration not found: {java_type_case['relative']}::{name}"
        )

    def test_spring_component_annotation_matrix(self, java_component_case):
        annotation = java_component_case["annotation"]
        content = java_component_case["content"]
        assert annotation in {"RestController", "Controller", "Service", "Repository", "Component", "Configuration", "Entity"}
        assert f"@{annotation}" in content
        assert java_component_case["name"], (
            f"Spring component annotation has no nearby Java type: {java_component_case['relative']}:{java_component_case['line']}"
        )

    def test_route_annotation_source_matrix(self, route_annotation_case):
        annotation = route_annotation_case["annotation"]
        args = route_annotation_case["args"]
        assert annotation
        assert route_annotation_case["line"] > 0

        if route_annotation_case["language"] == "java":
            assert annotation in {"GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping"}
            assert args is not None
        elif route_annotation_case["language"] == "python":
            assert annotation in {"GET", "POST", "PUT", "PATCH", "DELETE", "ROUTE", "WEBSOCKET"}
            assert "/" in args or annotation == "WEBSOCKET"

    def test_config_property_matrix(self, config_property_case):
        key = config_property_case["key"]
        assert key
        assert not CONFLICT_MARKER_PATTERN.search(config_property_case["value"])
        assert " " not in key, (
            f"Configuration key contains spaces: {config_property_case['relative']}:{config_property_case['line']}"
        )

    def test_dependency_manifest_matrix(self, dependency_case):
        assert dependency_case["ecosystem"] in {"maven", "python"}
        assert dependency_case["name"], f"Dependency entry missing name in {dependency_case['relative']}"
        if dependency_case["ecosystem"] == "maven":
            assert dependency_case["group"], f"Maven dependency missing groupId for {dependency_case['name']}"
