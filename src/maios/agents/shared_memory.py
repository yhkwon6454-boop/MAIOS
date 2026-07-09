from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class SharedMemoryPermissionError(PermissionError):
    """Raised when an agent is not allowed to access shared memory."""


class SharedMemoryConflictError(RuntimeError):
    """Raised when a memory write conflicts with the current version."""


@dataclass(frozen=True)
class MemoryPermission:
    agent_id: str
    can_read: bool = True
    can_write: bool = True


@dataclass(frozen=True)
class MemoryVersion:
    key: str
    value: Any
    version: int
    agent_id: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class MemoryConflict:
    key: str
    base_version: int
    versions: tuple[MemoryVersion, ...]

    @property
    def values(self) -> dict[str, Any]:
        return {version.agent_id: version.value for version in self.versions}


@dataclass
class SharedWorkspace:
    mission_id: str
    records: dict[str, MemoryVersion] = field(default_factory=dict)
    history: dict[str, list[MemoryVersion]] = field(default_factory=dict)
    permissions: dict[str, MemoryPermission] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {key: record.value for key, record in self.records.items()}


class SharedMemoryManager:
    """Mission-scoped shared memory with permissions and version history."""

    def __init__(self) -> None:
        self._workspaces: dict[str, SharedWorkspace] = {}

    def create_workspace(self, mission_id: str) -> SharedWorkspace:
        workspace = self._workspaces.get(mission_id)
        if workspace is None:
            workspace = SharedWorkspace(mission_id=mission_id)
            self._workspaces[mission_id] = workspace
        return workspace

    def get_workspace(self, mission_id: str) -> SharedWorkspace | None:
        return self._workspaces.get(mission_id)

    def grant(
        self,
        mission_id: str,
        agent_id: str,
        can_read: bool = True,
        can_write: bool = True,
    ) -> MemoryPermission:
        workspace = self.create_workspace(mission_id)
        permission = MemoryPermission(
            agent_id=agent_id,
            can_read=can_read,
            can_write=can_write,
        )
        workspace.permissions[agent_id] = permission
        return permission

    def revoke(self, mission_id: str, agent_id: str) -> bool:
        workspace = self.create_workspace(mission_id)
        return workspace.permissions.pop(agent_id, None) is not None

    def write(
        self,
        mission_id: str,
        agent_id: str,
        key: str,
        value: Any,
        expected_version: int | None = None,
    ) -> MemoryVersion:
        workspace = self.create_workspace(mission_id)
        self._ensure_allowed(workspace, agent_id, "write")
        current_version = len(workspace.history.get(key, []))
        if expected_version is not None and expected_version != current_version:
            raise SharedMemoryConflictError(
                f"Memory key '{key}' for mission '{mission_id}' is at version "
                f"{current_version}, not expected version {expected_version}."
            )
        next_version = current_version + 1
        record = MemoryVersion(
            key=key,
            value=value,
            version=next_version,
            agent_id=agent_id,
        )
        workspace.records[key] = record
        workspace.history.setdefault(key, []).append(record)
        return record

    def read(
        self,
        mission_id: str,
        agent_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        workspace = self.create_workspace(mission_id)
        self._ensure_allowed(workspace, agent_id, "read")
        record = workspace.records.get(key)
        if record is None:
            return default
        return record.value

    def read_all(self, mission_id: str, agent_id: str) -> dict[str, Any]:
        workspace = self.create_workspace(mission_id)
        self._ensure_allowed(workspace, agent_id, "read")
        return workspace.snapshot()

    def versions(
        self,
        mission_id: str,
        key: str,
        agent_id: str | None = None,
    ) -> list[MemoryVersion]:
        workspace = self.create_workspace(mission_id)
        if agent_id is not None:
            self._ensure_allowed(workspace, agent_id, "read")
        return list(workspace.history.get(key, []))

    def latest(
        self,
        mission_id: str,
        key: str,
        agent_id: str | None = None,
    ) -> MemoryVersion | None:
        workspace = self.create_workspace(mission_id)
        if agent_id is not None:
            self._ensure_allowed(workspace, agent_id, "read")
        return workspace.records.get(key)

    def rollback(
        self,
        mission_id: str,
        agent_id: str,
        key: str,
        version: int,
    ) -> MemoryVersion:
        workspace = self.create_workspace(mission_id)
        self._ensure_allowed(workspace, agent_id, "write")
        target = self._version_for_key(workspace, key, version)
        if target is None:
            raise ValueError(
                f"Memory key '{key}' for mission '{mission_id}' has no version {version}."
            )
        return self.write(
            mission_id,
            agent_id,
            key,
            target.value,
            expected_version=len(workspace.history.get(key, [])),
        )

    def detect_conflicts(
        self,
        mission_id: str,
        key: str | None = None,
        since_version: int = 0,
        agent_id: str | None = None,
    ) -> list[MemoryConflict]:
        workspace = self.create_workspace(mission_id)
        if agent_id is not None:
            self._ensure_allowed(workspace, agent_id, "read")

        keys = [key] if key is not None else list(workspace.history)
        conflicts = []
        for memory_key in keys:
            versions = [
                version
                for version in workspace.history.get(memory_key, [])
                if version.version > since_version
            ]
            unique_values = {repr(version.value) for version in versions}
            unique_agents = {version.agent_id for version in versions}
            if len(unique_values) > 1 and len(unique_agents) > 1:
                conflicts.append(
                    MemoryConflict(
                        key=memory_key,
                        base_version=since_version,
                        versions=tuple(versions),
                    )
                )
        return conflicts

    def _version_for_key(
        self,
        workspace: SharedWorkspace,
        key: str,
        version: int,
    ) -> MemoryVersion | None:
        for record in workspace.history.get(key, []):
            if record.version == version:
                return record
        return None

    def _ensure_allowed(
        self,
        workspace: SharedWorkspace,
        agent_id: str,
        action: str,
    ) -> None:
        permission = workspace.permissions.get(agent_id)
        if permission is None:
            return

        allowed = permission.can_read if action == "read" else permission.can_write
        if not allowed:
            raise SharedMemoryPermissionError(
                f"Agent '{agent_id}' does not have {action} permission for mission "
                f"'{workspace.mission_id}'."
            )
