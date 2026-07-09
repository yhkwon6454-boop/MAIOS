from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from maios.tools.base import BaseTool, ToolResult, normalize_output


class PythonTool(BaseTool):
    name = "python"
    description = "Execute Python code or a Python script."

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        code = input_data.get("code")
        script = input_data.get("script")
        if not code and not script:
            return ToolResult(success=False, error="Python code or script is required.")

        command = [sys.executable]
        if code:
            command.extend(["-c", str(code)])
        else:
            command.append(str(script))

        cwd = input_data.get("cwd")
        timeout = input_data.get("timeout", 30)

        try:
            completed = subprocess.run(
                command,
                cwd=Path(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                success=False,
                output=normalize_output(exc.stdout),
                error=f"Python execution timed out after {timeout} seconds.",
                metadata={"returncode": None},
            )

        return ToolResult(
            success=completed.returncode == 0,
            output=completed.stdout,
            error=completed.stderr,
            metadata={"returncode": completed.returncode},
        )
