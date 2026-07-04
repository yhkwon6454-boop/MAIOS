from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from maios.tools.base import BaseTool, ToolResult


class GitTool(BaseTool):
    name = "git"
    description = "Execute git commands in a repository."

    def __init__(self, repo_path: str | Path | None = None) -> None:
        self.repo_path = Path(repo_path).resolve() if repo_path else None

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        args = input_data.get("args")
        if not args:
            return ToolResult(success=False, error="Git args are required.")

        if isinstance(args, str):
            args = args.split()

        repo_path = Path(input_data.get("repo_path", self.repo_path or ".")).resolve()
        timeout = input_data.get("timeout", 30)
        command = ["git", *[str(arg) for arg in args]]

        try:
            completed = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                success=False,
                output=exc.stdout or "",
                error=f"Git command timed out after {timeout} seconds.",
                metadata={"returncode": None, "command": command},
            )

        return ToolResult(
            success=completed.returncode == 0,
            output=completed.stdout,
            error=completed.stderr,
            metadata={"returncode": completed.returncode, "command": command},
        )
