"""API discovery metadata quality tests."""

import pytest


@pytest.mark.api
class TestApiMetadata:
    def test_no_duplicate_method_path_pairs(self, discovered_endpoints):
        seen = set()
        duplicates = []
        for endpoint in discovered_endpoints:
            for method in endpoint.methods or ["GET"]:
                key = (method.upper(), endpoint.path)
                if key in seen:
                    duplicates.append(f"{key[0]} {key[1]}")
                seen.add(key)

        assert not duplicates, "Duplicate API method/path pairs:\n" + "\n".join(duplicates[:20])

    def test_endpoint_paths_are_normalized(self, discovered_endpoints):
        failures = []
        for endpoint in discovered_endpoints:
            path = endpoint.path
            if not path.startswith("/"):
                failures.append(f"{path}: must start with /")
            if "//" in path:
                failures.append(f"{path}: contains duplicate slashes")
            if " " in path:
                failures.append(f"{path}: contains spaces")

        assert not failures, "Malformed endpoint paths:\n" + "\n".join(failures[:20])

    def test_http_methods_are_known(self, discovered_endpoints):
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "WS"}
        failures = []
        for endpoint in discovered_endpoints:
            for method in endpoint.methods:
                if method.upper() not in allowed:
                    failures.append(f"{method} {endpoint.path}")

        assert not failures, "Unknown HTTP methods:\n" + "\n".join(failures[:20])

    def test_endpoint_kinds_are_known(self, discovered_endpoints):
        allowed = {"http", "actuator", "graphql", "websocket", "sse", "download"}
        failures = [
            f"{endpoint.path}: {endpoint.kind}"
            for endpoint in discovered_endpoints
            if endpoint.kind not in allowed
        ]

        assert not failures, "Unknown endpoint kinds:\n" + "\n".join(failures[:20])

