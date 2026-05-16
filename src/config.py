"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SMTP
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="")

    # Local GGUF model — unified VLM used for both vision and text tasks
    local_model_path: str = Field(
        default="/home/pranavvv/models/qwen3.5-VLM-9b/Qwen3.5-9B-Q4_K_M.gguf"
    )

    # VLM model directory (contains both .gguf and mmproj)
    vlm_model_dir: str = Field(default="/home/pranavvv/models/qwen3.5-VLM-9b")
    vlm_model_file: str = Field(default="Qwen3.5-9B-Q4_K_M.gguf")
    vlm_mmproj_file: str = Field(default="mmproj-F16.gguf")

    # Ollama fallback
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:9b")

    # Vision agent toggle
    use_vision: bool = Field(default=True)
    vision_timeout_ms: int = Field(default=30000)
    vision_headed: bool = Field(default=True)

    # Proxy
    proxy_server: str = Field(default="")
    proxy_username: str = Field(default="")
    proxy_password: str = Field(default="")

    # Database
    db_path: str = Field(default="./data/leads.db")

    # WhatsApp
    whatsapp_user_data_dir: str = Field(default="./whatsapp_session")

    # Dashboard
    dashboard_port: int = Field(default=8080)

    # Drafts
    whatsapp_drafts_dir: str = Field(default="./data/whatsapp_drafts")

    @property
    def vlm_model_path(self) -> Path:
        """Return resolved path to the VLM weights file."""
        return Path(self.vlm_model_dir) / self.vlm_model_file

    @property
    def vlm_mmproj_path(self) -> Path:
        """Return resolved path to the VLM vision projector file."""
        return Path(self.vlm_model_dir) / self.vlm_mmproj_file

    @property
    def db_uri(self) -> str:
        """Return SQLAlchemy SQLite URI."""
        path = Path(self.db_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    @property
    def whatsapp_session_path(self) -> Path:
        """Return resolved path for WhatsApp persistent session."""
        path = Path(self.whatsapp_user_data_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def whatsapp_drafts_path(self) -> Path:
        """Return resolved path for WhatsApp draft messages."""
        path = Path(self.whatsapp_drafts_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
