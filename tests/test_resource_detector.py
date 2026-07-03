from autoframe.scanner.models import DiscoveredEndpoint
from autoframe.scanner.resource_detector import detect_crud_resources


def test_relationship_post_action_does_not_create_unbacked_create_operation():
    endpoints = [
        DiscoveredEndpoint(path="/api/favorite/add", methods=["POST"], source="source"),
        DiscoveredEndpoint(path="/api/favorite/{id}", methods=["GET"], source="source"),
        DiscoveredEndpoint(path="/api/favorite/{id}", methods=["DELETE"], source="source"),
    ]

    resources = detect_crud_resources(endpoints)

    favorite = next(resource for resource in resources if resource.name == "favorite")
    assert favorite.create_endpoint is None
    assert "create" not in favorite.operations
    assert favorite.operations == ["delete", "read"]


def test_collection_post_keeps_create_operation_when_endpoint_exists():
    endpoints = [
        DiscoveredEndpoint(path="/api/category", methods=["POST"], source="source"),
        DiscoveredEndpoint(path="/api/category/{id}", methods=["GET"], source="source"),
    ]

    resources = detect_crud_resources(endpoints)

    category = next(resource for resource in resources if resource.name == "category")
    assert category.create_endpoint is endpoints[0]
    assert "create" in category.operations
