from maios.adapters.llm_provider import BaseLLMProvider
from maios.agents import Agent
from maios.kernel.memory_kernel import MemoryKernel
from maios.plugins import BasePlugin, PluginManager
from maios.tools import BaseTool, ToolResult


class TestAgent(Agent):
    name = "test_agent"

    def execute(self, context):
        return {**context, "agent": True}


class TestTool(BaseTool):
    name = "test_tool"

    def execute(self, input_data):
        return ToolResult(success=True, output=input_data["value"])


class TestProvider(BaseLLMProvider):
    name = "test_provider"

    def generate(self, prompt):
        return f"provider:{prompt}"


class TestPlugin(BasePlugin):
    name = "test_plugin"

    def register(self, plugin_manager):
        plugin_manager.register_agent("test_agent", TestAgent())
        plugin_manager.register_tool("test_tool", TestTool())
        plugin_manager.register_provider("test_provider", TestProvider())
        plugin_manager.register_memory_module("test_memory", MemoryKernel())


def test_plugin_manager_registers_plugin_components():
    manager = PluginManager()

    manager.register_plugin(TestPlugin())

    assert manager.get_agent("test_agent").execute({})["agent"] is True
    assert manager.get_tool("test_tool").execute({"value": "ok"}).output == "ok"
    assert manager.get_provider("test_provider").generate("x") == "provider:x"
    assert isinstance(manager.get_memory_module("test_memory"), MemoryKernel)
    assert manager.summary() == {
        "plugins": ["test_plugin"],
        "agents": ["test_agent"],
        "tools": ["test_tool"],
        "providers": ["test_provider"],
        "memory_modules": ["test_memory"],
    }


def test_plugin_manager_loads_plugins_from_directory(tmp_path):
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text(
        """
name = "sample_plugin"

class SampleTool:
    name = "sample_tool"
    def execute(self, input_data):
        return input_data

def register(plugin_manager):
    plugin_manager.register_tool("sample_tool", SampleTool())
    plugin_manager.register_provider("sample_provider", object())
""".strip(),
        encoding="utf-8",
    )
    manager = PluginManager(tmp_path)

    loaded = manager.load_plugins()

    assert loaded == ["sample_plugin"]
    assert manager.get_tool("sample_tool").execute({"ok": True}) == {"ok": True}
    assert manager.get_provider("sample_provider") is not None
    assert manager.summary()["plugins"] == ["sample_plugin"]


def test_plugin_manager_ignores_private_plugin_files(tmp_path):
    (tmp_path / "_private.py").write_text(
        "def register(plugin_manager):\n    plugin_manager.register_tool('bad', object())\n",
        encoding="utf-8",
    )
    manager = PluginManager(tmp_path)

    assert manager.auto_load() == []
    assert manager.summary()["tools"] == []


def test_plugin_manager_missing_directory_loads_no_plugins(tmp_path):
    manager = PluginManager(tmp_path / "missing")

    assert manager.load_plugins() == []
    assert manager.summary()["plugins"] == []


def test_plugin_manager_rejects_plugin_without_register(tmp_path):
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text("name = 'bad_plugin'\n", encoding="utf-8")
    manager = PluginManager(tmp_path)

    try:
        manager.load_plugins()
    except ValueError as exc:
        assert "Plugin does not expose register()" in str(exc)
    else:
        raise AssertionError("Expected invalid plugin to fail.")


def test_plugin_manager_validates_component_names():
    manager = PluginManager()

    for method in [
        manager.register_agent,
        manager.register_tool,
        manager.register_provider,
        manager.register_memory_module,
    ]:
        try:
            method("", object())
        except ValueError as exc:
            assert "name is required" in str(exc)
        else:
            raise AssertionError("Expected empty component name to fail.")
