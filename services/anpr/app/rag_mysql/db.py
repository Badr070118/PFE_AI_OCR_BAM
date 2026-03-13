from __future__ import annotations

from sqlalchemy import create_engine

from app.rag_mysql.config import get_settings


def build_mysql_url() -> str:
    settings = get_settings()
    if settings.mysql_url:
        return settings.mysql_url
    return (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )


def get_engine():
    url = build_mysql_url()
    return create_engine(url, pool_pre_ping=True)
