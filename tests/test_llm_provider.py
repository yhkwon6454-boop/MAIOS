from types import SimpleNamespace

from maios.adapters.llm_provider import (
    BaseLLMProvider,
    ClaudeProvider,
    GeminiProvider,
    MockGPTClient,
    OpenAIProvider,
    create_llm_provider,
)
from maios.config import MAIOSConfig, load_config


class FakeOpenAIResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="openai output")


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeOpenAIResponses()


class FakeClaudeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text="claude output")])


class FakeClaudeClient:
    def __init__(self):
        self.messages = FakeClaudeMessages()


class FakeGeminiModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text="gemini output")


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeGeminiModels()


def test_mock_provider_is_base_provider_and_runs_offline():
    provider = MockGPTClient()

    assert isinstance(provider, BaseLLMProvider)
    assert provider.generate("prompt") == "Mock GPT response: prompt"


def test_create_llm_provider_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("MAIOS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MAIOS_MODEL", raising=False)

    provider = create_llm_provider(load_config())

    assert isinstance(provider, MockGPTClient)


def test_create_llm_provider_selects_openai():
    config = MAIOSConfig(model_provider="openai", openai_model="gpt-test")
    provider = create_llm_provider(config=config, model="gpt-override")

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-override"


def test_create_llm_provider_selects_claude_with_injected_client():
    config = MAIOSConfig(model_provider="claude", claude_model="claude-test")
    provider = ClaudeProvider(config=config, client=FakeClaudeClient())

    result = provider.generate("hello")

    assert result == "claude output"
    assert provider.client.messages.calls == [
        {
            "model": "claude-test",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": "hello"}],
        }
    ]


def test_create_llm_provider_selects_gemini_with_injected_client():
    config = MAIOSConfig(model_provider="gemini", gemini_model="gemini-test")
    provider = GeminiProvider(config=config, client=FakeGeminiClient())

    result = provider.generate("hello")

    assert result == "gemini output"
    assert provider.client.models.calls == [
        {
            "model": "gemini-test",
            "contents": "hello",
        }
    ]


def test_openai_provider_uses_injected_client_without_api_key():
    client = FakeOpenAIClient()
    provider = OpenAIProvider(
        config=MAIOSConfig(model_provider="openai", openai_model="gpt-test"),
        client=client,
    )

    result = provider.generate("hello")

    assert result == "openai output"
    assert client.responses.calls == [
        {
            "model": "gpt-test",
            "input": "hello",
        }
    ]


def test_create_llm_provider_rejects_unknown_provider():
    try:
        create_llm_provider(MAIOSConfig(model_provider="unknown"))
    except ValueError as exc:
        assert str(exc) == "Unsupported LLM provider: unknown"
    else:
        raise AssertionError("Expected unsupported provider to fail.")
