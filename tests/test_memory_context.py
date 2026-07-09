from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.kernel.memory_context import MemoryContextBuilder
from maios.kernel.memory_kernel import MemoryKernel
from maios.retrieval import Document
from maios.runtime.models import Mission


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "memory-aware output"


def test_memory_context_builder_summarizes_memory_layers():
    builder = MemoryContextBuilder()
    summary = builder.summarize(
        ["short note"],
        [Document("long note")],
        [{"role": "user", "content": "hello"}],
    )

    assert "Short-term memory" in summary
    assert "short note" in summary
    assert "Long-term memory" in summary
    assert "long note" in summary
    assert "Conversation history" in summary
    assert "user: hello" in summary


def test_memory_kernel_retrieve_context_includes_history_and_query():
    kernel = MemoryKernel()
    kernel.remember_short_term("mission context note")
    kernel.remember_conversation("user", "previous question")

    context = kernel.retrieve_context("mission")

    assert context["query"] == "mission"
    assert "mission context note" in context["retrieved_memory"]
    assert context["conversation_history"] == "user: previous question"


def test_memory_kernel_injects_context_into_prompt():
    kernel = MemoryKernel()
    kernel.remember_short_term("alpha mission memory")

    prompt = kernel.inject_context("Answer the mission.", query="alpha")

    assert prompt.startswith("[MAIOS Memory Context]")
    assert "alpha mission memory" in prompt
    assert "Answer the mission." in prompt


def test_gpt_adapter_automatically_injects_memory_context():
    client = FakeClient()
    memory = MemoryKernel()
    memory.remember_short_term("doctrine memory")
    adapter = GPTAdapter(client=client, memory_kernel=memory)

    result = adapter.generate("Use doctrine.", memory_context={"manual": "style guide"})

    assert result == "memory-aware output"
    assert "[MAIOS Memory Context]" in client.prompts[0]
    assert "doctrine memory" in client.prompts[0]
    assert "manual: style guide" in client.prompts[0]
    assert "Use doctrine." in client.prompts[0]


def test_runtime_orchestrator_uses_memory_before_llm_call():
    client = FakeClient()
    adapter = GPTAdapter(client=client)
    orchestrator = RuntimeOrchestrator(gpt_adapter=adapter)
    mission = Mission(title="Memory Runtime", objective="Use mission memory.")

    result = orchestrator.run(mission)

    assert result.model_output == "memory-aware output"
    assert adapter.memory_kernel is orchestrator.memory_agent.memory_kernel
    assert "[MAIOS Memory Context]" in client.prompts[0]
    assert "Use mission memory." in client.prompts[0]
    assert orchestrator.memory_agent.memory_kernel.conversation_history == [
        {"role": "assistant", "content": "memory-aware output"}
    ]
