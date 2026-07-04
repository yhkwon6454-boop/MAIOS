from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from maios.plugins.base import BasePlugin


class PluginManager:
    """Loads and registers MAIOS extension plugins."""

    def __init__(self, plugin_dir: str | Path = "plugins") -> None:
        self.plugin_dir = Path(plugin_dir)
        self.plugins: dict[str, BasePlugin | ModuleType] = {}
        self.agents: dict[str, Any] = {}
        self.tools: dict[str, Any] = {}
        self.providers: dict[str, Any] = {}
        self.memory_modules: dict[str, Any] = {}

    def register_plugin(self, plugin: BasePlugin | ModuleType) -> None:
        name = getattr(plugin, "name", None)
        if not name:
            name = plugin.__name__ if isinstance(plugin, ModuleType) else plugin.__class__.__name__
        if isinstance(plugin, BasePlugin):
            plugin.register(self)
        elif hasattr(plugin, "register"):
            plugin.register(self)
        else:
            raise ValueError(f"Plugin does not expose register(): {name}")

        self.plugins[name] = plugin

    def register_agent(self, name: str, agent: Any) -> None:
        self._require_name(name, "agent")
        self.agents[name] = agent

    def register_tool(self, name: str, tool: Any) -> None:
        self._require_name(name, "tool")
        self.tools[name] = tool

    def register_provider(self, name: str, provider: Any) -> None:
        self._require_name(name, "provider")
        self.providers[name] = provider

    def register_memory_module(self, name: str, memory_module: Any) -> None:
        self._require_name(name, "memory module")
        self.memory_modules[name] = memory_module

    def get_agent(self, name: str) -> Any | None:
        return self.agents.get(name)

    def get_tool(self, name: str) -> Any | None:
        return self.tools.get(name)

    def get_provider(self, name: str) -> Any | None:
        return self.providers.get(name)

    def get_memory_module(self, name: str) -> Any | None:
        return self.memory_modules.get(name)

    def load_plugins(self) -> list[str]:
        if not self.plugin_dir.exists():
            return []

        loaded: list[str] = []
        for path in sorted(self.plugin_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module = self._load_module(path)
            self.register_plugin(module)
            loaded.append(getattr(module, "name", None) or module.__name__)

        return loaded

    def auto_load(self) -> list[str]:
        return self.load_plugins()

    def summary(self) -> dict[str, list[str]]:
        return {
            "plugins": sorted(self.plugins),
            "agents": sorted(self.agents),
            "tools": sorted(self.tools),
            "providers": sorted(self.providers),
            "memory_modules": sorted(self.memory_modules),
        }

    def _load_module(self, path: Path) -> ModuleType:
        module_name = f"maios_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load plugin: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _require_name(self, name: str, kind: str) -> None:
        if not name:
            raise ValueError(f"Plugin {kind} name is required.")
