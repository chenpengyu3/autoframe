"""Shared adaptive helper functions for test modules.

All functions derive behavior from discovered data, never from hardcoded values.
"""

from typing import Any, Optional

from autoframe.core.client import HttpClient
from autoframe.core.config import AuthConfig


def filter_auth_required(endpoints: list[dict], client=None) -> list[dict]:
    """Return endpoints that are accessible.

    If client has an auth token, return all endpoints (including auth-required ones).
    If client has no token, return only endpoints that don't require authentication.
    """
    if client and getattr(client, 'auth', None) and getattr(client.auth, 'token', None):
        # Client has token - all endpoints are accessible
        return endpoints
    # No token - only return endpoints that don't require auth
    return [ep for ep in endpoints if not ep.get("auth_required", False)]


def filter_methods(endpoints: list[dict], method: str) -> list[dict]:
    """Return endpoints that support the given HTTP method."""
    method_upper = method.upper()
    return [
        ep for ep in endpoints
        if ep.get("method", "GET").upper() == method_upper
    ]


def find_accessible_get_endpoint(client: HttpClient, endpoints: list[dict]) -> Optional[str]:
    """Find the first GET endpoint that responds without 401/403.

    Iterates through endpoints, skipping auth-required ones, and returns
    the path of the first one that responds successfully.
    """
    accessible = filter_auth_required(filter_methods(endpoints, "GET"), client)
    for ep in accessible:
        path = ep.get("path", "/")
        try:
            resp = client.get(path)
            if 200 <= resp.status_code < 400:
                return path
        except Exception:
            continue
    return None


def make_no_auth_client(config) -> HttpClient:
    """Create an HttpClient with no authentication configured."""
    return HttpClient(
        base_url=config.service.base_url,
        auth=AuthConfig(type="none"),
        timeout=30,
    )


def make_fake_token_client(config, token: str = "fake_invalid_token_12345") -> HttpClient:
    """Create an HttpClient with a fake bearer token."""
    return HttpClient(
        base_url=config.service.base_url,
        auth=AuthConfig(type="bearer", token=token),
        timeout=30,
    )


def extract_id(data: dict, id_field: str = "id") -> Any:
    """Extract an ID from a response dict using the discovered id_field.

    Supports dot-notation paths like 'data.id'.
    """
    if not isinstance(data, dict):
        return None
    keys = id_field.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def dispatch_request(client: HttpClient, method: str, path: str, **kwargs):
    """Send an HTTP request using the discovered method string."""
    method_upper = method.upper()
    fn = getattr(client, method_upper.lower(), None)
    if fn is None:
        raise ValueError(f"Unsupported HTTP method: {method_upper}")
    return fn(path, **kwargs)


def is_success(status_code: int, expected: Optional[tuple] = None) -> bool:
    """Check if a status code indicates success.

    If expected is provided, check against those specific codes.
    Otherwise, any 2xx is considered success.
    """
    if expected:
        return status_code in expected
    return 200 <= status_code < 300


def is_client_error(status_code: int) -> bool:
    """Check if status code is a 4xx client error."""
    return 400 <= status_code < 500


def is_server_error(status_code: int) -> bool:
    """Check if status code is a 5xx server error."""
    return 500 <= status_code < 600


def is_heavy_endpoint(path: str) -> bool:
    """Return True for endpoints that are expected to be slower than CRUD reads."""
    lowered = path.lower()
    heavy_tokens = (
        "ai",
        "analysis",
        "analytics",
        "generate",
        "report",
        "advice",
        "download",
        "upload",
        "voice",
        "predict",
        "recognize",
        "restore",
        "stream",
    )
    return any(token in lowered for token in heavy_tokens)
