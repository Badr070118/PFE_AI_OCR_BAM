from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    desc,
    func,
    insert,
    select,
    text,
    update,
)

from app.db import IS_SQLITE, engine
from app.db.session import DB_SCHEMA

METADATA = MetaData(schema=None if IS_SQLITE else DB_SCHEMA)

vehicles = Table(
    "vehicles",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("plate_number", String(32), nullable=False, unique=True, index=True),
    Column("owner_name", String(128), nullable=False),
    Column("vehicle_type", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

unknown_detections = Table(
    "unknown_detections",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("plate_number", String(32), nullable=False),
    Column("image_path", String(512), nullable=True),
    Column("detected_at", DateTime, nullable=False, server_default=func.now()),
)

parking_logs = Table(
    "parking_logs",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("plate_number", String(32), nullable=False, index=True),
    Column("entry_time", DateTime, nullable=False),
    Column("exit_time", DateTime, nullable=True),
    Column("status", String(32), nullable=False),
    Column("image_path", String(512), nullable=True),
)


def init_db() -> None:
    with engine.begin() as connection:
        if not IS_SQLITE:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
    METADATA.create_all(engine)
    seed_default_vehicles()


def seed_default_vehicles() -> None:
    defaults = [
        {
            "plate_number": "34567-أ-6",
            "owner_name": "Ahmed Benali",
            "vehicle_type": "employee",
            "status": "AUTHORIZED",
        },
        {
            "plate_number": "98765-A-1",
            "owner_name": "Unknown",
            "vehicle_type": "visitor",
            "status": "AUTHORIZED",
        },
        {
            "plate_number": "11111-A-3",
            "owner_name": "Suspicious Car",
            "vehicle_type": "unknown",
            "status": "BLACKLISTED",
        },
    ]
    with engine.begin() as connection:
        existing = connection.execute(select(func.count()).select_from(vehicles)).scalar() or 0
        if existing:
            return
        connection.execute(insert(vehicles), defaults)


def get_vehicle(plate_number: str) -> dict | None:
    with engine.begin() as connection:
        row = (
            connection.execute(select(vehicles).where(vehicles.c.plate_number == plate_number))
            .mappings()
            .first()
        )
    return dict(row) if row else None


def insert_unknown_detection(plate_number: str, image_path: str | None, detected_at: datetime) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            insert(unknown_detections).values(
                plate_number=plate_number,
                image_path=image_path,
                detected_at=detected_at,
            )
        )
        inserted = result.inserted_primary_key
    return int(inserted[0]) if inserted else 0


def log_detection(
    plate_number: str,
    status: str,
    image_path: str | None,
    detected_at: datetime,
) -> dict:
    with engine.begin() as connection:
        open_log = (
            connection.execute(
                select(parking_logs)
                .where(and_(parking_logs.c.plate_number == plate_number, parking_logs.c.exit_time.is_(None)))
                .order_by(desc(parking_logs.c.entry_time))
                .limit(1)
            )
            .mappings()
            .first()
        )

        if open_log:
            connection.execute(
                update(parking_logs)
                .where(parking_logs.c.id == open_log["id"])
                .values(exit_time=detected_at)
            )
            return {"log_id": int(open_log["id"]), "event": "exit"}

        result = connection.execute(
            insert(parking_logs).values(
                plate_number=plate_number,
                entry_time=detected_at,
                exit_time=None,
                status=status,
                image_path=image_path,
            )
        )
        inserted = result.inserted_primary_key
        return {"log_id": int(inserted[0]) if inserted else 0, "event": "entry"}


def log_no_plate(image_path: str | None, detected_at: datetime) -> dict:
    synthetic_plate = f"NO_PLATE_{detected_at.strftime('%Y%m%d%H%M%S%f')}"
    with engine.begin() as connection:
        result = connection.execute(
            insert(parking_logs).values(
                plate_number=synthetic_plate,
                entry_time=detected_at,
                exit_time=None,
                status="NO_PLATE",
                image_path=image_path,
            )
        )
        inserted = result.inserted_primary_key
    return {"log_id": int(inserted[0]) if inserted else 0, "event": "entry"}


def close_parking_session(plate_number: str, exit_time: datetime) -> dict:
    with engine.begin() as connection:
        open_log = (
            connection.execute(
                select(parking_logs)
                .where(and_(parking_logs.c.plate_number == plate_number, parking_logs.c.exit_time.is_(None)))
                .order_by(desc(parking_logs.c.entry_time))
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not open_log:
            return {"closed": False, "log_id": None}
        connection.execute(
            update(parking_logs)
            .where(parking_logs.c.id == open_log["id"])
            .values(exit_time=exit_time)
        )
    return {"closed": True, "log_id": int(open_log["id"])}


def fetch_logs(limit: int = 50, plate_number: str | None = None, status: str | None = None) -> list[dict]:
    query = select(parking_logs).order_by(desc(parking_logs.c.entry_time)).limit(limit)
    if plate_number:
        query = query.where(parking_logs.c.plate_number == plate_number)
    if status:
        query = query.where(parking_logs.c.status == status)
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_unknown_detections(limit: int = 50) -> list[dict]:
    query = select(unknown_detections).order_by(desc(unknown_detections.c.detected_at)).limit(limit)
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_alerts(limit: int = 50) -> dict:
    blacklisted = fetch_logs(limit=limit, status="BLACKLISTED")
    unknown = fetch_unknown_detections(limit=limit)
    return {"blacklisted": blacklisted, "unknown": unknown}


def stats_snapshot() -> dict:
    with engine.begin() as connection:
        total_vehicles = connection.execute(select(func.count()).select_from(vehicles)).scalar() or 0
        authorized = (
            connection.execute(select(func.count()).select_from(vehicles).where(vehicles.c.status == "AUTHORIZED"))
            .scalar()
            or 0
        )
        blacklisted = (
            connection.execute(select(func.count()).select_from(vehicles).where(vehicles.c.status == "BLACKLISTED"))
            .scalar()
            or 0
        )
        unknown_today = connection.execute(
            text(
                "SELECT COUNT(*) FROM unknown_detections "
                + ("WHERE DATE(detected_at) = DATE('now')" if IS_SQLITE else "WHERE DATE(detected_at) = CURRENT_DATE")
            )
        ).scalar() or 0
        entries_today = connection.execute(
            text(
                "SELECT COUNT(*) FROM parking_logs "
                + ("WHERE DATE(entry_time) = DATE('now')" if IS_SQLITE else "WHERE DATE(entry_time) = CURRENT_DATE")
            )
        ).scalar() or 0
        avg_minutes = connection.execute(
            text(
                "SELECT AVG("
                + (
                    "(julianday(exit_time) - julianday(entry_time)) * 24 * 60"
                    if IS_SQLITE
                    else "EXTRACT(EPOCH FROM (exit_time - entry_time)) / 60"
                )
                + ") FROM parking_logs "
                + ("WHERE exit_time IS NOT NULL AND DATE(entry_time) = DATE('now')" if IS_SQLITE else "WHERE exit_time IS NOT NULL AND DATE(entry_time) = CURRENT_DATE")
            )
        ).scalar()
        currently_inside = connection.execute(
            text("SELECT COUNT(*) FROM parking_logs WHERE exit_time IS NULL AND status = 'AUTHORIZED'")
        ).scalar() or 0
    return {
        "total_vehicles": int(total_vehicles),
        "authorized": int(authorized),
        "blacklisted": int(blacklisted),
        "unknown_today": int(unknown_today),
        "entries_today": int(entries_today),
        "average_parking_minutes_today": float(avg_minutes) if avg_minutes is not None else 0.0,
        "currently_inside": int(currently_inside),
    }


def run_query(sql: str) -> list[dict[str, Any]]:
    with engine.begin() as connection:
        rows = connection.execute(text(sql)).mappings().all()
    return [dict(row) for row in rows]
