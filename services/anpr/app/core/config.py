from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "service-mlpdr"
    app_env: str = Field(default="production", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    db_schema: str = Field(default="mlpdr_schema", alias="DB_SCHEMA")
    cors_allow_origins: str = Field(
        default="http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    api_prefix: str = "/api/mlpdr"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
