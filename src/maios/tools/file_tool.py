from __future__ import annotations

from pathlib import Path
from typing import Any

from maios.tools.base import BaseTool, ToolResult


class FileTool(BaseTool):
    name = "file"
    description = "Read, write, append, list, and check files."

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root else None

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        action = input_data.get("action")
        if not action:
            return ToolResult(success=False, error="File action is required.")

        try:
            if action == "read":
                return self._read(input_data)
            if action == "write":
                return self._write(input_data)
            if action == "append":
                return self._append(input_data)
            if action == "exists":
                return self._exists(input_data)
            if action == "list":
                return self._list(input_data)
        except OSError as exc:
            return ToolResult(success=False, error=str(exc))
        except ValueError as exc:
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=False, error=f"Unsupported file action: {action}")

    def _path(self, value: str | Path | None) -> Path:
        if value is None:
            raise ValueError("File path is required.")

        path = Path(value)
        if self.root and not path.is_absolute():
            path = self.root / path

        resolved = path.resolve()
        if self.root and not self._is_relative_to(resolved, self.root):
            raise ValueError(f"Path is outside root: {resolved}")

        return resolved

    def _read(self, input_data: dict[str, Any]) -> ToolResult:
        path = self._path(input_data.get("path"))
        encoding = input_data.get("encoding", "utf-8")
        return ToolResult(
            success=True,
            output=path.read_text(encoding=encoding),
            metadata={"path": str(path)},
        )

    def _write(self, input_data: dict[str, Any]) -> ToolResult:
        path = self._path(input_data.get("path"))
        content = input_data.get("content", "")
        encoding = input_data.get("encoding", "utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding=encoding)
        return ToolResult(success=True, metadata={"path": str(path)})

    def _append(self, input_data: dict[str, Any]) -> ToolResult:
        path = self._path(input_data.get("path"))
        content = input_data.get("content", "")
        encoding = input_data.get("encoding", "utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding=encoding) as handle:
            handle.write(str(content))
        return ToolResult(success=True, metadata={"path": str(path)})

    def _exists(self, input_data: dict[str, Any]) -> ToolResult:
        path = self._path(input_data.get("path"))
        exists = path.exists()
        return ToolResult(
            success=True,
            output=str(exists),
            metadata={"path": str(path), "exists": exists},
        )

    def _list(self, input_data: dict[str, Any]) -> ToolResult:
        path = self._path(input_data.get("path", "."))
        items = sorted(item.name for item in path.iterdir())
        return ToolResult(
            success=True,
            output="\n".join(items),
            metadata={"path": str(path), "items": items},
        )

    def _is_relative_to(self, path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True
