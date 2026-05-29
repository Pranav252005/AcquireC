"""Connector registry for discovering and instantiating LLM backends."""

from __future__ import annotations

from src.connectors.llm.anthropic import AnthropicConnector
from src.connectors.llm.base import LLMConnector
from src.connectors.llm.kimi import KimiConnector
from src.connectors.llm.local import LocalConnector
from src.connectors.llm.ollama import OllamaConnector
from src.connectors.llm.openai import OpenAIConnector
from src.connectors.llm.openrouter import OpenRouterConnector

CONNECTORS: dict[str, type[LLMConnector]] = {
    "local": LocalConnector,
    "openai": OpenAIConnector,
    "anthropic": AnthropicConnector,
    "ollama": OllamaConnector,
    "openrouter": OpenRouterConnector,
    "kimi": KimiConnector,
}


class ConnectorRegistry:
    """Registry that manages singleton instances of LLM connectors.

    .. note::
        This registry is not thread-safe. Concurrent ``get()`` or
        ``list_available()`` calls from multiple threads may race on
        ``_instances``. Add a threading.Lock if used with Celery or
        other multi-threaded workers.
    """

    def __init__(self) -> None:
        self._instances: dict[str, LLMConnector] = {}

    def get(self, name: str) -> LLMConnector:
        """Return a connector instance by name.

        Args:
            name: Connector key (e.g. 'local', 'openai').

        Returns:
            Instantiated LLMConnector subclass.

        Raises:
            ValueError: If the connector name is unknown.
        """
        if name not in CONNECTORS:
            raise ValueError(f"Unknown connector: {name}")
        if name not in self._instances:
            self._instances[name] = CONNECTORS[name]()
        return self._instances[name]

    def list_available(self) -> list[str]:
        """List connectors whose can_use() returns True."""
        return [name for name, cls in CONNECTORS.items() if cls.can_use()]
