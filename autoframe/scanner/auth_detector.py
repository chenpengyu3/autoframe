"""Auto-detect authentication mechanism."""

import re
from pathlib import Path
from typing import Optional

import httpx

from autoframe.scanner.models import DiscoveredAuth

LOGIN_ENDPOINTS = [
    "/auth/login", "/api/auth/login", "/api/login", "/login",
    "/token", "/oauth/token", "/api/token", "/api/auth/token",
    "/api/user/login", "/api/users/login", "/signin", "/api/signin",
]

TOKEN_FIELDS = ["token", "access_token", "jwt", "accessToken", "data.token", "result.token", "data.accessToken"]

LOGIN_BODIES = [
    {"username": "test", "password": "test"},
    {"email": "test@example.com", "password": "test"},
    {"account": "test", "password": "test"},
]


def detect_auth(base_url: str, project_path: Optional[str] = None, timeout: float = 3.0) -> DiscoveredAuth:
    """Detect authentication mechanism from running service and/or source code."""
    base_url = base_url.rstrip("/")

    # Try probing login endpoints
    auth = _probe_login_endpoints(base_url, timeout)
    if auth.login_endpoint:
        return auth

    # Check source code for auth patterns
    if project_path:
        auth = _detect_auth_from_source(project_path)
        if auth.auth_type != "none":
            return auth

    return DiscoveredAuth(auth_type="none")


def _probe_login_endpoints(base_url: str, timeout: float) -> DiscoveredAuth:
    """Probe common login endpoints to find auth mechanism."""
    for endpoint in LOGIN_ENDPOINTS:
        try:
            resp = httpx.get(f"{base_url}{endpoint}", timeout=timeout)
            if resp.status_code in (405, 415):
                # Endpoint exists but needs POST - try it
                for body in LOGIN_BODIES:
                    try:
                        resp = httpx.post(
                            f"{base_url}{endpoint}",
                            json=body,
                            timeout=timeout,
                        )
                        if resp.status_code in (200, 201):
                            data = resp.json()
                            token = _extract_token(data)
                            if token:
                                return DiscoveredAuth(
                                    auth_type="bearer",
                                    login_endpoint=endpoint,
                                    login_body=body,
                                    token_field=_find_token_field(data),
                                    token=token,
                                )
                        # Login endpoint found but token not obtained
                        if resp.status_code in (200, 201, 400, 401, 422):
                            return DiscoveredAuth(
                                auth_type="bearer",
                                login_endpoint=endpoint,
                                login_body=body,
                                acquisition_failed=True,
                            )
                    except Exception:
                        continue

            if resp.status_code == 200:
                # GET returned 200 - might be a login page
                return DiscoveredAuth(
                    auth_type="bearer",
                    login_endpoint=endpoint,
                    acquisition_failed=True,
                )
        except Exception:
            continue

    return DiscoveredAuth(auth_type="none")


def _detect_auth_from_source(project_path: str) -> DiscoveredAuth:
    """Detect auth from source code patterns."""
    root = Path(project_path)

    # Check for Spring Security
    java_files = list(root.rglob("*.java"))[:100]
    for jf in java_files:
        try:
            content = jf.read_text(encoding="utf-8", errors="ignore")
            if "SecurityFilterChain" in content or "@EnableWebSecurity" in content:
                return DiscoveredAuth(auth_type="bearer", detected_from_source=True)
            if "JwtAuthenticationFilter" in content or "JWT" in content.upper():
                return DiscoveredAuth(auth_type="bearer", detected_from_source=True)
        except Exception:
            continue

    # Check for JWT in Python
    py_files = list(root.rglob("*.py"))[:100]
    for pf in py_files:
        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
            if "jwt" in content.lower() or "jsonwebtoken" in content.lower():
                return DiscoveredAuth(auth_type="bearer", detected_from_source=True)
            if "from fastapi.security" in content:
                return DiscoveredAuth(auth_type="bearer", detected_from_source=True)
        except Exception:
            continue

    return DiscoveredAuth(auth_type="none")


def _extract_token(data: dict) -> Optional[str]:
    """Extract token from login response."""
    if not isinstance(data, dict):
        return None

    for field_path in TOKEN_FIELDS:
        value = data
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        if isinstance(value, str) and len(value) > 10:
            return value

    return None


def _find_token_field(data: dict) -> str:
    """Find the token field path in response."""
    if not isinstance(data, dict):
        return "token"

    for field_path in TOKEN_FIELDS:
        value = data
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        if isinstance(value, str) and len(value) > 10:
            return field_path

    return "token"
