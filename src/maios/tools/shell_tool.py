from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from maios.tools.base import BaseTool, ToolResult, normalize_output


class ShellTool(BaseTool):
    name = "shell"
    description = "Execute a shell command and return stdout, stderr, and exit code."

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        command = input_data.get("command")
        if not command:
            return ToolResult(success=False, error="Shell command is required.")

        cwd = input_data.get("cwd")
        timeout = input_data.get("timeout", 30)

        try:
            completed = subprocess.run(
                command,
                cwd=Path(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                success=False,
                output=normalize_output(exc.stdout),
                error=f"Command timed out after {timeout} seconds.",
                metadata={"returncode": None},
            )

        return ToolResult(
            success=completed.returncode == 0,
            output=completed.stdout,
            error=completed.stderr,
            metadata={"returncode": completed.returncode},
        )
