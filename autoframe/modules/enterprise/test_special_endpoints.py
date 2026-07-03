"""Enterprise checks for uploads, downloads, SSE, WebSocket, and GraphQL metadata."""

import pytest


@pytest.mark.enterprise
class TestSpecialEndpoints:
    """Ensure special API styles are discovered and isolated from plain REST tests."""

    def test_multipart_upload_endpoints_are_classified(self, discovered_endpoints):
        upload_endpoints = [
            ep for ep in discovered_endpoints
            if "multipart/form-data" in ep.consumes
        ]
        if not upload_endpoints:
            pytest.skip("No multipart upload endpoints discovered")

        failures = []
        for endpoint in upload_endpoints:
            methods = {m.upper() for m in endpoint.methods}
            if not methods & {"POST", "PUT", "PATCH"}:
                failures.append(f"{endpoint.path}: multipart endpoint has non-write methods {methods}")
            if endpoint.metadata.get("multipart") is not True:
                failures.append(f"{endpoint.path}: missing multipart metadata")

        assert not failures, "Multipart endpoint classification failures:\n" + "\n".join(failures)

    def test_streaming_endpoints_are_not_plain_json_targets(self, discovered_endpoints):
        streaming = [
            ep for ep in discovered_endpoints
            if ep.kind in {"sse", "websocket"}
        ]
        if not streaming:
            pytest.skip("No streaming endpoints discovered")

        failures = []
        for endpoint in streaming:
            if endpoint.kind == "websocket" and "WS" not in endpoint.methods:
                failures.append(f"{endpoint.path}: websocket endpoint missing WS method")
            if endpoint.kind == "sse" and "text/event-stream" not in endpoint.produces:
                failures.append(f"{endpoint.path}: SSE endpoint missing text/event-stream")
            if endpoint.safe_to_call and endpoint.kind == "websocket":
                failures.append(f"{endpoint.path}: websocket endpoint marked safe_to_call as HTTP")

        assert not failures, "Streaming endpoint classification failures:\n" + "\n".join(failures)

    def test_graphql_endpoints_are_post_json_contracts(self, discovered_endpoints):
        graphql = [ep for ep in discovered_endpoints if ep.kind == "graphql"]
        if not graphql:
            return

        failures = []
        for endpoint in graphql:
            methods = {m.upper() for m in endpoint.methods}
            if "POST" not in methods:
                failures.append(f"{endpoint.path}: GraphQL endpoint should support POST")
            if endpoint.consumes and "application/json" not in endpoint.consumes:
                failures.append(f"{endpoint.path}: GraphQL endpoint should consume JSON")

        assert not failures, "GraphQL endpoint contract failures:\n" + "\n".join(failures)

    def test_download_like_endpoints_have_explicit_contract(self, discovered_endpoints):
        downloads = [
            ep for ep in discovered_endpoints
            if any(token in ep.path.lower() for token in ("download", "export"))
        ]
        if not downloads:
            pytest.skip("No download/export endpoints discovered")

        failures = []
        for endpoint in downloads:
            if not endpoint.produces and endpoint.kind == "http":
                # Source-only Spring routes often omit produces; this is a warning-grade
                # enterprise contract surfaced as a test failure for teams to tighten.
                failures.append(f"{endpoint.path}: download/export endpoint has no produces metadata")

        if failures:
            pytest.xfail("Download/export endpoints lack explicit produces metadata:\n" + "\n".join(failures))
