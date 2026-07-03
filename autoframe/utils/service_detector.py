"""Service type detection utility."""

import httpx

SPRING_BOOT_INDICATORS = ["/actuator/health", "/actuator/info", "/actuator/env"]
PYTHON_INDICATORS = ["/health", "/healthz", "/api/health", "/ping", "/docs", "/openapi.json"]


def detect_service_type(base_url: str, timeout: float = 5.0) -> str:
    base_url = base_url.rstrip("/")

    for endpoint in SPRING_BOOT_INDICATORS:
        try:
            resp = httpx.get(f"{base_url}{endpoint}", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
                if "status" in data or "actuator" in endpoint:
                    return "spring_boot"
        except Exception:
            continue

    for endpoint in PYTHON_INDICATORS:
        try:
            resp = httpx.get(f"{base_url}{endpoint}", timeout=timeout)
            if resp.status_code == 200:
                if endpoint in ("/docs", "/openapi.json"):
                    return "python"
                return "python"
        except Exception:
            continue

    try:
        resp = httpx.get(base_url, timeout=timeout)
        server = resp.headers.get("Server", "").lower()
        powered_by = resp.headers.get("X-Powered-By", "").lower()
        if "wsgiserver" in server or "gunicorn" in server or "uvicorn" in server:
            return "python"
        if "spring" in powered_by:
            return "spring_boot"
    except Exception:
        pass

    return "unknown"
