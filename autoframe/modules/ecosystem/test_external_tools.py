"""External testing ecosystem readiness checks."""

import subprocess

import pytest


@pytest.mark.ecosystem
class TestExternalTooling:
    def test_external_tool_command_is_usable_when_available(self, external_tool_case):
        command = external_tool_case["command"]
        if not external_tool_case["available"]:
            assert external_tool_case["required"] is False, (
                f"Required external tool is missing: {external_tool_case['name']}"
            )
            return

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        output = (result.stdout or "") + (result.stderr or "")
        assert output.strip() or result.returncode == 0, (
            f"External tool produced no output: {external_tool_case['name']}"
        )
        assert result.returncode in {0, 1, 2}, (
            f"External tool command failed unexpectedly: {external_tool_case['name']} -> {result.returncode}"
        )

    def test_external_tool_metadata_is_documented(self, external_tool_case):
        assert external_tool_case["name"]
        assert external_tool_case["category"]
        assert external_tool_case["env"].startswith("AUTOFRAME_")
        assert external_tool_case["command"]
