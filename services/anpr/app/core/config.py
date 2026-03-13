from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "service-mlpdr"
    app_env: str = Field(default="production", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./anpr.db", alias="DATABASE_URL")
    db_schema: str = Field(default="mlpdr_schema", alias="DB_SCHEMA")
    cors_allow_origins: str = Field(
        default="http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    api_prefix: str = "/api/mlpdr"
    anpr_output_dir: str = Field(default="/srv/service/outputs", alias="MLPDR_OUTPUT_DIR")
    anpr_stream_dir: str = Field(default="/srv/service/stream", alias="ANPR_STREAM_DIR")
    anpr_llm_provider: str = Field(default="auto", alias="ANPR_LLM_PROVIDER")
    anpr_llm_model: str = Field(default="llama3.1:8b", alias="ANPR_LLM_MODEL")
    anpr_llm_temperature: float = Field(default=0.1, alias="ANPR_LLM_TEMPERATURE")
    anpr_llm_timeout_seconds: float = Field(default=3.0, alias="ANPR_LLM_TIMEOUT_SECONDS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    ollama_base_url: str | None = Field(default=None, alias="OLLAMA_BASE_URL")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
