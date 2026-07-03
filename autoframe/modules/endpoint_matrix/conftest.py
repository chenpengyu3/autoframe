"""Dynamic pytest case generation for discovered API inventory."""

import os
import re

import pytest

from autoframe.scanner.pipeline import ScanPipeline
from autoframe.utils.helpers import is_heavy_endpoint


_PROJECT_CACHE = None
_HEADER_VARIANTS = (
    ("accept-json", {"Accept": "application/json"}),
    ("accept-any", {"Accept": "*/*"}),
    ("gzip", {"Accept-Encoding": "gzip"}),
)


def _case_id(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, dict):
        parts = [
            str(value.get("method", "")),
            str(value.get("path", "")),
            str(value.get("name", "")),
            str(value.get("operation", "")),
            str(value.get("variant", "")),
        ]
        label = " ".join(part for part in parts if part).strip()
        return label.replace("/", "_").replace("{", "").replace("}", "").replace(" ", "_") or "case"
    if hasattr(value, "path"):
        method = (value.methods or ["GET"])[0]
        return f"{method} {value.path}".replace("/", "_").replace("{", "").replace("}", "")
    if hasattr(value, "base_path"):
        return value.name.replace("/", "_")
    return str(value)


def _project():
    global _PROJECT_CACHE
    if _PROJECT_CACHE is not None:
        return _PROJECT_CACHE

    base_url = os.environ.get("AUTOFRAME_BASE_URL")
    project_path = os.environ.get("AUTOFRAME_PROJECT_PATH")
    if not base_url or base_url.startswith("${"):
        return None

    _PROJECT_CACHE = ScanPipeline(base_url=base_url, project_path=project_path).run()
    return _PROJECT_CACHE


def _parametrize_or_skip(metafunc, fixture_name: str, values: list, reason: str):
    if values:
        metafunc.parametrize(fixture_name, values, ids=[_case_id(value) for value in values])
    else:
        metafunc.parametrize(
            fixture_name,
            [pytest.param(None, marks=pytest.mark.skip(reason=reason))],
        )


def _endpoint_method_cases(endpoints):
    return [
        {"endpoint": endpoint, "method": method.upper(), "path": endpoint.path}
        for endpoint in endpoints
        for method in endpoint.methods
    ]


def _endpoint_parameter_cases(endpoints):
    cases = []
    for endpoint in endpoints:
        seen = set()
        for parameter in endpoint.parameters:
            name = parameter.get("name") or parameter.get("key") or parameter.get("param")
            if name:
                seen.add((str(name), str(parameter.get("in") or parameter.get("location") or "")))
            cases.append(
                {
                    "endpoint": endpoint,
                    "method": (endpoint.methods or ["GET"])[0].upper(),
                    "path": endpoint.path,
                    "name": name or "<unnamed>",
                    "parameter": parameter,
                }
            )
        for name in re.findall(r"{([^{}]+)}", endpoint.path):
            if (name, "path") in seen:
                continue
            cases.append(
                {
                    "endpoint": endpoint,
                    "method": (endpoint.methods or ["GET"])[0].upper(),
                    "path": endpoint.path,
                    "name": name,
                    "parameter": {"name": name, "in": "path", "required": True, "source": "path_template"},
                }
            )
    return cases


def _endpoint_path_template_cases(endpoints):
    return [
        {
            "endpoint": endpoint,
            "method": method.upper(),
            "path": endpoint.path,
            "parameters": re.findall(r"{([^{}]+)}", endpoint.path),
        }
        for endpoint in endpoints
        if "{" in endpoint.path or "}" in endpoint.path
        for method in endpoint.methods
    ]


def _endpoint_request_schema_cases(endpoints):
    return [
        {
            "endpoint": endpoint,
            "method": method.upper(),
            "path": endpoint.path,
            "schema": endpoint.request_schema,
        }
        for endpoint in endpoints
        if endpoint.request_schema
        for method in endpoint.methods
        if method.upper() in {"POST", "PUT", "PATCH"}
    ]


def _endpoint_request_field_cases(endpoints):
    cases = []
    for endpoint in endpoints:
        if not endpoint.request_schema:
            continue
        properties = endpoint.request_schema.get("properties", {})
        for field_name, field_schema in properties.items():
            for method in endpoint.methods:
                if method.upper() not in {"POST", "PUT", "PATCH"}:
                    continue
                cases.append(
                    {
                        "endpoint": endpoint,
                        "method": method.upper(),
                        "path": endpoint.path,
                        "name": field_name,
                        "field_schema": field_schema,
                    }
                )
    return cases


def _crud_operation_cases(resources):
    cases = []
    endpoint_by_operation = {
        "create": "create_endpoint",
        "read": "read_endpoint",
        "update": "update_endpoint",
        "delete": "delete_endpoint",
    }
    for resource in resources:
        for operation in resource.operations:
            cases.append(
                {
                    "resource": resource,
                    "name": resource.name,
                    "operation": operation,
                    "endpoint": getattr(resource, endpoint_by_operation.get(operation, ""), None),
                }
            )
    return cases


def _safe_get_header_variant_cases(endpoints):
    safe_gets = [
        endpoint for endpoint in endpoints
        if "GET" in endpoint.methods
        and endpoint.safe_to_call
        and "{" not in endpoint.path
        and endpoint.kind == "http"
        and not is_heavy_endpoint(endpoint.path)
    ]
    return [
        {
            "endpoint": endpoint,
            "method": "GET",
            "path": endpoint.path,
            "variant": variant,
            "headers": headers,
        }
        for endpoint in safe_gets
        for variant, headers in _HEADER_VARIANTS
    ]


def pytest_generate_tests(metafunc):
    project = _project()
    endpoints = project.endpoints if project else []
    resources = project.resources if project else []

    if "endpoint_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_case",
            endpoints,
            "No discovered endpoints available for endpoint matrix",
        )

    if "endpoint_method_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_method_case",
            _endpoint_method_cases(endpoints),
            "No discovered endpoint methods available for method matrix",
        )

    if "endpoint_path_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_path_case",
            endpoints,
            "No discovered endpoints available for path matrix",
        )

    if "endpoint_media_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_media_case",
            endpoints,
            "No discovered endpoints available for media matrix",
        )

    if "endpoint_auth_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_auth_case",
            endpoints,
            "No discovered endpoints available for auth metadata matrix",
        )

    if "endpoint_parameter_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_parameter_case",
            _endpoint_parameter_cases(endpoints),
            "No discovered endpoint parameters available for parameter matrix",
        )

    if "endpoint_template_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_template_case",
            _endpoint_path_template_cases(endpoints),
            "No templated endpoint paths available for template matrix",
        )

    if "endpoint_request_schema_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_request_schema_case",
            _endpoint_request_schema_cases(endpoints),
            "No request body schemas available for request schema matrix",
        )

    if "endpoint_request_field_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "endpoint_request_field_case",
            _endpoint_request_field_cases(endpoints),
            "No request body fields available for request field matrix",
        )

    if "safe_get_case" in metafunc.fixturenames:
        safe_gets = [
            endpoint for endpoint in endpoints
            if "GET" in endpoint.methods
            and endpoint.safe_to_call
            and "{" not in endpoint.path
            and endpoint.kind == "http"
        ]
        _parametrize_or_skip(
            metafunc,
            "safe_get_case",
            safe_gets,
            "No safe concrete GET endpoints available for runtime matrix",
        )

    if "safe_get_header_variant_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "safe_get_header_variant_case",
            _safe_get_header_variant_cases(endpoints),
            "No safe concrete lightweight GET endpoints available for header variant matrix",
        )

    if "special_endpoint_case" in metafunc.fixturenames:
        special = [
            endpoint for endpoint in endpoints
            if endpoint.kind != "http" or "multipart/form-data" in endpoint.consumes
        ]
        _parametrize_or_skip(
            metafunc,
            "special_endpoint_case",
            special,
            "No special endpoints available for matrix",
        )

    if "crud_candidate_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "crud_candidate_case",
            resources,
            "No CRUD candidate resources available for matrix",
        )

    if "crud_operation_case" in metafunc.fixturenames:
        _parametrize_or_skip(
            metafunc,
            "crud_operation_case",
            _crud_operation_cases(resources),
            "No CRUD resource operations available for operation matrix",
        )
