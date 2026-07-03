"""Dynamic pytest case generation for optional external test tools."""

import os
import shutil

import pytest


TOOL_CASES = [
    {
        "name": "schemathesis",
        "command": ["schemathesis", "--version"],
        "category": "schema/property API testing",
        "env": "AUTOFRAME_SCHEMATHESIS_CMD",
        "required": False,
    },
    {
        "name": "k6",
        "command": ["k6", "version"],
        "category": "load/performance testing",
        "env": "AUTOFRAME_K6_CMD",
        "required": False,
    },
    {
        "name": "zap-baseline",
        "command": ["zap-baseline.py", "-h"],
        "category": "passive DAST baseline",
        "env": "AUTOFRAME_ZAP_BASELINE_CMD",
        "required": False,
    },
    {
        "name": "restler",
        "command": ["restler", "--help"],
        "category": "stateful REST API fuzzing",
        "env": "AUTOFRAME_RESTLER_CMD",
        "required": False,
    },
    {
        "name": "docker",
        "command": ["docker", "--version"],
        "category": "containerized integration testing",
        "env": "AUTOFRAME_DOCKER_CMD",
        "required": False,
    },
    {
        "name": "java",
        "command": ["java", "-version"],
        "category": "Spring Boot runtime/toolchain",
        "env": "AUTOFRAME_JAVA_CMD",
        "required": False,
    },
    {
        "name": "maven",
        "command": ["mvn", "-version"],
        "category": "Spring Boot build/test toolchain",
        "env": "AUTOFRAME_MAVEN_CMD",
        "required": False,
    },
    {
        "name": "gradle",
        "command": ["gradle", "--version"],
        "category": "Spring Boot build/test toolchain",
        "env": "AUTOFRAME_GRADLE_CMD",
        "required": False,
    },
    {
        "name": "pytest",
        "command": ["python", "-m", "pytest", "--version"],
        "category": "Python test toolchain",
        "env": "AUTOFRAME_PYTEST_CMD",
        "required": True,
    },
]


def _resolved_command(case: dict) -> list[str]:
    override = os.environ.get(case["env"])
    if override:
        return [override, *case["command"][1:]]
    executable = case["command"][0]
    if executable != "python":
        resolved = shutil.which(executable)
        if resolved:
            return [resolved, *case["command"][1:]]
    return case["command"]


def _available(command: list[str]) -> bool:
    executable = command[0]
    if executable == "python":
        return True
    return shutil.which(executable) is not None or os.path.exists(executable)


def pytest_generate_tests(metafunc):
    if "external_tool_case" in metafunc.fixturenames:
        cases = []
        for case in TOOL_CASES:
            command = _resolved_command(case)
            cases.append({**case, "command": command, "available": _available(command)})
        metafunc.parametrize("external_tool_case", cases, ids=[case["name"] for case in cases])
