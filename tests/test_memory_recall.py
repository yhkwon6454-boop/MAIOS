from __future__ import annotations

from maios.adapters.llm_provider import BaseLLMProvider
from maios.kernel import CognitiveLoop, MemoryRecall, Workspace
from maios.knowledge import KnowledgeGraph


class ScriptedProvider(BaseLLMProvider):
    name = "scripted"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def _graph_with_knowledge() -> KnowledgeGraph:
    graph = KnowledgeGraph()
    graph.add_node(
        title="Drone defense study",
        content="Layered jamming plus interceptor drones proved most effective.",
        node_type="experience",
    )
    graph.add_node(
        title="World State: WM-1",
        content="{'noise': 'drone defense state dump'}",
        node_type="world_state",
    )
    return graph


def test_memory_recall_without_graph_is_empty():
    recall = MemoryRecall().recall("anything")

    assert not recall
    assert recall.entries == ()


def test_memory_recall_returns_relevant_entries_and_skips_state_dumps():
    recall = MemoryRecall(_graph_with_knowledge()).recall("drone defense tactics")

    assert len(recall.entries) == 1
    assert recall.entries[0].startswith("Drone defense study:")
    assert "jamming" in recall.entries[0]


def test_memory_recall_caps_entries_at_top_k():
    graph = KnowledgeGraph()
    for index in range(4):
        graph.add_node(
            title=f"Drone note {index}",
            content=f"Drone observation number {index}.",
            node_type="concept",
            merge_duplicates=False,
        )

    recall = MemoryRecall(graph, top_k=2).recall("drone observation")

    assert len(recall.entries) == 2
    assert len(recall.node_ids) == 2


def test_memory_recall_trims_long_content():
    graph = KnowledgeGraph()
    graph.add_node(title="Long note", content="drone " * 100, node_type="concept")

    recall = MemoryRecall(graph, max_chars=50).recall("drone")

    assert recall.entries[0].endswith("...")
    assert len(recall.entries[0]) < 80


def test_understand_phase_injects_recalled_knowledge():
    loop = CognitiveLoop(knowledge_graph=_graph_with_knowledge())

    cycle = loop.run_cycle("Plan drone defense drills")

    understand = cycle.phases[1]
    assert any("Drone defense study" in entry for entry in understand.data["recalled"])


def test_recalled_knowledge_reaches_interpreter_and_executor_prompts():
    provider = ScriptedProvider(
        [
            "Understood with memory.",
            "Executed with memory.",
            "Reflected.\n- Lesson kept.",
        ]
    )
    loop = CognitiveLoop(knowledge_graph=_graph_with_knowledge(), llm_provider=provider)

    cycle = loop.run_cycle("Plan drone defense drills")

    assert cycle.status == "COMPLETED"
    understand_prompt, act_prompt = provider.prompts[0], provider.prompts[1]
    assert "Relevant memories" in understand_prompt
    assert "Drone defense study" in understand_prompt
    assert "Relevant memories from earlier work" in act_prompt
    assert "Drone defense study" in act_prompt


def test_prior_lessons_flow_into_next_pursuit_prompt(tmp_path):
    space = Workspace(tmp_path / "space")

    first_provider = ScriptedProvider(["Seen.", "Done.", "Fine.\n- Always cite sources."])
    first = space.build_foundation(llm_provider=first_provider)
    first.pursue("Research drone doctrine")
    space.save(first)

    second_provider = ScriptedProvider(["Seen again.", "Done again.", "Fine.\n- Another lesson."])
    second = space.build_foundation(llm_provider=second_provider)
    pursuit = second.pursue("Write the drone doctrine memo")

    act_prompt = second_provider.prompts[1]
    assert "Lessons from previous pursuits" in act_prompt
    assert "Always cite sources." in act_prompt
    assert pursuit.status == "COMPLETED"


def test_cross_session_recall_references_previous_experience(tmp_path):
    space = Workspace(tmp_path / "space")

    first = space.build_foundation()
    first.pursue("Study drone defense doctrine")
    space.save(first)

    second = space.build_foundation()
    cycles_before = len(second.cognitive_loop.cycles)
    second.pursue("Plan drone defense training")
    cycle = second.cognitive_loop.cycles[cycles_before]

    recalled = cycle.phases[1].data.get("recalled", [])
    assert any("drone defense" in entry.lower() for entry in recalled)


def test_shell_prints_recall_lines(tmp_path):
    from maios.shell import MAIOSShell

    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation()
    foundation.knowledge_graph.add_node(
        title="Budget rules",
        content="Purchases above threshold require approval.",
        node_type="concept",
    )
    outputs: list[str] = []
    lines = iter(["Review the budget rules", "/exit"])
    MAIOSShell(
        foundation,
        space,
        input_fn=lambda prompt: next(lines),
        output_fn=outputs.append,
    ).run()

    assert any(line.strip().startswith("recall: Budget rules") for line in outputs)
