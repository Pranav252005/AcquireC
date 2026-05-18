"""Tests for LLM connector infrastructure."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.llm import (
    AnthropicConnector,
    BusinessContext,
    ConnectorError,
    ConnectorRegistry,
    LocalConnector,
    OllamaConnector,
    OpenAIConnector,
    OpenRouterConnector,
    PitchResult,
)
from src.connectors.llm.registry import CONNECTORS


class TestBusinessContext:
    """Tests for the BusinessContext dataclass."""

    def test_creation(self) -> None:
        """Should create a BusinessContext with all fields."""
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=5,
            city="Mumbai",
            name="Test Cafe",
            has_website=True,
            website_issues=["slow_load"],
        )
        assert ctx.business_type == "cafe"
        assert ctx.city == "Mumbai"
        assert ctx.has_website is True
        assert ctx.website_issues == ["slow_load"]

    def test_optional_fields_none(self) -> None:
        """Should allow None for optional fields."""
        ctx = BusinessContext(
            business_type="retail",
            maturity_stage=None,
            website_score=None,
            years_in_business=None,
            city="Delhi",
            name="Test Shop",
            has_website=False,
            website_issues=[],
        )
        assert ctx.maturity_stage is None
        assert ctx.website_score is None
        assert ctx.years_in_business is None


class TestPitchResult:
    """Tests for the PitchResult dataclass."""

    def test_creation(self) -> None:
        """Should create a PitchResult with all fields."""
        result = PitchResult(
            pitch_text="Hello!",
            membership_idea="Club",
            website_benefits="Fast",
            model_used="local",
        )
        assert result.pitch_text == "Hello!"
        assert result.model_used == "local"


class TestConnectorRegistry:
    """Tests for ConnectorRegistry."""

    def test_get_local_returns_local_connector(self) -> None:
        """Registry.get('local') should return a LocalConnector instance."""
        registry = ConnectorRegistry()
        connector = registry.get("local")
        assert isinstance(connector, LocalConnector)

    def test_get_openai_returns_openai_connector(self) -> None:
        """Registry.get('openai') should return an OpenAIConnector instance."""
        registry = ConnectorRegistry()
        connector = registry.get("openai")
        assert isinstance(connector, OpenAIConnector)

    def test_get_unknown_raises_value_error(self) -> None:
        """Registry.get('unknown') should raise ValueError."""
        registry = ConnectorRegistry()
        with pytest.raises(ValueError, match="Unknown connector: unknown"):
            registry.get("unknown")

    def test_get_caches_instances(self) -> None:
        """Registry should return the same instance on repeated gets."""
        registry = ConnectorRegistry()
        c1 = registry.get("local")
        c2 = registry.get("local")
        assert c1 is c2

    def test_list_available_filters_by_health(self, monkeypatch) -> None:
        """list_available should only include connectors passing can_use."""
        registry = ConnectorRegistry()
        monkeypatch.setattr(LocalConnector, "can_use", staticmethod(lambda: True))
        monkeypatch.setattr(OpenAIConnector, "can_use", staticmethod(lambda: False))
        monkeypatch.setattr(AnthropicConnector, "can_use", staticmethod(lambda: True))
        monkeypatch.setattr(OllamaConnector, "can_use", staticmethod(lambda: False))
        monkeypatch.setattr(OpenRouterConnector, "can_use", staticmethod(lambda: False))

        available = registry.list_available()
        assert "local" in available
        assert "anthropic" in available
        assert "openai" not in available
        assert "ollama" not in available
        assert "openrouter" not in available


class TestLocalConnector:
    """Tests for LocalConnector."""

    def test_health_check_when_model_missing(self, monkeypatch) -> None:
        """health_check should return False when model file does not exist."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        conn = LocalConnector()
        assert conn.health_check() is False

    def test_health_check_when_model_present(self, monkeypatch) -> None:
        """health_check should return True when model file exists."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        conn = LocalConnector()
        assert conn.health_check() is True

    def test_can_use_when_model_present(self, monkeypatch) -> None:
        """can_use should return True when model file exists."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        assert LocalConnector.can_use() is True

    def test_can_use_when_model_missing(self, monkeypatch) -> None:
        """can_use should return False when model file does not exist."""
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        assert LocalConnector.can_use() is False

    def test_generate_pitch_with_grammar(self, monkeypatch) -> None:
        """generate_pitch should return PitchResult when model outputs valid JSON."""
        mock_llm = MagicMock()
        mock_llm.return_value = {
            "choices": [{"text": json.dumps({
                "pitch_text": "Great cafe!",
                "membership_idea": "Coffee Club",
                "website_benefits": "Online menu",
                "model_used": "local",
            })}],
        }
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr("llama_cpp.Llama", lambda **kwargs: mock_llm)

        conn = LocalConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=3,
            city="Mumbai",
            name="Alpha Cafe",
            has_website=False,
            website_issues=["slow_load"],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Great cafe!"
        assert result.membership_idea == "Coffee Club"
        assert result.model_used == "local"

    def test_generate_pitch_fallback_without_grammar(self, monkeypatch) -> None:
        """generate_pitch should fall back to plain text when grammar fails."""
        mock_llm = MagicMock()
        # First call with grammar raises, second succeeds
        mock_llm.side_effect = [
            Exception("grammar not supported"),
            {"choices": [{"text": json.dumps({
                "pitch_text": "Fallback pitch",
                "membership_idea": "Club",
                "website_benefits": "Benefits",
                "model_used": "local",
            })}]},
        ]
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr("llama_cpp.Llama", lambda **kwargs: mock_llm)

        conn = LocalConnector()
        ctx = BusinessContext(
            business_type="retail",
            maturity_stage=None,
            website_score=None,
            years_in_business=None,
            city="Delhi",
            name="Beta Shop",
            has_website=False,
            website_issues=[],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Fallback pitch"

    def test_generate_pitch_invalid_json_raises_error(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError for invalid JSON output."""
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": "not json"}]}
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr("llama_cpp.Llama", lambda **kwargs: mock_llm)

        conn = LocalConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage=None,
            website_score=None,
            years_in_business=None,
            city="Pune",
            name="Gamma",
            has_website=False,
            website_issues=[],
        )
        with pytest.raises(ConnectorError):
            conn.generate_pitch(ctx)

    def test_generate_pitch_with_preset(self, monkeypatch) -> None:
        """generate_pitch should respect preset system_prompt and tone."""
        mock_llm = MagicMock()
        mock_llm.return_value = {
            "choices": [{"text": json.dumps({
                "pitch_text": "Preset pitch",
                "membership_idea": "Club",
                "website_benefits": "Benefits",
                "model_used": "local",
            })}],
        }
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        monkeypatch.setattr("llama_cpp.Llama", lambda **kwargs: mock_llm)

        conn = LocalConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage=None,
            website_score=None,
            years_in_business=None,
            city="Pune",
            name="Gamma",
            has_website=False,
            website_issues=[],
        )
        preset = {"system_prompt": "Custom sys", "tone": "friendly"}
        result = conn.generate_pitch(ctx, preset)
        assert result.pitch_text == "Preset pitch"
        # Verify prompt was passed to llm with preset values
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert "Custom sys" in prompt
        assert "friendly" in prompt

    def test_detect_chat_format_from_filename(self, monkeypatch) -> None:
        """_detect_chat_format should infer format from model filename."""
        monkeypatch.setattr(
            "src.connectors.llm.local.get_settings",
            lambda: MagicMock(local_model_path="/models/Qwen-7B.gguf", llm_chat_format="generic"),
        )
        conn = LocalConnector()
        assert conn._detect_chat_format() == "qwen"

    def test_detect_chat_format_llama(self, monkeypatch) -> None:
        """_detect_chat_format should detect llama from filename."""
        monkeypatch.setattr(
            "src.connectors.llm.local.get_settings",
            lambda: MagicMock(local_model_path="/models/Meta-Llama-3-8B.gguf", llm_chat_format="generic"),
        )
        conn = LocalConnector()
        assert conn._detect_chat_format() == "llama"

    def test_detect_chat_format_fallback_to_config(self, monkeypatch) -> None:
        """_detect_chat_format should fall back to config when filename is ambiguous."""
        monkeypatch.setattr(
            "src.connectors.llm.local.get_settings",
            lambda: MagicMock(local_model_path="/models/unknown.gguf", llm_chat_format="chatml"),
        )
        conn = LocalConnector()
        assert conn._detect_chat_format() == "chatml"

    def test_detect_chat_format_defaults_to_generic(self, monkeypatch) -> None:
        """_detect_chat_format should default to generic for unknown models."""
        monkeypatch.setattr(
            "src.connectors.llm.local.get_settings",
            lambda: MagicMock(local_model_path="/models/unknown.gguf", llm_chat_format="generic"),
        )
        conn = LocalConnector()
        assert conn._detect_chat_format() == "generic"


class TestOpenAIConnector:
    """Tests for OpenAIConnector."""

    def test_health_check_with_key(self, monkeypatch) -> None:
        """health_check should return True when API key is set and valid."""
        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test"),
        )
        conn = OpenAIConnector()
        assert conn.health_check() is True

    def test_health_check_without_key(self, monkeypatch) -> None:
        """health_check should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key=""),
        )
        conn = OpenAIConnector()
        assert conn.health_check() is False

    def test_health_check_invalid_key_format(self, monkeypatch) -> None:
        """health_check should return False when API key has invalid format."""
        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="invalid"),
        )
        conn = OpenAIConnector()
        assert conn.health_check() is False

    def test_can_use_with_key(self, monkeypatch) -> None:
        """can_use should return True when API key is set."""
        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test"),
        )
        assert OpenAIConnector.can_use() is True

    def test_can_use_without_key(self, monkeypatch) -> None:
        """can_use should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key=""),
        )
        assert OpenAIConnector.can_use() is False

    def test_generate_pitch_returns_pitch_result(self, monkeypatch) -> None:
        """generate_pitch should return PitchResult when API responds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "pitch_text": "OpenAI pitch",
            "membership_idea": "Membership",
            "website_benefits": "Benefits",
            "model_used": "openai",
        })
        mock_client.chat.completions.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

        conn = OpenAIConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "OpenAI pitch"
        assert result.membership_idea == "Membership"
        assert result.model_used == "openai"

    def test_generate_pitch_with_preset(self, monkeypatch) -> None:
        """generate_pitch should respect preset model, system_prompt and tone."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "pitch_text": "Preset pitch",
            "membership_idea": "Membership",
            "website_benefits": "Benefits",
            "model_used": "openai",
        })
        mock_client.chat.completions.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

        conn = OpenAIConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        preset = {
            "model": "gpt-4o",
            "system_prompt": "Custom system prompt",
            "tone": "friendly",
            "timeout": 10.0,
        }
        result = conn.generate_pitch(ctx, preset)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Preset pitch"

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["timeout"] == 10.0
        messages = call_kwargs["messages"]
        assert messages[0]["content"] == "Custom system prompt Use a friendly tone."

    def test_generate_pitch_api_error(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError on openai.APIError."""
        from openai import APIError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            message="bad request",
            request=MagicMock(),
            body=None,
        )

        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

        conn = OpenAIConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        with pytest.raises(ConnectorError, match="OpenAI API request failed"):
            conn.generate_pitch(ctx)

    def test_generate_pitch_timeout(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError on openai.APITimeoutError."""
        from openai import APITimeoutError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            request=MagicMock(),
        )

        monkeypatch.setattr(
            "src.connectors.llm.openai.get_settings",
            lambda: MagicMock(openai_api_key="sk-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

        conn = OpenAIConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        with pytest.raises(ConnectorError, match="OpenAI API request timed out"):
            conn.generate_pitch(ctx)


class TestAnthropicConnector:
    """Tests for AnthropicConnector."""

    def test_health_check_with_key(self, monkeypatch) -> None:
        """health_check should return True when API key is set and valid."""
        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test"),
        )
        conn = AnthropicConnector()
        assert conn.health_check() is True

    def test_health_check_without_key(self, monkeypatch) -> None:
        """health_check should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key=""),
        )
        conn = AnthropicConnector()
        assert conn.health_check() is False

    def test_health_check_invalid_key_format(self, monkeypatch) -> None:
        """health_check should return False when API key has invalid format."""
        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="invalid"),
        )
        conn = AnthropicConnector()
        assert conn.health_check() is False

    def test_can_use_with_key(self, monkeypatch) -> None:
        """can_use should return True when API key is set."""
        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test"),
        )
        assert AnthropicConnector.can_use() is True

    def test_can_use_without_key(self, monkeypatch) -> None:
        """can_use should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key=""),
        )
        assert AnthropicConnector.can_use() is False

    def test_generate_pitch_returns_pitch_result(self, monkeypatch) -> None:
        """generate_pitch should return PitchResult when API responds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "pitch_text": "Anthropic pitch",
            "membership_idea": "Club",
            "website_benefits": "Benefits",
            "model_used": "anthropic",
        }))]
        mock_client.messages.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

        conn = AnthropicConnector()
        ctx = BusinessContext(
            business_type="salon",
            maturity_stage="mature",
            website_score="good",
            years_in_business=10,
            city="Bangalore",
            name="Elegant Salon",
            has_website=True,
            website_issues=[],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Anthropic pitch"
        assert result.model_used == "anthropic"

    def test_generate_pitch_with_preset(self, monkeypatch) -> None:
        """generate_pitch should respect preset model, system_prompt and tone."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "pitch_text": "Preset pitch",
            "membership_idea": "Club",
            "website_benefits": "Benefits",
            "model_used": "anthropic",
        }))]
        mock_client.messages.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

        conn = AnthropicConnector()
        ctx = BusinessContext(
            business_type="salon",
            maturity_stage="mature",
            website_score="good",
            years_in_business=10,
            city="Bangalore",
            name="Elegant Salon",
            has_website=True,
            website_issues=[],
        )
        preset = {
            "model": "claude-3-opus",
            "system_prompt": "Custom prompt",
            "tone": "casual",
            "timeout": 15.0,
        }
        result = conn.generate_pitch(ctx, preset)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Preset pitch"

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-opus"
        assert call_kwargs["timeout"] == 15.0
        assert call_kwargs["system"] == "Custom prompt"
        assert "casual" in call_kwargs["messages"][0]["content"]

    def test_generate_pitch_api_error(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError on anthropic.APIError."""
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="bad request",
            request=MagicMock(),
            body=None,
        )

        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

        conn = AnthropicConnector()
        ctx = BusinessContext(
            business_type="salon",
            maturity_stage="mature",
            website_score="good",
            years_in_business=10,
            city="Bangalore",
            name="Elegant Salon",
            has_website=True,
            website_issues=[],
        )
        with pytest.raises(ConnectorError, match="Anthropic API request failed"):
            conn.generate_pitch(ctx)

    def test_generate_pitch_timeout(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError on anthropic.APITimeoutError."""
        from anthropic import APITimeoutError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APITimeoutError(
            request=MagicMock(),
        )

        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

        conn = AnthropicConnector()
        ctx = BusinessContext(
            business_type="salon",
            maturity_stage="mature",
            website_score="good",
            years_in_business=10,
            city="Bangalore",
            name="Elegant Salon",
            has_website=True,
            website_issues=[],
        )
        with pytest.raises(ConnectorError, match="Anthropic API request timed out"):
            conn.generate_pitch(ctx)

    def test_generate_pitch_with_json_block(self, monkeypatch) -> None:
        """generate_pitch should extract JSON from markdown code blocks."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=(
            "```json\n"
            + json.dumps({
                "pitch_text": "Markdown pitch",
                "membership_idea": "Idea",
                "website_benefits": "Benefits",
                "model_used": "anthropic",
            })
            + "\n```"
        ))]
        mock_client.messages.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.anthropic.get_settings",
            lambda: MagicMock(anthropic_api_key="sk-ant-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

        conn = AnthropicConnector()
        ctx = BusinessContext(
            business_type="gym",
            maturity_stage="new",
            website_score="poor",
            years_in_business=1,
            city="Chennai",
            name="Fit Gym",
            has_website=False,
            website_issues=["no_ssl"],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Markdown pitch"


class TestOllamaConnector:
    """Tests for OllamaConnector."""

    def test_generate_pitch_returns_pitch_result(self, monkeypatch) -> None:
        """generate_pitch should return PitchResult on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps({
                "pitch_text": "Ollama pitch",
                "membership_idea": "Idea",
                "website_benefits": "Benefits",
                "model_used": "ollama",
            }),
        }
        mock_response.raise_for_status = MagicMock()
        monkeypatch.setattr("httpx.post", lambda *args, **kwargs: mock_response)
        monkeypatch.setattr(
            "src.connectors.llm.ollama.get_settings",
            lambda: MagicMock(ollama_url="http://localhost:11434", ollama_model="qwen2.5:9b"),
        )

        conn = OllamaConnector()
        ctx = BusinessContext(
            business_type="clinic",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=4,
            city="Hyderabad",
            name="Health Clinic",
            has_website=True,
            website_issues=["slow_load"],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "Ollama pitch"
        assert result.model_used == "ollama"

    def test_health_check_success(self, monkeypatch) -> None:
        """health_check should return True when server responds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        monkeypatch.setattr("httpx.get", lambda *args, **kwargs: mock_response)
        monkeypatch.setattr(
            "src.connectors.llm.ollama.get_settings",
            lambda: MagicMock(ollama_url="http://localhost:11434"),
        )
        conn = OllamaConnector()
        assert conn.health_check() is True

    def test_health_check_failure(self, monkeypatch) -> None:
        """health_check should return False when server is unreachable."""
        monkeypatch.setattr("httpx.get", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Connection refused")))
        monkeypatch.setattr(
            "src.connectors.llm.ollama.get_settings",
            lambda: MagicMock(ollama_url="http://localhost:11434"),
        )
        conn = OllamaConnector()
        assert conn.health_check() is False


class TestOpenRouterConnector:
    """Tests for OpenRouterConnector."""

    def test_health_check_with_key(self, monkeypatch) -> None:
        """health_check should return True when API key is set and valid."""
        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key="sk-or-test"),
        )
        conn = OpenRouterConnector()
        assert conn.health_check() is True

    def test_health_check_without_key(self, monkeypatch) -> None:
        """health_check should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key=""),
        )
        conn = OpenRouterConnector()
        assert conn.health_check() is False

    def test_can_use_with_key(self, monkeypatch) -> None:
        """can_use should return True when API key is set."""
        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key="sk-or-test"),
        )
        assert OpenRouterConnector.can_use() is True

    def test_can_use_without_key(self, monkeypatch) -> None:
        """can_use should return False when API key is empty."""
        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key=""),
        )
        assert OpenRouterConnector.can_use() is False

    def test_generate_pitch_returns_pitch_result(self, monkeypatch) -> None:
        """generate_pitch should return PitchResult when API responds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "pitch_text": "OpenRouter pitch",
            "membership_idea": "Membership",
            "website_benefits": "Benefits",
            "model_used": "openrouter",
        })
        mock_client.chat.completions.create.return_value = mock_response

        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key="sk-or-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key, base_url: mock_client)

        conn = OpenRouterConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        result = conn.generate_pitch(ctx)
        assert isinstance(result, PitchResult)
        assert result.pitch_text == "OpenRouter pitch"
        assert result.membership_idea == "Membership"
        assert result.model_used == "openrouter"

    def test_generate_pitch_api_error(self, monkeypatch) -> None:
        """generate_pitch should raise ConnectorError on APIError."""
        from openai import APIError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            message="bad request",
            request=MagicMock(),
            body=None,
        )

        monkeypatch.setattr(
            "src.connectors.llm.openrouter.get_settings",
            lambda: MagicMock(openrouter_api_key="sk-or-test", llm_timeout_ms=30000),
        )
        monkeypatch.setattr("openai.OpenAI", lambda api_key, base_url: mock_client)

        conn = OpenRouterConnector()
        ctx = BusinessContext(
            business_type="cafe",
            maturity_stage="growing",
            website_score="needs_work",
            years_in_business=2,
            city="Mumbai",
            name="Delta Cafe",
            has_website=False,
            website_issues=["missing_meta"],
        )
        with pytest.raises(ConnectorError, match="OpenRouter API request failed"):
            conn.generate_pitch(ctx)
