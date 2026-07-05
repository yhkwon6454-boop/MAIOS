from __future__ import annotations

from maios.agents import (
    SharedMemoryManager,
    SharedMemoryPermissionError,
)


def test_shared_memory_manager_creates_mission_workspace():
    manager = SharedMemoryManager()

    workspace = manager.create_workspace("mission-1")

    assert workspace.mission_id == "mission-1"
    assert manager.get_workspace("mission-1") is workspace
    assert manager.create_workspace("mission-1") is workspace


def test_shared_memory_manager_supports_agent_read_write():
    manager = SharedMemoryManager()

    version = manager.write("mission-1", "planner", "plan", "draft")

    assert version.key == "plan"
    assert version.value == "draft"
    assert version.version == 1
    assert version.agent_id == "planner"
    assert manager.read("mission-1", "executor", "plan") == "draft"
    assert manager.read_all("mission-1", "executor") == {"plan": "draft"}


def test_shared_memory_manager_tracks_versions_per_key():
    manager = SharedMemoryManager()

    first = manager.write("mission-1", "planner", "plan", "draft")
    second = manager.write("mission-1", "planner", "plan", "final")

    assert first.version == 1
    assert second.version == 2
    assert manager.latest("mission-1", "plan") is second
    assert manager.versions("mission-1", "plan") == [first, second]
    assert manager.read("mission-1", "planner", "plan") == "final"


def test_shared_memory_manager_enforces_read_permissions():
    manager = SharedMemoryManager()
    manager.write("mission-1", "planner", "plan", "draft")
    manager.grant("mission-1", "executor", can_read=False, can_write=True)

    try:
        manager.read("mission-1", "executor", "plan")
    except SharedMemoryPermissionError as exc:
        assert "read permission" in str(exc)
    else:
        raise AssertionError("Expected read permission failure.")


def test_shared_memory_manager_enforces_write_permissions():
    manager = SharedMemoryManager()
    manager.grant("mission-1", "observer", can_read=True, can_write=False)

    try:
        manager.write("mission-1", "observer", "note", "blocked")
    except SharedMemoryPermissionError as exc:
        assert "write permission" in str(exc)
    else:
        raise AssertionError("Expected write permission failure.")


def test_shared_memory_manager_revokes_explicit_permissions():
    manager = SharedMemoryManager()
    manager.grant("mission-1", "observer", can_read=False, can_write=False)

    assert manager.revoke("mission-1", "observer")
    assert not manager.revoke("mission-1", "missing")
    manager.write("mission-1", "observer", "note", "allowed")

    assert manager.read("mission-1", "observer", "note") == "allowed"


def test_shared_memory_manager_returns_default_for_missing_key():
    manager = SharedMemoryManager()

    assert manager.read("mission-1", "planner", "missing", default="none") == "none"
    assert manager.versions("mission-1", "missing") == []
    assert manager.latest("mission-1", "missing") is None
