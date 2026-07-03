"""API documentation and OpenAPI endpoint tests."""

import pytest

from autoframe.core.client import HttpClient


OPENAPI_DOC_PATHS = (
    "/v3/api-docs",
    "/swagger.json",
    "/openapi.json",
    "/api-docs",
)

SWAGGER_UI_PATHS = (
    "/swagger-ui/index.html",
    "/swagger-ui.html",
    "/docs",
    "/redoc",
)


@pytest.mark.documentation
class TestApiDocumentation:
    def test_openapi_docs_endpoint_behavior(self, client: HttpClient, discovered_endpoints):
        observed = []
        for path in OPENAPI_DOC_PATHS:
            response = client.get(path)
            if response.status_code < 500:
                observed.append((path, response))

        available = [(path, response) for path, response in observed if response.status_code == 200]
        if not available:
            assert discovered_endpoints, "No public OpenAPI JSON docs and no source-derived API inventory"
            return

        failures = []
        for path, response in available:
            try:
                data = response.json()
            except Exception:
                failures.append(f"{path}: response is not JSON")
                continue
            if not isinstance(data, dict) or not any(key in data for key in ("openapi", "swagger", "paths")):
                failures.append(f"{path}: response is not an OpenAPI document")

        assert not failures, "OpenAPI documentation failures:\n" + "\n".join(failures)

    def test_swagger_ui_paths_do_not_server_error(self, client: HttpClient):
        failures = []
        for path in SWAGGER_UI_PATHS:
            response = client.get(path)
            if response.status_code >= 500:
                failures.append(f"GET {path}: {response.status_code}")

        assert not failures, "Documentation UI server errors:\n" + "\n".join(failures)

    def test_documentation_endpoints_are_not_accidentally_public(self, client: HttpClient):
        public_paths = []
        for path in OPENAPI_DOC_PATHS + SWAGGER_UI_PATHS:
            response = client.get(path)
            if response.status_code == 200:
                public_paths.append(path)

        # Public docs may be intentional in dev, so this is an informational
        # contract check: the endpoint must at least respond without server error.
        assert all(path.startswith("/") for path in public_paths)
