from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Prefer repo-root .env (../ from backend/), then backend/.env when cwd is backend.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_ENV_FILES = tuple(
    p for p in (_REPO_ROOT / ".env", _BACKEND_DIR / ".env") if p.is_file()
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES if _ENV_FILES else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Pre-Sales AI Agent API"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    llm_backend: Literal["groq", "ollama", "azure_openai", "mock"] = "mock"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_seconds: float = 600.0
    llm_fallback_on_error: bool = False
    llm_only_mode: bool = True
    enable_agentic_critic_loop: bool = True
    agentic_critic_max_iterations: int = 1

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_retries: int = 6
    groq_retry_base_seconds: float = 30.0
    groq_inter_request_delay_seconds: float = 55.0
    groq_max_output_tokens: int = 4096
    # Total input+output token budget per Groq call (0 = auto from model name).
    groq_max_request_tokens: int = 0

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"

    vector_store_backend: Literal["memory", "chroma"] = "memory"
    chroma_persist_dir: str = "data/chroma"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@presales-agent.local"
    smtp_use_tls: bool = True
    email_enabled: bool = False
    reminder_days_before: int = 3
    scheduler_interval_seconds: int = 3600

    data_dir: str = "data/uploads"
    run_db_path: str = "data/runs.sqlite3"
    proposal_company_name: str = "MAQ Software"
    chunk_target_chars: int = 1800
    chunk_overlap_chars: int = 240
    chunk_min_chars: int = 500

    @field_validator("data_dir", "chroma_persist_dir", "run_db_path", mode="before")
    @classmethod
    def resolve_repo_relative_paths(cls, value: str) -> str:
        """Paths in .env are relative to repo root (not uvicorn cwd)."""
        path = Path(value)
        if path.is_absolute():
            return str(path)
        return str((_REPO_ROOT / path).resolve())

    @field_validator("chunk_target_chars", mode="after")
    @classmethod
    def validate_chunk_target_chars(cls, value: int) -> int:
        return min(max(value, 800), 6000)

    @field_validator("chunk_overlap_chars", mode="after")
    @classmethod
    def validate_chunk_overlap_chars(cls, value: int) -> int:
        return min(max(value, 80), 1500)

    @field_validator("chunk_min_chars", mode="after")
    @classmethod
    def validate_chunk_min_chars(cls, value: int) -> int:
        return min(max(value, 250), 2500)


def get_settings() -> Settings:
    """Fresh read each call so `.env` edits apply without restarting the server."""
    return Settings()
