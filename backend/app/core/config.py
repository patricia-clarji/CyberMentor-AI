from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="CYBERMENTOR_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "CyberMentor Trusted API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://cybermentor:cybermentor@localhost:5432/cybermentor"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: str = "http://localhost:5173"
    session_cookie_name: str = "cm_session"
    csrf_cookie_name: str = "cm_csrf"
    session_ttl_seconds: int = Field(default=604800, ge=900, le=2592000)
    verification_ttl_seconds: int = Field(default=86400, ge=900, le=604800)
    reset_ttl_seconds: int = Field(default=3600, ge=600, le=86400)
    secure_cookies: bool = False
    dev_seed_enabled: bool = False
    email_backend: Literal["mailpit", "console", "provider"] = "mailpit"
    mailpit_host: str = "localhost"
    mailpit_port: int = 1025
    production_email_provider: str | None = None
    llm_provider: (
        Literal[
            "openai",
            "anthropic",
            "google",
            "ollama",
            "mock",
            "deterministic",
        ]
        | None
    ) = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = Field(default=12.0, ge=1, le=60)
    llm_temperature: float = Field(default=0.1, ge=0, le=1)
    llm_input_cost_per_million: float = Field(default=0.0, ge=0)
    llm_output_cost_per_million: float = Field(default=0.0, ge=0)
    embedding_provider: str = "test"
    object_storage_backend: Literal["minio", "provider"] = "minio"
    content_root: Path = Path("../content/published")
    cms_media_root: Path = Path("cms-media")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def empty_provider_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def production_guards(self) -> "Settings":
        if self.environment == "production":
            problems: list[str] = []
            if self.dev_seed_enabled:
                problems.append("development seed accounts")
            if self.database_url.startswith("sqlite"):
                problems.append("SQLite database")
            if self.email_backend in {"mailpit", "console"}:
                problems.append("development-only email")
            if not self.secure_cookies:
                problems.append("insecure cookies")
            if self.embedding_provider == "test":
                problems.append("test embeddings")
            if self.object_storage_backend == "minio":
                problems.append("local MinIO configuration")
            if problems:
                raise ValueError("Production configuration rejected: " + ", ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
