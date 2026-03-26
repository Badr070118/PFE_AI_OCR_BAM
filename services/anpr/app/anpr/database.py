from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    JSON,
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

from app.anpr.plate_utils import normalize_plate, plate_loose_key
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
    Column("blacklist_reason", String(512), nullable=True),
    Column("blacklisted_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

employees = Table(
    "employees",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("full_name", String(128), nullable=False),
    Column("plate_number", String(32), nullable=False, unique=True, index=True),
    Column("department", String(128), nullable=True),
    Column("employee_code", String(64), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default=text("1" if IS_SQLITE else "true")),
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
    Column(
        "manual_opened",
        Boolean,
        nullable=False,
        server_default=text("0" if IS_SQLITE else "false"),
    ),
)

attendance_reports = Table(
    "attendance_reports",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("report_type", String(32), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("generated_at", DateTime, nullable=False, server_default=func.now()),
    Column("file_path", String(512), nullable=False),
    Column("file_name", String(256), nullable=False),
    Column("summary", JSON, nullable=True),
    Column("metadata", JSON, nullable=True),
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


def find_vehicle_by_plate(plate_number: str) -> dict | None:
    if not plate_number:
        return None
    normalized = normalize_plate(plate_number)
    target_key = plate_loose_key(plate_number)
    direct = get_vehicle(plate_number)
    if direct:
        return direct
    if normalized and normalized != plate_number:
        direct = get_vehicle(normalized)
        if direct:
            return direct
    with engine.begin() as connection:
        rows = connection.execute(select(vehicles)).mappings().all()
    for row in rows:
        candidate_plate = row.get("plate_number") or ""
        if normalize_plate(candidate_plate) == normalized:
            return dict(row)
        if target_key and plate_loose_key(candidate_plate) == target_key:
            return dict(row)
    return None


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
    manual_opened = status not in {"UNKNOWN", "BLACKLISTED", "NO_PLATE"}
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
                manual_opened=manual_opened,
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
                manual_opened=False,
            )
        )
        inserted = result.inserted_primary_key
    return {"log_id": int(inserted[0]) if inserted else 0, "event": "entry"}


def mark_manual_open(plate_number: str, opened_at: datetime) -> dict:
    normalized = normalize_plate(plate_number)
    target_key = plate_loose_key(plate_number)
    with engine.begin() as connection:
        rows = (
            connection.execute(
                select(parking_logs)
                .where(
                    and_(
                        parking_logs.c.exit_time.is_(None),
                        parking_logs.c.status.in_(["UNKNOWN", "BLACKLISTED"]),
                    )
                )
                .order_by(desc(parking_logs.c.entry_time))
            )
            .mappings()
            .all()
        )
        open_log = None
        for row in rows:
            candidate = row.get("plate_number") or ""
            if candidate == plate_number:
                open_log = row
                break
            if normalized and normalize_plate(candidate) == normalized:
                open_log = row
                break
            if target_key and plate_loose_key(candidate) == target_key:
                open_log = row
                break
        if not open_log:
            return {"updated": False, "log_id": None}
        connection.execute(
            update(parking_logs)
            .where(parking_logs.c.id == open_log["id"])
            .values(entry_time=opened_at, manual_opened=True)
        )
    return {"updated": True, "log_id": int(open_log["id"])}


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


def delete_unknown_detections_by_plate(plate_number: str) -> int:
    if not plate_number:
        return 0
    normalized = normalize_plate(plate_number)
    targets = {plate_number}
    if normalized:
        targets.add(normalized)
    with engine.begin() as connection:
        result = connection.execute(unknown_detections.delete().where(unknown_detections.c.plate_number.in_(targets)))
    return int(result.rowcount or 0)


def fetch_blacklisted_vehicles(limit: int = 50) -> list[dict]:
    order_col = func.coalesce(vehicles.c.blacklisted_at, vehicles.c.created_at)
    query = (
        select(vehicles)
        .where(vehicles.c.status == "BLACKLISTED")
        .order_by(desc(order_col))
        .limit(limit)
    )
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_alerts(limit: int = 50) -> dict:
    blacklisted = fetch_blacklisted_vehicles(limit=limit)
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


def fetch_vehicles(active_only: bool = False) -> list[dict]:
    query = select(vehicles)
    if active_only:
        query = query.where(vehicles.c.status == "AUTHORIZED")
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_employees(active_only: bool = False) -> list[dict]:
    query = select(employees)
    if active_only:
        query = query.where(employees.c.is_active.is_(True))
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_parking_logs_range(start_time: datetime, end_time: datetime) -> list[dict]:
    query = (
        select(parking_logs)
        .where(and_(parking_logs.c.entry_time >= start_time, parking_logs.c.entry_time < end_time))
        .order_by(parking_logs.c.entry_time)
    )
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def fetch_unknown_detections_range(start_time: datetime, end_time: datetime) -> list[dict]:
    query = (
        select(unknown_detections)
        .where(and_(unknown_detections.c.detected_at >= start_time, unknown_detections.c.detected_at < end_time))
        .order_by(unknown_detections.c.detected_at)
    )
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def insert_attendance_report(
    report_type: str,
    start_date: datetime,
    end_date: datetime,
    file_path: str,
    file_name: str,
    summary: dict | None = None,
    metadata: dict | None = None,
) -> int:
    with engine.begin() as connection:
        result = connection.execute(
            insert(attendance_reports).values(
                report_type=report_type,
                start_date=start_date.date(),
                end_date=end_date.date(),
                file_path=file_path,
                file_name=file_name,
                summary=summary,
                metadata=metadata,
            )
        )
        inserted = result.inserted_primary_key
    return int(inserted[0]) if inserted else 0


def fetch_attendance_reports(limit: int = 50) -> list[dict]:
    query = select(attendance_reports).order_by(desc(attendance_reports.c.generated_at)).limit(limit)
    with engine.begin() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def get_attendance_report(report_id: int) -> dict | None:
    with engine.begin() as connection:
        row = (
            connection.execute(select(attendance_reports).where(attendance_reports.c.id == report_id))
            .mappings()
            .first()
        )
    return dict(row) if row else None


def upsert_authorized_employee(
    *,
    full_name: str,
    department: str,
    plate_number: str,
    is_authorized: bool = True,
    employee_code: str | None = None,
) -> dict:
    if not plate_number:
        raise ValueError("plate_number is required")
    normalized = normalize_plate(plate_number)
    plate_storage = normalized or plate_number
    status = "AUTHORIZED" if is_authorized else "BLACKLISTED"

    with engine.begin() as connection:
        vehicle_row = (
            connection.execute(select(vehicles).where(vehicles.c.plate_number == plate_number))
            .mappings()
            .first()
        )
        if not vehicle_row and normalized and normalized != plate_number:
            vehicle_row = (
                connection.execute(select(vehicles).where(vehicles.c.plate_number == normalized))
                .mappings()
                .first()
            )
        if vehicle_row:
            connection.execute(
                update(vehicles)
                .where(vehicles.c.id == vehicle_row["id"])
                .values(owner_name=full_name, vehicle_type=department, status=status)
            )
            vehicle_id = int(vehicle_row["id"])
        else:
            result = connection.execute(
                insert(vehicles).values(
                    plate_number=plate_storage,
                    owner_name=full_name,
                    vehicle_type=department,
                    status=status,
                )
            )
            inserted = result.inserted_primary_key
            vehicle_id = int(inserted[0]) if inserted else 0

        employee_row = (
            connection.execute(select(employees).where(employees.c.plate_number == plate_number))
            .mappings()
            .first()
        )
        if not employee_row and normalized and normalized != plate_number:
            employee_row = (
                connection.execute(select(employees).where(employees.c.plate_number == normalized))
                .mappings()
                .first()
            )
        if employee_row:
            connection.execute(
                update(employees)
                .where(employees.c.id == employee_row["id"])
                .values(full_name=full_name, department=department, is_active=is_authorized, employee_code=employee_code)
            )
            employee_id = int(employee_row["id"])
        else:
            result = connection.execute(
                insert(employees).values(
                    full_name=full_name,
                    plate_number=plate_storage,
                    department=department,
                    employee_code=employee_code,
                    is_active=is_authorized,
                )
            )
            inserted = result.inserted_primary_key
            employee_id = int(inserted[0]) if inserted else 0

    return {"vehicle_id": vehicle_id, "employee_id": employee_id, "plate_number": plate_storage}


def upsert_blacklisted_vehicle(
    *,
    plate_number: str,
    reason: str,
    owner_name: str | None = None,
    vehicle_type: str | None = None,
    detected_at: datetime | None = None,
) -> dict:
    if not plate_number:
        raise ValueError("plate_number is required")
    normalized = normalize_plate(plate_number)
    plate_storage = normalized or plate_number
    timestamp = detected_at or datetime.now()

    with engine.begin() as connection:
        vehicle_row = (
            connection.execute(select(vehicles).where(vehicles.c.plate_number == plate_number))
            .mappings()
            .first()
        )
        if not vehicle_row and normalized and normalized != plate_number:
            vehicle_row = (
                connection.execute(select(vehicles).where(vehicles.c.plate_number == normalized))
                .mappings()
                .first()
            )

        payload = {
            "status": "BLACKLISTED",
            "blacklist_reason": reason,
            "blacklisted_at": timestamp,
        }
        if owner_name:
            payload["owner_name"] = owner_name
        if vehicle_type:
            payload["vehicle_type"] = vehicle_type

        if vehicle_row:
            connection.execute(
                update(vehicles)
                .where(vehicles.c.id == vehicle_row["id"])
                .values(**payload)
            )
            vehicle_id = int(vehicle_row["id"])
        else:
            result = connection.execute(
                insert(vehicles).values(
                    plate_number=plate_storage,
                    owner_name=owner_name or "Unknown",
                    vehicle_type=vehicle_type or "unknown",
                    status="BLACKLISTED",
                    blacklist_reason=reason,
                    blacklisted_at=timestamp,
                )
            )
            inserted = result.inserted_primary_key
            vehicle_id = int(inserted[0]) if inserted else 0

    return {
        "vehicle_id": vehicle_id,
        "plate_number": plate_storage,
        "blacklist_reason": reason,
        "blacklisted_at": timestamp,
    }


def run_query(sql: str) -> list[dict[str, Any]]:
    with engine.begin() as connection:
        rows = connection.execute(text(sql)).mappings().all()
    return [dict(row) for row in rows]
