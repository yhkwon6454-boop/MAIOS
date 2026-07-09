from __future__ import annotations

import pytest

from maios.agents import (
    SharedMemoryConflictError,
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


def test_shared_memory_manager_denies_permission_checked_history_reads():
    manager = SharedMemoryManager()
    manager.write("mission-1", "planner", "plan", "draft")
    manager.grant("mission-1", "observer", can_read=False, can_write=True)

    with pytest.raises(SharedMemoryPermissionError):
        manager.versions("mission-1", "plan", agent_id="observer")

    with pytest.raises(SharedMemoryPermissionError):
        manager.latest("mission-1", "plan", agent_id="observer")

    with pytest.raises(SharedMemoryPermissionError):
        manager.detect_conflicts("mission-1", agent_id="observer")


def test_shared_memory_manager_rolls_back_to_prior_version():
    manager = SharedMemoryManager()
    manager.write("mission-1", "planner", "plan", "draft")
    manager.write("mission-1", "planner", "plan", "final")

    rollback = manager.rollback("mission-1", "planner", "plan", version=1)

    assert rollback.version == 3
    assert rollback.value == "draft"
    assert manager.read("mission-1", "planner", "plan") == "draft"
    assert [version.value for version in manager.versions("mission-1", "plan")] == [
        "draft",
        "final",
        "draft",
    ]


def test_shared_memory_manager_blocks_stale_version_writes():
    manager = SharedMemoryManager()
    manager.write("mission-1", "planner", "plan", "draft", expected_version=0)

    with pytest.raises(SharedMemoryConflictError) as exc:
        manager.write("mission-1", "executor", "plan", "other", expected_version=0)

    assert "expected version 0" in str(exc.value)
    assert manager.read("mission-1", "planner", "plan") == "draft"


def test_shared_memory_manager_detects_memory_conflicts():
    manager = SharedMemoryManager()
    manager.write("mission-1", "planner", "plan", "draft")
    manager.write("mission-1", "executor", "plan", "alternate")
    manager.write("mission-1", "reviewer", "notes", "same")
    manager.write("mission-1", "planner", "notes", "same")

    conflicts = manager.detect_conflicts("mission-1")

    assert len(conflicts) == 1
    assert conflicts[0].key == "plan"
    assert conflicts[0].base_version == 0
    assert conflicts[0].values == {
        "planner": "draft",
        "executor": "alternate",
    }


def test_shared_memory_manager_returns_default_for_missing_key():
    manager = SharedMemoryManager()

    assert manager.read("mission-1", "planner", "missing", default="none") == "none"
    assert manager.versions("mission-1", "missing") == []
    assert manager.latest("mission-1", "missing") is None
