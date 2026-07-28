from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq/psql connection options that the asyncpg driver does not accept as
# keyword arguments. Neon's copyable connection strings include these, so they
# are stripped or translated before the URL reaches SQLAlchemy's asyncpg dialect.
_ASYNCPG_UNSUPPORTED_QUERY_KEYS = {"channel_binding"}
_ASYNCPG_QUERY_KEY_ALIASES = {"sslmode": "ssl"}


class Settings(BaseSettings):
    app_name: str = "Voice Inventory Agent API"
    app_env: Literal["local", "test", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/housekeeper"
    # Separate database for integration tests. Never point this at the runtime
    # database_url; integration tests drop and recreate tables. When unset,
    # integration tests are skipped.
    test_database_url: str | None = None
    database_echo: bool = False
    llm_provider: Literal["openai"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-sol"

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return cls._sanitize_asyncpg_query(value)

    @staticmethod
    def _sanitize_asyncpg_query(value: str) -> str:
        parts = urlsplit(value)
        if not parts.query:
            return value
        sanitized: list[tuple[str, str]] = []
        for key, item in parse_qsl(parts.query, keep_blank_values=True):
            if key in _ASYNCPG_UNSUPPORTED_QUERY_KEYS:
                continue
            sanitized.append((_ASYNCPG_QUERY_KEY_ALIASES.get(key, key), item))
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(sanitized), parts.fragment)
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
