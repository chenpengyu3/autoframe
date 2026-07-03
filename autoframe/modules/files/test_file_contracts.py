"""Upload, download, and binary endpoint contract tests."""

import pytest


@pytest.mark.files
class TestFileContracts:
    def test_download_endpoints_are_binary_contracts(self, discovered_endpoints):
        downloads = [
            endpoint for endpoint in discovered_endpoints
            if endpoint.kind == "download" or any(token in endpoint.path.lower() for token in ("download", "export"))
        ]
        if not downloads:
            pytest.skip("No download/export endpoints discovered")

        failures = []
        for endpoint in downloads:
            if endpoint.kind != "download":
                failures.append(f"{endpoint.path}: not classified as download")
            if not endpoint.produces:
                failures.append(f"{endpoint.path}: missing binary produces metadata")

        assert not failures, "Download contract failures:\n" + "\n".join(failures)

    def test_multipart_endpoints_are_not_plain_json_targets(self, discovered_endpoints, api_test_params):
        multipart_paths = {
            endpoint.path for endpoint in discovered_endpoints
            if "multipart/form-data" in endpoint.consumes
        }
        if not multipart_paths:
            pytest.skip("No multipart endpoints discovered")

        plain_api_targets = {
            endpoint.get("path")
            for endpoint in api_test_params.get("endpoints", [])
            if endpoint.get("path") in multipart_paths
        }
        assert not plain_api_targets, (
            "Multipart endpoints should not be generated as plain JSON API targets:\n"
            + "\n".join(sorted(plain_api_targets))
        )

    def test_file_like_endpoints_are_classified(self, discovered_endpoints):
        file_like = [
            endpoint for endpoint in discovered_endpoints
            if (
                any(token in endpoint.path.lower() for token in ("upload", "download", "export"))
                or endpoint.kind == "download"
                or "multipart/form-data" in endpoint.consumes
                or endpoint.metadata.get("multipart") is True
            )
        ]
        if not file_like:
            pytest.skip("No file-like endpoints discovered")

        failures = []
        for endpoint in file_like:
            has_file_metadata = (
                endpoint.kind == "download"
                or "multipart/form-data" in endpoint.consumes
                or endpoint.metadata.get("multipart") is True
            )
            if not has_file_metadata:
                failures.append(f"{endpoint.path}: missing file classification metadata")

        assert not failures, "File-like endpoint classification failures:\n" + "\n".join(failures)
