from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "service-ocr"
    app_env: str = Field(default="production", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    db_schema: str = Field(default="ocr_schema", alias="DB_SCHEMA")
    cors_allow_origins: str = Field(
        default="http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    api_prefix: str = "/api/ocr"
    upload_dir: str = Field(default="uploads", alias="OCR_UPLOAD_DIR")
    results_dir: str = Field(default="results", alias="OCR_RESULTS_DIR")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

