from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    mysql_host: str = Field(default="127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="smart_parking", alias="MYSQL_DATABASE")
    mysql_url: str | None = Field(default=None, alias="MYSQL_URL")

    llm_provider: str = Field(default="auto", alias="RAG_LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="RAG_LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="RAG_LLM_TEMPERATURE")
    llm_timeout_seconds: float = Field(default=3.0, alias="RAG_LLM_TIMEOUT_SECONDS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    ollama_base_url: str | None = Field(default=None, alias="OLLAMA_BASE_URL")


def get_settings() -> RagSettings:
    return RagSettings()
