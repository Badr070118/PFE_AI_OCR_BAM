import re

from sqlalchemy import create_engine, event, text

from app.core.config import get_settings

settings = get_settings()
_schema_candidate = settings.db_schema.strip()
DB_SCHEMA = (
    _schema_candidate
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", _schema_candidate)
    else "mlpdr_schema"
)

engine = create_engine(settings.database_url, pool_pre_ping=True)


def _set_search_path(dbapi_connection) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET search_path TO {DB_SCHEMA}, public")
    finally:
        cursor.close()


@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, _connection_record) -> None:
    _set_search_path(dbapi_connection)


@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_connection, _connection_record, _connection_proxy) -> None:
    _set_search_path(dbapi_connection)


def get_db_health() -> dict:
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        current_schema = connection.execute(text("SELECT current_schema()")).scalar()
        connection.execute(text("SELECT 1"))
    return {"ok": True, "service": "mlpdr", "db": "up", "schema": current_schema}
