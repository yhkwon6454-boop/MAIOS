from __future__ import annotations

from maios.plugins import BasePlugin, PluginManager
from maios.tools import BaseTool, ToolResult


class DemoTool(BaseTool):
    name = "demo"
    description = "Demo plugin tool."

    def execute(self, input_data):
        return ToolResult(success=True, output=f"demo:{input_data.get('value', '')}")


class DemoPlugin(BasePlugin):
    name = "demo_plugin"
    version = "0.1.0"

    def register(self, plugin_manager):
        plugin_manager.register_tool("demo", DemoTool())


def main() -> None:
    manager = PluginManager()
    manager.register_plugin(DemoPlugin())
    result = manager.get_tool("demo").execute({"value": "ok"})
    print(manager.summary())
    print(result.output)


if __name__ == "__main__":
    main()
