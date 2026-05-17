"""LLM connector package.

Exports all connectors and the registry for pluggable LLM backends.
"""

from src.connectors.llm.anthropic import AnthropicConnector
from src.connectors.llm.base import BusinessContext, ConnectorError, LLMConnector, PitchResult
from src.connectors.llm.local import LocalConnector
from src.connectors.llm.ollama import OllamaConnector
from src.connectors.llm.openai import OpenAIConnector
from src.connectors.llm.openrouter import OpenRouterConnector
from src.connectors.llm.registry import CONNECTORS, ConnectorRegistry

__all__ = [
    "AnthropicConnector",
    "BusinessContext",
    "ConnectorError",
    "ConnectorRegistry",
    "CONNECTORS",
    "LLMConnector",
    "LocalConnector",
    "OllamaConnector",
    "OpenAIConnector",
    "OpenRouterConnector",
    "PitchResult",
]
