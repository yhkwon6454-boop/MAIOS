from __future__ import annotations

import subprocess
from types import SimpleNamespace

from maios.adapters.llm_provider import ClaudeProvider, GeminiProvider, OpenAIProvider
from maios.kernel.memory_context import MemoryContextBuilder
from maios.kernel.quality_kernel import QualityKernel
from maios.knowledge.store import InMemoryKnowledgeStore, KnowledgeStore
from maios.reasoning.engine import ReasoningEngine
from maios.runtime.loader import load_mission
from maios.runtime.models import CognitivePacket, Mission, MissionType, Status
from maios.runtime.plan import Plan
from maios.scheduler.mission_scheduler import MissionScheduler
from maios.service.api import _to_jsonable
from maios.tools import GitTool, PythonTool, ShellTool, ToolRegistry, ToolResult
from maios.tools.base import normalize_output


def _tree_names(tree):
    names = []
    nodes = list(tree.root_nodes)
    while nodes:
        node = nodes.pop(0)
        names.append(node.process.name)
        nodes.extend(node.children)
    return names


def test_scheduler_covers_specialized_mission_types():
    scheduler = MissionScheduler()

    military = scheduler.schedule(
        Mission("Military", "Assess", mission_type=MissionType.MILITARY_RESEARCH)
    )
    writing = scheduler.schedule(Mission("Writing", "Draft", mission_type=MissionType.WRITING))
    translation = scheduler.schedule(
        Mission("Translation", "Translate", mission_type=MissionType.TRANSLATION)
    )

    assert _tree_names(military) == [
        "Threat Research",
        "Operational Impact Analysis",
        "Response Option Development",
        "Final Military Brief",
    ]
    assert _tree_names(writing) == ["Outline", "Draft", "Revision"]
    assert _tree_names(translation) == ["Terminology Pass", "Translation Pass", "Review Pass"]


def test_loader_reads_json_and_yaml_missions(tmp_path):
    json_file = tmp_path / "mission.json"
    json_file.write_text('{"title": "JSON", "objective": "Load json"}', encoding="utf-8")
    yaml_file = tmp_path / "mission.yaml"
    yaml_file.write_text(
        """
title: YAML
objective: Load yaml
constraints:
  - fast
  - local
""".strip(),
        encoding="utf-8",
    )

    assert load_mission(json_file).title == "JSON"
    yaml_mission = load_mission(yaml_file)
    assert yaml_mission.title == "YAML"
    assert yaml_mission.constraints == ["fast", "local"]


def test_quality_kernel_failure_paths():
    kernel = QualityKernel()

    result = kernel.execute({"status": "PENDING", "cognitive_result": ""})
    qa_result = kernel.evaluate(["", "", "ok"])

    assert not result["passed"]
    assert result["score"] == 0
    assert not kernel.validate(result)
    assert qa_result.status == Status.NEEDS_REVISION
    assert qa_result.issues == [
        "Packet output is empty: 0",
        "Packet output is empty: 1",
    ]
    assert kernel.shutdown()


def test_memory_context_empty_and_document_paths():
    builder = MemoryContextBuilder()

    assert builder.summarize([], [], []) == ""
    assert builder.build_context("", [], []) == {}
    assert builder.inject_context("prompt", {"empty": ""}) == "prompt"
    assert builder._section("Empty", []) == ""


def test_knowledge_store_update_delete_and_in_memory_store(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    document_id = store.add("alpha", {"kind": "note"})

    updated = store.update(document_id, content="beta", metadata={"kind": "updated"})

    assert updated is not None
    assert updated.content == "beta"
    assert store.delete(document_id)
    assert not store.delete("missing")
    assert not store.exists(document_id)

    memory_store = InMemoryKnowledgeStore()
    memory_store.store("a", "1")
    assert memory_store.retrieve(["a", "b"]) == {"a": "1"}
    assert memory_store.get("missing", "fallback") == "fallback"
    assert memory_store.exists("a")
    assert memory_store.count() == 1


def test_llm_provider_response_fallbacks():
    openai = OpenAIProvider(client=SimpleNamespace(responses=SimpleNamespace()))
    claude = ClaudeProvider(client=SimpleNamespace(messages=SimpleNamespace()))
    gemini = GeminiProvider(
        client=SimpleNamespace(
            models=SimpleNamespace(
                generate_content=lambda **kwargs: {"text": "dict gemini"},
            )
        )
    )

    openai_response = {
        "output": [
            {
                "content": [
                    {
                        "text": "nested openai",
                    }
                ]
            }
        ]
    }
    assert openai._extract_text(openai_response) == "nested openai"
    assert openai._extract_text({"unknown": "value"}) == "{'unknown': 'value'}"
    assert claude._extract_text({"content": [{"text": "dict claude"}]}) == "dict claude"
    assert gemini.generate("hello") == "dict gemini"


def test_tool_timeout_and_output_normalization(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="x", timeout=1, output=b"partial", stderr=b"err")

    assert normalize_output(b"bytes") == "bytes"
    assert normalize_output(None) == ""

    monkeypatch.setattr("maios.tools.shell_tool.subprocess.run", raise_timeout)
    shell_result = ShellTool().execute({"command": "slow", "timeout": 1})
    assert not shell_result.success
    assert shell_result.output == "partial"

    monkeypatch.setattr("maios.tools.python_tool.subprocess.run", raise_timeout)
    python_result = PythonTool().execute({"code": "print('slow')", "timeout": 1})
    assert not python_result.success
    assert python_result.output == "partial"

    monkeypatch.setattr("maios.tools.git_tool.subprocess.run", raise_timeout)
    git_result = GitTool().execute({"args": "status", "timeout": 1})
    assert not git_result.success
    assert git_result.output == "partial"


def test_reasoning_engine_fallback_and_error_observation_paths():
    class Model:
        def __init__(self):
            self.calls = 0

        def execute(self, packet, memory_context):
            self.calls += 1
            if self.calls == 1:
                return '```json\n{"tool_name": "missing", "tool_input": "value"}\n```'
            return '{"answer": "done"}'

    registry = ToolRegistry()
    result = ReasoningEngine(Model(), registry, max_iterations=2).execute(
        CognitivePacket(process_id="P-1", instruction="Use a tool")
    )

    assert result.completed
    assert result.final_answer == "done"
    assert result.steps[2].observation == ToolResult(
        success=False,
        error="Tool not found: missing",
        metadata={"tool": "missing"},
    )


def test_service_jsonable_handles_dicts_lists_enums_and_dataclasses():
    value = {
        "status": Status.COMPLETED,
        "plan": Plan(objective="x", tasks=["a"]),
        "items": [Status.READY],
    }

    assert _to_jsonable(value) == {
        "status": "COMPLETED",
        "plan": {
            "objective": "x",
            "tasks": ["a"],
            "risk": "MEDIUM",
            "priority": "NORMAL",
            "output": "",
        },
        "items": ["READY"],
    }
