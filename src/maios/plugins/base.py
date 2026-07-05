from __future__ import annotations

from abc import ABC, abstractmethod


class BasePlugin(ABC):
    name: str
    version: str = "1.0.0"

    @abstractmethod
    def register(self, plugin_manager) -> None:
        pass
