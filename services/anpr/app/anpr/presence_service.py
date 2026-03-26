from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from app.anpr.database import (
    fetch_employees,
    fetch_parking_logs_range,
    fetch_unknown_detections_range,
    fetch_vehicles,
)
from app.anpr.reporting_service import _build_presence_config
from app.anpr.plate_utils import normalize_plate, plate_loose_key


@dataclass(frozen=True)
class PresenceOverview:
    date: date
    summary: dict[str, Any]
    recent_accesses: list[dict[str, Any]]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _date_bounds(target_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date + timedelta(days=1), time.min)
    return start_dt, end_dt


def _employees_map() -> dict[str, dict[str, Any]]:
    employees = fetch_employees()
    return {row["plate_number"]: row for row in employees if row.get("plate_number")}


def _vehicles_map() -> dict[str, dict[str, Any]]:
    vehicles = fetch_vehicles()
    return {row["plate_number"]: row for row in vehicles if row.get("plate_number")}


def _build_directory() -> dict[str, dict[str, Any]]:
    directory: dict[str, dict[str, Any]] = {}
    employees_by_plate = _employees_map()
    for plate, employee in employees_by_plate.items():
        if not plate or not employee.get("is_active", True):
            continue
        directory[plate] = {
            "plate_number": plate,
            "full_name": employee.get("full_name"),
            "department": employee.get("department"),
        }

    vehicles_by_plate = _vehicles_map()
    for plate, vehicle in vehicles_by_plate.items():
        if not plate:
            continue
        if (vehicle.get("status") or "").upper() != "AUTHORIZED":
            continue
        if plate not in directory:
            directory[plate] = {
                "plate_number": plate,
                "full_name": vehicle.get("owner_name"),
                "department": vehicle.get("vehicle_type"),
            }
        else:
            entry = directory[plate]
            entry.setdefault("full_name", vehicle.get("owner_name"))
            entry.setdefault("department", vehicle.get("vehicle_type"))
    return directory


def _directory_lookup(directory: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for plate, entry in directory.items():
        if not plate:
            continue
        normalized = normalize_plate(plate)
        loose = plate_loose_key(plate)
        for key in {plate, normalized, loose}:
            if key and key not in lookup:
                lookup[key] = entry
    return lookup


def _attach_employee_meta(
    rows: list[dict[str, Any]],
    directory_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    for row in rows:
        plate = row.get("plate_number")
        if not plate:
            continue
        entry = (
            directory_lookup.get(plate)
            or directory_lookup.get(normalize_plate(plate))
            or directory_lookup.get(plate_loose_key(plate))
        )
        if entry:
            row.setdefault("employee_name", entry.get("full_name"))
            row.setdefault("department", entry.get("department"))
    return rows


def getPresenceOverviewDashboard(target_date: date | None = None) -> dict[str, Any]:
    target_date = target_date or datetime.now().date()
    directory = _build_directory()
    directory_lookup = _directory_lookup(directory)
    config = _build_presence_config()
    late_threshold = datetime.combine(target_date, config.standard_start) + timedelta(minutes=config.late_minutes)

    start_dt, end_dt = _date_bounds(target_date)
    logs = fetch_parking_logs_range(start_dt, end_dt)
    logs.sort(key=lambda item: item.get("entry_time") or datetime.min, reverse=True)
    recent = logs[:10]

    present_plates: set[str] = set()
    first_entry_by_plate: dict[str, datetime] = {}
    for log in logs:
        plate = log.get("plate_number")
        if not plate:
            continue
        entry = (
            directory_lookup.get(plate)
            or directory_lookup.get(normalize_plate(plate))
            or directory_lookup.get(plate_loose_key(plate))
        )
        if not entry:
            continue
        canonical_plate = entry.get("plate_number")
        if not canonical_plate:
            continue
        present_plates.add(canonical_plate)
        entry_time = log.get("entry_time")
        if entry_time and (
            canonical_plate not in first_entry_by_plate or entry_time < first_entry_by_plate[canonical_plate]
        ):
            first_entry_by_plate[canonical_plate] = entry_time

    late_count = sum(1 for ts in first_entry_by_plate.values() if ts > late_threshold)

    unknown_detections = fetch_unknown_detections_range(start_dt, end_dt)
    unknown_plates: list[dict[str, Any]] = []
    for item in unknown_detections:
        plate = item.get("plate_number")
        if not plate:
            continue
        if (
            directory_lookup.get(plate)
            or directory_lookup.get(normalize_plate(plate))
            or directory_lookup.get(plate_loose_key(plate))
        ):
            continue
        unknown_plates.append({"plate_number": plate, "detected_at": item.get("detected_at")})

    total_employees = len(directory)
    employees_present = len(present_plates)
    employees_absent = max(total_employees - employees_present, 0)

    summary = {
        "total_employees": total_employees,
        "employees_present": employees_present,
        "employees_absent": employees_absent,
        "total_late": late_count,
        "unknown_plates": len(unknown_plates),
    }

    recent = _attach_employee_meta(recent, directory_lookup)

    return {
        "date": target_date,
        "summary": summary,
        "recent_accesses": recent,
    }


__all__ = ["getPresenceOverviewDashboard", "_parse_date"]
