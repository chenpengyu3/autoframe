"""Detect project type from source code or running service."""

import re
from pathlib import Path
from typing import Optional

import httpx


def detect_from_source(project_path: str) -> Optional[str]:
    """Detect project type by examining source files."""
    root = Path(project_path)
    if not root.exists():
        return None

    # Spring Boot: pom.xml or build.gradle with spring-boot
    for build_file in ["pom.xml", "build.gradle", "build.gradle.kts"]:
        build_path = root / build_file
        if build_path.exists():
            content = build_path.read_text(encoding="utf-8", errors="ignore")
            if "spring-boot" in content or "org.springframework.boot" in content:
                return "spring_boot"

    # Check for Java source with Spring annotations
    java_files = list(root.rglob("*.java"))[:50]
    for jf in java_files:
        try:
            content = jf.read_text(encoding="utf-8", errors="ignore")
            if "@SpringBootApplication" in content or "@RestController" in content:
                return "spring_boot"
        except Exception:
            continue

    # FastAPI: check for fastapi import
    py_files = list(root.rglob("*.py"))[:50]
    for pf in py_files:
        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
            if "from fastapi" in content or "import fastapi" in content:
                return "fastapi"
            if "from flask" in content or "import flask" in content:
                return "flask"
            if "from django" in content or "import django" in content:
                return "django"
        except Exception:
            continue

    # Check requirements.txt / pyproject.toml
    for req_file in ["requirements.txt", "pyproject.toml"]:
        req_path = root / req_file
        if req_path.exists():
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "fastapi" in content:
                return "fastapi"
            if "flask" in content:
                return "flask"
            if "django" in content:
                return "django"

    return None


def detect_from_service(base_url: str, timeout: float = 5.0) -> str:
    """Detect project type by probing a running service."""
    base_url = base_url.rstrip("/")

    # Spring Boot indicators
    for endpoint in ["/actuator/health", "/actuator/info"]:
        try:
            resp = httpx.get(f"{base_url}{endpoint}", timeout=timeout)
            if resp.status_code == 200:
                return "spring_boot"
        except Exception:
            continue

    # FastAPI indicators
    for endpoint in ["/openapi.json", "/docs"]:
        try:
            resp = httpx.get(f"{base_url}{endpoint}", timeout=timeout)
            if resp.status_code == 200:
                return "fastapi"
        except Exception:
            continue

    # Flask indicators
    try:
        resp = httpx.get(f"{base_url}/swagger.json", timeout=timeout)
        if resp.status_code == 200:
            return "flask"
    except Exception:
        pass

    # Check headers
    try:
        resp = httpx.get(base_url, timeout=timeout)
        server = resp.headers.get("Server", "").lower()
        if "uvicorn" in server or "gunicorn" in server:
            return "fastapi"
        if "werkzeug" in server:
            return "flask"
    except Exception:
        pass

    return "unknown"
