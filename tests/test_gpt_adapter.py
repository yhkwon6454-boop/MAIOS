from types import SimpleNamespace

from maios.adapters.gpt_adapter import GPTAdapter, OpenAIGPTClient
from maios.config import MAIOSConfig
from maios.runtime.models import CognitivePacket


class FakeLLMClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "generated response"


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="sdk response")


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_gpt_adapter_preserves_generate_client_api():
    client = FakeLLMClient()
    adapter = GPTAdapter(client)
    packet = CognitivePacket(
        process_id="P-1",
        instruction="Analyze the mission.",
        strategy=["OODA", "Risk Analysis"],
        required_memory=["doctrine"],
        output_format="brief",
    )

    result = adapter.execute(packet, {"doctrine": "Use mission command."})

    assert result == "generated response"
    assert len(client.prompts) == 1
    prompt = client.prompts[0]
    assert "Analyze the mission." in prompt
    assert "OODA, Risk Analysis" in prompt
    assert "- doctrine: Use mission command." in prompt
    assert "brief" in prompt


def test_openai_gpt_client_uses_responses_api():
    openai_client = FakeOpenAIClient()
    client = OpenAIGPTClient(
        config=MAIOSConfig(openai_api_key="test-key", openai_model="gpt-test"),
        openai_client=openai_client,
    )

    result = client.generate("hello")

    assert result == "sdk response"
    assert openai_client.responses.calls == [
        {
            "model": "gpt-test",
            "input": "hello",
        }
    ]


def test_openai_gpt_client_extracts_text_from_nested_response():
    openai_client = FakeOpenAIClient()
    openai_client.responses.create = lambda **_: {
        "output": [
            {
                "content": [
                    {
                        "text": "nested response",
                    }
                ]
            }
        ]
    }
    client = OpenAIGPTClient(openai_client=openai_client)

    assert client.generate("hello") == "nested response"


def test_gpt_adapter_builds_default_openai_client(monkeypatch):
    created = {}

    class FakeDefaultClient:
        def __init__(self, config=None, model=None):
            created["config"] = config
            created["model"] = model

        def generate(self, prompt: str) -> str:
            return prompt

    monkeypatch.setattr("maios.adapters.gpt_adapter.OpenAIGPTClient", FakeDefaultClient)

    config = MAIOSConfig(openai_model="gpt-test")
    adapter = GPTAdapter(config=config, model="gpt-override")

    assert isinstance(adapter.client, FakeDefaultClient)
    assert created == {"config": config, "model": "gpt-override"}
