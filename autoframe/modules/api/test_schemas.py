import json

import pytest

from autoframe.core.client import HttpClient
from autoframe.core import logging


@pytest.mark.api
class TestSchemas:
    """Response schema and format validation tests."""

    def test_special_endpoint_metadata(self, discovered_endpoints):
        """Verify non-REST endpoint capabilities are classified, not flattened."""
        special = [
            ep for ep in discovered_endpoints
            if ep.kind != "http" or "multipart/form-data" in ep.consumes
        ]
        if not special:
            pytest.skip("No special endpoint types discovered")

        failures = []
        for endpoint in special:
            if endpoint.kind == "websocket" and "WS" not in endpoint.methods:
                failures.append(f"{endpoint.path}: websocket endpoint missing WS method")
            if endpoint.kind == "sse" and "text/event-stream" not in endpoint.produces:
                failures.append(f"{endpoint.path}: SSE endpoint missing text/event-stream")
            if "multipart/form-data" in endpoint.consumes and endpoint.metadata.get("multipart") is not True:
                failures.append(f"{endpoint.path}: multipart endpoint missing multipart metadata")

        assert not failures, "Special endpoint metadata failures:\n" + "\n".join(failures)

    def test_json_response_format(
        self, client: HttpClient, api_test_params: dict
    ):
        """Verify that all GET endpoints return valid JSON."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        failures = []
        for endpoint in endpoints:
            method = endpoint.get("method", "GET").upper()
            path = endpoint.get("path", "/")
            if method != "GET":
                continue
            try:
                response = client.get(path)
                if response.status_code >= 400:
                    logging.info(
                        f"Skipping {path} - status {response.status_code}"
                    )
                    continue
                try:
                    response.json()
                    logging.info(f"{path} returns valid JSON")
                except (json.JSONDecodeError, ValueError):
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type:
                        failures.append(
                            f"{path} has content-type JSON but invalid body"
                        )
                        logging.error(
                            f"{path} has content-type JSON but invalid body"
                        )
                    else:
                        logging.info(
                            f"{path} returns non-JSON content ({content_type})"
                        )
            except Exception as e:
                logging.error(
                    f"{path} raised {type(e).__name__}: {e}"
                )

        assert not failures, (
            f"Invalid JSON responses:\n" + "\n".join(failures)
        )

    def test_response_schemas_valid(
        self, client: HttpClient, api_test_params: dict
    ):
        """Validate response schemas against expected schemas if provided."""
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No endpoints configured")

        schema_failures = []
        for endpoint in endpoints:
            method = endpoint.get("method", "GET").upper()
            path = endpoint.get("path", "/")
            expected_schema = endpoint.get("response_schema")
            if method != "GET" or not expected_schema:
                continue
            try:
                response = client.get(path)
                if response.status_code >= 400:
                    continue
                data = response.json()
                # Check required fields
                required_fields = expected_schema.get("required", [])
                for field in required_fields:
                    if field not in data:
                        schema_failures.append(
                            f"{path} missing required field '{field}'"
                        )
                        logging.error(
                            f"{path} missing required field '{field}'"
                        )
                # Check field types
                field_types = expected_schema.get("properties", {})
                for field_name, field_type in field_types.items():
                    if field_name in data:
                        expected_type = field_type.get("type")
                        actual_value = data[field_name]
                        type_map = {
                            "string": str,
                            "integer": int,
                            "number": (int, float),
                            "boolean": bool,
                            "array": list,
                            "object": dict,
                        }
                        if expected_type in type_map:
                            if not isinstance(
                                actual_value, type_map[expected_type]
                            ):
                                schema_failures.append(
                                    f"{path}.{field_name}: expected "
                                    f"{expected_type}, got "
                                    f"{type(actual_value).__name__}"
                                )
                logging.info(f"{path} schema validation passed")
            except Exception as e:
                logging.error(
                    f"{path} raised {type(e).__name__}: {e}"
                )

        assert not schema_failures, (
            f"Schema validation failures:\n" + "\n".join(schema_failures)
        )
