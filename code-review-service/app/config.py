"""Configuration for the graph-based code review service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Repo checkout root: where to clone/checkout repositories
    repo_checkout_root: Path = Path("/tmp/code-review-repos")

    # Supported languages and their file extensions (comma-separated per language)
    # Format: python=.py,.pyi,typescript=.ts,.tsx
    supported_languages: str = "python=.py,.pyi"

    # LLM provider and credentials
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.2

    # Gemini (Google AI)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.2

    # Optional: Anthropic / local model placeholders
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Optional: webhook secret for PR webhooks
    webhook_secret: Optional[str] = None

    # GitHub integration (for posting review comments and status)
    github_token: Optional[str] = None


def get_settings() -> Settings:
    """Return application settings (singleton-style usage)."""
    return Settings()


def get_language_extensions(settings: Optional[Settings] = None) -> dict[str, list[str]]:
    """Parse supported_languages into a map language -> list of extensions."""
    s = settings or get_settings()
    result: dict[str, list[str]] = {}
    for part in s.supported_languages.strip().split(","):
        part = part.strip()
        if "=" in part:
            lang, exts = part.split("=", 1)
            result[lang.strip()] = [e.strip().lstrip(".") for e in exts.split(",")]
    return result


def get_extension_to_language(settings: Optional[Settings] = None) -> dict[str, str]:
    """Map file extension (without dot) to language."""
    ext_to_lang: dict[str, str] = {}
    for lang, exts in get_language_extensions(settings).items():
        for e in exts:
            ext_to_lang[e] = lang
    return ext_to_lang
