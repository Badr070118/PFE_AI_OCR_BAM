from sqlalchemy import text

from app.legacy.db import engine


def get_db_health() -> dict:
    with engine.connect() as connection:
        current_schema = connection.execute(text("SELECT current_schema()")).scalar()
        connection.execute(text("SELECT 1"))
    return {"ok": True, "service": "ocr", "db": "up", "schema": current_schema}

