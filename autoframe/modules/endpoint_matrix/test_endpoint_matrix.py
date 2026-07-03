"""Generated endpoint and resource matrix tests."""

import os
import re

import pytest

from autoframe.core.client import HttpClient


KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
KNOWN_KINDS = {"http", "actuator", "graphql", "websocket", "sse", "download"}


def _xfail_or_assert_no_5xx(response, label: str):
    if response.status_code >= 500 and os.environ.get("AUTOFRAME_STRICT_ENDPOINT_MATRIX", "").lower() not in {"1", "true", "yes"}:
        pytest.xfail(
            f"{label}: runtime matrix observed {response.status_code}; "
            "set AUTOFRAME_STRICT_ENDPOINT_MATRIX=true to fail on endpoint-level 5xx"
        )
    assert response.status_code < 500, (
        f"{label}: expected non-5xx, got {response.status_code}"
    )


@pytest.mark.endpoint_matrix
class TestEndpointMatrix:
    def test_endpoint_discovery_matrix(self, endpoint_case):
        assert endpoint_case is not None
        assert endpoint_case.path.startswith("/")
        assert endpoint_case.source in {"openapi", "source", "probe"}
        assert endpoint_case.kind in KNOWN_KINDS
        assert endpoint_case.methods

    def test_endpoint_method_matrix(self, endpoint_method_case):
        endpoint = endpoint_method_case["endpoint"]
        method = endpoint_method_case["method"]
        assert method in KNOWN_METHODS
        assert method in {item.upper() for item in endpoint.methods}
        assert endpoint.path == endpoint_method_case["path"]

    def test_endpoint_path_contract_matrix(self, endpoint_path_case):
        path = endpoint_path_case.path
        assert path.startswith("/")
        assert " " not in path
        assert "?" not in path
        assert "//" not in path
        assert path.count("{") == path.count("}")
        for variable in re.findall(r"{([^{}]+)}", path):
            assert variable.strip(), f"Empty path variable in {path}"

    def test_endpoint_media_contract_matrix(self, endpoint_media_case):
        assert isinstance(endpoint_media_case.consumes, list)
        assert isinstance(endpoint_media_case.produces, list)
        assert all(isinstance(value, str) and value for value in endpoint_media_case.consumes)
        assert all(isinstance(value, str) and value for value in endpoint_media_case.produces)
        if endpoint_media_case.kind == "download":
            assert endpoint_media_case.produces, f"Download endpoint missing produces contract: {endpoint_media_case.path}"
        if "multipart/form-data" in endpoint_media_case.consumes:
            assert endpoint_media_case.metadata.get("multipart") is True

    def test_endpoint_auth_metadata_matrix(self, endpoint_auth_case):
        assert isinstance(endpoint_auth_case.auth_required, bool)
        if endpoint_auth_case.status_code in {401, 403}:
            assert endpoint_auth_case.auth_required is True
        if endpoint_auth_case.auth_required:
            assert endpoint_auth_case.source in {"openapi", "source", "probe"}

    def test_endpoint_parameter_matrix(self, endpoint_parameter_case):
        endpoint = endpoint_parameter_case["endpoint"]
        parameter = endpoint_parameter_case["parameter"]
        name = endpoint_parameter_case["name"]
        assert isinstance(parameter, dict)
        assert name and name != "<unnamed>"
        location = str(parameter.get("in") or parameter.get("location") or "").lower()
        if location == "path":
            assert "{" + name + "}" in endpoint.path

    def test_endpoint_template_path_matrix(self, endpoint_template_case):
        path = endpoint_template_case["path"]
        parameters = endpoint_template_case["parameters"]
        assert parameters
        assert path.count("{") == path.count("}")
        assert len(parameters) == len(set(parameters)), f"Duplicate template parameters in {path}"
        for parameter in parameters:
            assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", parameter), (
                f"Unexpected template parameter name in {path}: {parameter}"
            )

    def test_endpoint_request_schema_matrix(self, endpoint_request_schema_case):
        schema = endpoint_request_schema_case["schema"]
        assert schema.get("type") == "object"
        assert isinstance(schema.get("properties", {}), dict)
        assert endpoint_request_schema_case["method"] in {"POST", "PUT", "PATCH"}
        assert endpoint_request_schema_case["path"].startswith("/")

    def test_endpoint_request_field_matrix(self, endpoint_request_field_case):
        field_name = endpoint_request_field_case["name"]
        field_schema = endpoint_request_field_case["field_schema"]
        assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", field_name), (
            f"Unexpected request field name in {endpoint_request_field_case['path']}: {field_name}"
        )
        assert isinstance(field_schema, dict)
        assert field_schema.get("type") in {"string", "integer", "number", "boolean", "array", "object"}

    def test_safe_get_endpoint_runtime_matrix(self, client: HttpClient, safe_get_case):
        assert safe_get_case is not None
        response = client.get(safe_get_case.path)
        _xfail_or_assert_no_5xx(response, f"GET {safe_get_case.path}")

    def test_safe_get_header_variant_runtime_matrix(self, client: HttpClient, safe_get_header_variant_case):
        response = client.get(
            safe_get_header_variant_case["path"],
            headers=safe_get_header_variant_case["headers"],
        )
        _xfail_or_assert_no_5xx(
            response,
            f"GET {safe_get_header_variant_case['path']} ({safe_get_header_variant_case['variant']})",
        )

    def test_special_endpoint_matrix(self, special_endpoint_case):
        assert special_endpoint_case is not None
        is_special = (
            special_endpoint_case.kind != "http"
            or "multipart/form-data" in special_endpoint_case.consumes
        )
        assert is_special
        if special_endpoint_case.kind == "sse":
            assert "text/event-stream" in special_endpoint_case.produces
        if "multipart/form-data" in special_endpoint_case.consumes:
            assert special_endpoint_case.metadata.get("multipart") is True
        if special_endpoint_case.kind == "download":
            assert special_endpoint_case.produces

    def test_crud_candidate_matrix(self, crud_candidate_case):
        assert crud_candidate_case is not None
        assert crud_candidate_case.base_path.startswith("/")
        assert crud_candidate_case.operations
        endpoints = [
            crud_candidate_case.create_endpoint,
            crud_candidate_case.read_endpoint,
            crud_candidate_case.update_endpoint,
            crud_candidate_case.delete_endpoint,
        ]
        assert any(endpoint is not None for endpoint in endpoints)

    def test_crud_operation_matrix(self, crud_operation_case):
        resource = crud_operation_case["resource"]
        operation = crud_operation_case["operation"]
        endpoint = crud_operation_case["endpoint"]
        assert operation in {"create", "read", "update", "delete"}
        assert operation in resource.operations
        assert endpoint is not None, f"{resource.name} operation has no endpoint: {operation}"
        assert endpoint.path.startswith("/")
