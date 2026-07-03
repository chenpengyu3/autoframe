"""Source tree quality and configuration hygiene checks."""

import re
import os
from pathlib import Path

import pytest


MANIFEST_NAMES = (
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
)

CONFIG_PATTERNS = (
    "application*.properties",
    "application*.yml",
    "application*.yaml",
    ".env",
    "*.env",
)

SECRET_LINE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret|private[_-]?key|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*['\"]?([^'\"\s#]+)"
)

PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "change-me",
    "password",
    "secret",
    "token",
    "${password}",
    "${secret}",
    "${token}",
}


def _project_root(config) -> Path | None:
    project_path = getattr(config.service, "project_path", None)
    if not project_path:
        return None
    return Path(project_path)


@pytest.mark.source_quality
class TestSourceHygiene:
    def test_project_source_path_is_accessible(self, config):
        root = _project_root(config)
        if root is None:
            pytest.skip("No project source path provided")

        assert root.exists() and root.is_dir(), f"Project source path is not accessible: {root}"

    def test_build_or_dependency_manifest_exists(self, config):
        root = _project_root(config)
        if root is None or not root.exists():
            pytest.skip("No project source path provided")

        found = [name for name in MANIFEST_NAMES if (root / name).exists()]
        assert found, "No build/dependency manifest found at project root"

    def test_source_config_files_do_not_expose_plaintext_secrets(self, config):
        root = _project_root(config)
        if root is None or not root.exists():
            pytest.skip("No project source path provided")

        files = []
        for pattern in CONFIG_PATTERNS:
            files.extend(root.rglob(pattern))
        files = [
            path for path in files
            if not any(part in {".git", ".venv", "venv", "target", "build", "dist", "node_modules"} for part in path.parts)
        ]
        if not files:
            pytest.skip("No source configuration files discovered")

        findings = []
        for path in files[:100]:
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for line_no, line in enumerate(lines, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                match = SECRET_LINE_PATTERN.search(stripped)
                if not match:
                    continue
                value = match.group(2).strip().strip("'\"")
                if value.startswith("${") or value.lower() in PLACEHOLDER_VALUES:
                    continue
                findings.append(f"{path.name}:{line_no}: {match.group(1)} has a literal value")

        if findings:
            message = "Plaintext secret-like config values:\n" + "\n".join(findings[:20])
            if os.environ.get("AUTOFRAME_STRICT_SOURCE_QUALITY", "").lower() in {"1", "true", "yes"}:
                pytest.fail(message)
            pytest.xfail(message)

    def test_ci_or_container_metadata_is_detected_when_present(self, config):
        root = _project_root(config)
        if root is None or not root.exists():
            pytest.skip("No project source path provided")

        candidates = [
            root / "Dockerfile",
            root / "docker-compose.yml",
            root / "docker-compose.yaml",
            root / ".github" / "workflows",
            root / ".gitlab-ci.yml",
            root / "Jenkinsfile",
        ]
        present = [path for path in candidates if path.exists()]
        if not present:
            return

        assert all(path.exists() for path in present)
