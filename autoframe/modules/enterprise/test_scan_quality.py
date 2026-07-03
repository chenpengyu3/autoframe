"""Enterprise scan quality gates."""

import pytest


@pytest.mark.enterprise
class TestScanQuality:
    """Validate that auto-discovery is broad enough to trust."""

    def test_source_route_coverage_at_least_95_percent(self, discovered_project):
        coverage = discovered_project.coverage or {}
        candidates = coverage.get("candidate_routes", 0)
        if not candidates:
            pytest.skip("No source route candidates available for coverage audit")

        assert coverage.get("estimated_percent", 0.0) >= 95.0, (
            "Source route discovery coverage is below 95%: "
            f"{coverage.get('estimated_percent', 0.0):.2f}% "
            f"({coverage.get('parsed_source_routes', 0)}/{candidates}), "
            f"estimated missing={coverage.get('estimated_missing', 0)}"
        )

    def test_crud_resources_come_from_trusted_sources(self, discovered_resources):
        if not discovered_resources:
            pytest.skip("No CRUD resources discovered")

        failures = []
        for resource in discovered_resources:
            endpoints = [
                resource.create_endpoint,
                resource.read_endpoint,
                resource.update_endpoint,
                resource.delete_endpoint,
            ]
            for endpoint in [ep for ep in endpoints if ep is not None]:
                if endpoint.source not in {"openapi", "source"}:
                    failures.append(f"{resource.name}: {endpoint.path} came from {endpoint.source}")

        assert not failures, "Untrusted CRUD resources:\n" + "\n".join(failures)

    def test_crud_lifecycle_targets_are_explicitly_testable(self, discovered_resources, crud_test_params):
        generated = crud_test_params.get("crud_resources", [])
        if not generated:
            pytest.skip("No testable CRUD lifecycle resources discovered")

        testable_names = {
            resource.name
            for resource in discovered_resources
            if getattr(resource, "testable", False)
        }
        generated_names = {resource.get("name") for resource in generated}

        assert generated_names <= testable_names, (
            "CRUD lifecycle tests must only use resources marked testable"
        )

    def test_runtime_api_targets_are_concrete_paths(self, api_test_params):
        endpoints = api_test_params.get("endpoints", [])
        if not endpoints:
            pytest.skip("No runtime API endpoints generated")

        templated = [
            f"{ep.get('method', 'GET')} {ep.get('path')}"
            for ep in endpoints
            if "{" in ep.get("path", "") or "<" in ep.get("path", "")
        ]
        assert not templated, (
            "Runtime API tests must not call unresolved path templates:\n"
            + "\n".join(templated)
        )
