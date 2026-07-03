"""OpenAPI/schema contract checks inspired by schema-driven API testing."""

import pytest

from autoframe.scanner.openapi_fetcher import fetch_openapi_spec, parse_openapi_endpoints


@pytest.fixture(scope="session")
def openapi_spec(config):
    return fetch_openapi_spec(config.service.base_url)


@pytest.mark.contract
class TestOpenApiContracts:
    def test_openapi_spec_has_paths_when_available(self, openapi_spec, discovered_endpoints):
        if not openapi_spec:
            assert discovered_endpoints, "No OpenAPI spec and no source-derived endpoint contract discovered"
            assert all(endpoint.path.startswith("/") for endpoint in discovered_endpoints)
            return

        paths = openapi_spec.get("paths")
        assert isinstance(paths, dict) and paths, "OpenAPI spec must contain non-empty paths"

    def test_openapi_operations_are_discovered(self, openapi_spec, discovered_endpoints):
        if not openapi_spec:
            discovered = {
                (endpoint.path, method.upper())
                for endpoint in discovered_endpoints
                for method in endpoint.methods
            }
            assert discovered, "No source-derived operations discovered"
            return

        spec_endpoints = parse_openapi_endpoints(openapi_spec)
        if not spec_endpoints:
            assert discovered_endpoints, "OpenAPI specification contains no operations and scanner found no fallback operations"
            return

        discovered = {
            (endpoint.path, method.upper())
            for endpoint in discovered_endpoints
            for method in endpoint.methods
        }
        missing = [
            f"{method} {endpoint.path}"
            for endpoint in spec_endpoints
            for method in endpoint.methods
            if (endpoint.path, method.upper()) not in discovered
        ]

        assert not missing, "OpenAPI operations missing from scanner:\n" + "\n".join(missing[:20])

    def test_openapi_operations_declare_success_responses(self, openapi_spec, discovered_endpoints):
        if not openapi_spec:
            contract_like = [
                endpoint for endpoint in discovered_endpoints
                if endpoint.source in {"source", "openapi"} and endpoint.methods and endpoint.path.startswith("/")
            ]
            assert contract_like, "No OpenAPI spec and no source-derived operation contracts discovered"
            return

        failures = []
        for path, path_item in openapi_spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                responses = operation.get("responses", {})
                has_success = any(str(code).startswith("2") for code in responses)
                if not has_success:
                    failures.append(f"{method.upper()} {path}: missing 2xx response declaration")

        assert not failures, "OpenAPI operations without success responses:\n" + "\n".join(failures[:20])
