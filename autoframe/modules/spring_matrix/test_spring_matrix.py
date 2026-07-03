"""Generated Spring Boot source matrix tests."""

import re

import pytest


JAVA_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@pytest.mark.spring_matrix
class TestSpringMatrix:
    def test_spring_controller_matrix(self, spring_controller_case):
        if spring_controller_case is None:
            return
        assert spring_controller_case["annotation"] in {"RestController", "Controller"}
        assert spring_controller_case["name"]
        assert spring_controller_case["package"]

    def test_spring_route_method_matrix(self, spring_route_method_case):
        if spring_route_method_case is None:
            return
        assert spring_route_method_case["annotation"] in {
            "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping",
        }
        assert spring_route_method_case["line"] > 0
        assert spring_route_method_case["method_name"], (
            f"Route annotation has no method nearby: {spring_route_method_case['relative']}:{spring_route_method_case['line']}"
        )
        assert JAVA_IDENTIFIER.match(spring_route_method_case["method_name"])

    def test_spring_service_matrix(self, spring_service_case):
        if spring_service_case is None:
            return
        assert spring_service_case["annotation"] in {"Service", "Component"}
        assert spring_service_case["name"]
        assert spring_service_case["kind"] in {"class", "interface", "record", "enum"}

    def test_spring_repository_matrix(self, spring_repository_case):
        if spring_repository_case is None:
            return
        assert spring_repository_case["annotation"] in {"Repository", "RepositoryInterface"}
        assert spring_repository_case["name"]
        assert spring_repository_case["kind"] in {"class", "interface"}

    def test_spring_entity_matrix(self, spring_entity_case):
        if spring_entity_case is None:
            return
        assert spring_entity_case["annotation"] in {"Entity", "Table", "Embeddable", "MappedSuperclass"}
        assert spring_entity_case["name"]
        assert spring_entity_case["kind"] in {"class", "record"}

    def test_spring_entity_field_matrix(self, spring_entity_field_case):
        if spring_entity_field_case is None:
            return
        field_name = spring_entity_field_case["field_name"]
        assert JAVA_IDENTIFIER.match(field_name), (
            f"Invalid JPA field name: {spring_entity_field_case['relative']}:{field_name}"
        )
        assert spring_entity_field_case["field_type"]
        if "@Id" in spring_entity_field_case["field_annotations"]:
            assert field_name.lower() in {"id"} or field_name.lower().endswith("id")

    def test_spring_transactional_method_matrix(self, spring_transactional_method_case):
        if spring_transactional_method_case is None:
            return
        assert spring_transactional_method_case["annotation"] == "Transactional"
        assert spring_transactional_method_case["method_name"]
        assert JAVA_IDENTIFIER.match(spring_transactional_method_case["method_name"])

    def test_spring_scheduled_method_matrix(self, spring_scheduled_method_case):
        if spring_scheduled_method_case is None:
            return
        assert spring_scheduled_method_case["annotation"] == "Scheduled"
        assert spring_scheduled_method_case["method_name"]
        assert JAVA_IDENTIFIER.match(spring_scheduled_method_case["method_name"])

    def test_spring_injection_matrix(self, spring_injection_case):
        if spring_injection_case is None:
            return
        assert spring_injection_case["annotation"] in {"Autowired", "Resource", "Inject"}
        if spring_injection_case["field_name"]:
            assert JAVA_IDENTIFIER.match(spring_injection_case["field_name"])
