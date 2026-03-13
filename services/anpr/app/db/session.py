import re

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings

settings = get_settings()
_schema_candidate = settings.db_schema.strip()
DB_SCHEMA = (
    _schema_candidate
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", _schema_candidate)
    else "mlpdr_schema"
)

_db_url = make_url(settings.database_url)
IS_SQLITE = _db_url.get_backend_name() == "sqlite"
_connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)


def _set_search_path(dbapi_connection) -> None:
    if IS_SQLITE:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET search_path TO {DB_SCHEMA}, public")
    finally:
        cursor.close()


if not IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _connection_record) -> None:
        _set_search_path(dbapi_connection)

    @event.listens_for(engine, "checkout")
    def _on_checkout(dbapi_connection, _connection_record, _connection_proxy) -> None:
        _set_search_path(dbapi_connection)


def get_db_health() -> dict:
    with engine.begin() as connection:
        if not IS_SQLITE:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
            current_schema = connection.execute(text("SELECT current_schema()")).scalar()
        else:
            current_schema = "main"
        connection.execute(text("SELECT 1"))
    return {"ok": True, "service": "mlpdr", "db": "up", "schema": current_schema}
