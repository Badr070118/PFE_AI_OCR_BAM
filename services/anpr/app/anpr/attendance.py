from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from app.anpr.database import (
    fetch_employees,
    fetch_parking_logs_range,
    fetch_unknown_detections_range,
    fetch_vehicles,
)
from app.core.config import get_settings


@dataclass(frozen=True)
class AttendanceConfig:
    standard_start: time
    late_minutes: int
    dedup_minutes: int


def _parse_time(value: str, default: time) -> time:
    if not value:
        return default
    try:
        parts = value.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return time(hour=hour, minute=minute)
    except (ValueError, IndexError):
        return default


def build_attendance_config() -> AttendanceConfig:
    settings = get_settings()
    return AttendanceConfig(
        standard_start=_parse_time(settings.attendance_start_time, time(hour=9, minute=0)),
        late_minutes=max(int(settings.attendance_late_minutes), 0),
        dedup_minutes=max(int(settings.attendance_dedup_minutes), 0),
    )


def _date_range(start_date: date, end_date: date) -> Iterable[date]:
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += timedelta(days=1)


def _merge_employee_directory(vehicles: list[dict], employees: list[dict]) -> list[dict]:
    by_plate = {item.get("plate_number"): dict(item) for item in employees if item.get("plate_number")}
    merged: list[dict] = []

    for vehicle in vehicles:
        plate = vehicle.get("plate_number")
        if not plate:
            continue
        base = {
            "full_name": vehicle.get("owner_name") or "Unknown",
            "plate_number": plate,
            "department": vehicle.get("vehicle_type") or "-",
            "employee_code": None,
            "is_active": vehicle.get("status") == "AUTHORIZED",
        }
        entry = by_plate.pop(plate, None)
        if entry:
            base.update(
                {
                    "full_name": entry.get("full_name") or base["full_name"],
                    "department": entry.get("department") or base["department"],
                    "employee_code": entry.get("employee_code"),
                    "is_active": bool(entry.get("is_active")) if entry.get("is_active") is not None else base["is_active"],
                }
            )
        merged.append(base)

    for leftover in by_plate.values():
        merged.append(
            {
                "full_name": leftover.get("full_name") or "Unknown",
                "plate_number": leftover.get("plate_number"),
                "department": leftover.get("department") or "-",
                "employee_code": leftover.get("employee_code"),
                "is_active": bool(leftover.get("is_active", True)),
            }
        )

    merged.sort(key=lambda item: (item.get("full_name") or "").lower())
    return merged


def aggregate_attendance(start_date: date, end_date: date) -> dict:
    config = build_attendance_config()
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
    total_days = (end_date - start_date).days + 1

    vehicles = fetch_vehicles()
    employees = fetch_employees()
    directory = _merge_employee_directory(vehicles, employees)
    employees_by_plate = {item["plate_number"]: item for item in directory if item.get("plate_number")}

    logs = fetch_parking_logs_range(start_dt, end_dt)
    unknown_detections = fetch_unknown_detections_range(start_dt, end_dt)

    sessions_by_plate: dict[str, list[dict]] = {}
    anomalies: dict[str, list[dict]] = {
        "entry_without_exit": [],
        "incoherent": [],
        "duplicates": [],
        "unknown_plates": [],
        "blacklisted": [],
        "no_plate": [],
    }
    day_anomalies: dict[str, dict[date, list[str]]] = {}

    def add_day_anomaly(plate: str, when: datetime | None, label: str) -> None:
        if not plate or when is None:
            return
        day = when.date()
        day_anomalies.setdefault(plate, {}).setdefault(day, []).append(label)

    last_entry_by_plate: dict[str, datetime] = {}
    dedup_window = timedelta(minutes=config.dedup_minutes)

    for log in logs:
        plate = log.get("plate_number")
        entry_time = log.get("entry_time")
        exit_time = log.get("exit_time")
        status = (log.get("status") or "").upper()

        if not plate or not entry_time:
            continue

        if plate.startswith("NO_PLATE"):
            anomalies["no_plate"].append({"plate_number": plate, "entry_time": entry_time})
            continue

        if status == "BLACKLISTED":
            anomalies["blacklisted"].append({"plate_number": plate, "entry_time": entry_time})
            add_day_anomaly(plate, entry_time, "blacklisted")

        if status == "UNKNOWN" and plate not in employees_by_plate:
            anomalies["unknown_plates"].append({"plate_number": plate, "entry_time": entry_time})
            add_day_anomaly(plate, entry_time, "unknown")

        last_entry = last_entry_by_plate.get(plate)
        if last_entry and entry_time - last_entry <= dedup_window:
            anomalies["duplicates"].append(
                {
                    "plate_number": plate,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "note": f"Within {config.dedup_minutes} minutes",
                }
            )
            add_day_anomaly(plate, entry_time, "duplicate")
            continue
        last_entry_by_plate[plate] = entry_time

        if exit_time is None:
            anomalies["entry_without_exit"].append({"plate_number": plate, "entry_time": entry_time})
            add_day_anomaly(plate, entry_time, "entry_without_exit")
        elif exit_time < entry_time:
            anomalies["incoherent"].append({"plate_number": plate, "entry_time": entry_time, "exit_time": exit_time})
            add_day_anomaly(plate, entry_time, "incoherent")
            continue

        sessions_by_plate.setdefault(plate, []).append(log)

    daily_records: dict[str, dict[date, dict]] = {}
    for plate, sessions in sessions_by_plate.items():
        daily_records[plate] = {}
        for session in sessions:
            entry_time = session.get("entry_time")
            if entry_time is None:
                continue
            day = entry_time.date()
            day_bucket = daily_records[plate].setdefault(
                day,
                {
                    "date": day,
                    "first_entry": None,
                    "last_exit": None,
                    "total_minutes": 0.0,
                    "late": False,
                    "status": "absent",
                    "anomalies": [],
                    "incomplete": False,
                },
            )

            if day_bucket["first_entry"] is None or entry_time < day_bucket["first_entry"]:
                day_bucket["first_entry"] = entry_time

            exit_time = session.get("exit_time")
            if exit_time is None:
                day_bucket["incomplete"] = True
            else:
                if day_bucket["last_exit"] is None or exit_time > day_bucket["last_exit"]:
                    day_bucket["last_exit"] = exit_time
                duration_minutes = (exit_time - entry_time).total_seconds() / 60.0
                if duration_minutes > 0:
                    day_bucket["total_minutes"] += duration_minutes

    for plate, records in daily_records.items():
        for day, bucket in records.items():
            if bucket["first_entry"] is None:
                continue
            expected = datetime.combine(day, config.standard_start) + timedelta(minutes=config.late_minutes)
            bucket["late"] = bucket["first_entry"] > expected

    employee_summaries: list[dict] = []
    total_presence_minutes = 0.0
    total_days_present = 0
    total_late = 0
    total_anomalies = 0
    first_arrival: tuple[datetime, dict] | None = None
    last_exit: tuple[datetime, dict] | None = None

    for employee in directory:
        plate = employee.get("plate_number")
        employee_days: list[dict] = []
        days_present = 0
        late_count = 0
        anomalies_count = 0
        employee_minutes = 0.0

        plate_records = daily_records.get(plate, {}) if plate else {}

        for day in _date_range(start_date, end_date):
            record = plate_records.get(day)
            if not record:
                employee_days.append(
                    {
                        "date": day,
                        "first_entry": None,
                        "last_exit": None,
                        "total_minutes": 0.0,
                        "late": False,
                        "status": "absent",
                        "anomalies": [],
                    }
                )
                continue

            anomalies_list = list(day_anomalies.get(plate, {}).get(day, []))
            if record["incomplete"] and "incomplete" not in anomalies_list:
                anomalies_list.append("incomplete")
            if record["late"]:
                late_count += 1

            status = "present"
            if anomalies_list:
                status = "anomalie"
            if record["incomplete"]:
                status = "incomplete"
            if record["late"] and status == "present":
                status = "late"

            employee_minutes += record["total_minutes"]
            if record["first_entry"]:
                days_present += 1

            employee_days.append(
                {
                    "date": day,
                    "first_entry": record["first_entry"],
                    "last_exit": record["last_exit"],
                    "total_minutes": record["total_minutes"],
                    "late": record["late"],
                    "status": status,
                    "anomalies": anomalies_list,
                }
            )

        anomalies_count = sum(1 for day in employee_days if day["status"] in {"incomplete", "anomalie"})
        total_anomalies += anomalies_count

        total_presence_minutes += employee_minutes
        total_days_present += days_present
        total_late += late_count

        first_entry_times = [day["first_entry"] for day in employee_days if day["first_entry"]]
        last_exit_times = [day["last_exit"] for day in employee_days if day["last_exit"]]

        if first_entry_times:
            earliest = min(first_entry_times)
            if first_arrival is None or earliest < first_arrival[0]:
                first_arrival = (earliest, employee)
        if last_exit_times:
            latest = max(last_exit_times)
            if last_exit is None or latest > last_exit[0]:
                last_exit = (latest, employee)

        days_absent = total_days - days_present
        avg_minutes = employee_minutes / days_present if days_present else 0.0

        if not employee.get("is_active", True):
            status_global = "inactive"
        elif anomalies_count > 0:
            status_global = "anomalie"
        elif late_count > 0:
            status_global = "retard"
        elif days_present > 0:
            status_global = "present"
        else:
            status_global = "absent"

        employee_summaries.append(
            {
                "full_name": employee.get("full_name") or "Unknown",
                "plate_number": plate,
                "department": employee.get("department") or "-",
                "employee_code": employee.get("employee_code"),
                "is_active": bool(employee.get("is_active", True)),
                "days_present": days_present,
                "days_absent": days_absent,
                "late_count": late_count,
                "total_minutes": round(employee_minutes, 2),
                "avg_minutes": round(avg_minutes, 2),
                "status": status_global,
                "anomalies_count": anomalies_count,
                "daily": employee_days,
            }
        )

    anomalies["unknown_plates"].extend(
        {
            "plate_number": item.get("plate_number"),
            "detected_at": item.get("detected_at"),
        }
        for item in unknown_detections
    )

    extra_anomalies = sum(len(items) for items in anomalies.values())
    summary = {
        "total_employees": len(directory),
        "employees_present": sum(1 for emp in employee_summaries if emp["days_present"] > 0),
        "total_presences": total_days_present,
        "total_late": total_late,
        "total_anomalies": total_anomalies + extra_anomalies,
        "total_presence_minutes": round(total_presence_minutes, 2),
        "avg_presence_minutes": round(total_presence_minutes / total_days_present, 2) if total_days_present else 0.0,
        "first_arrival": {
            "timestamp": first_arrival[0] if first_arrival else None,
            "employee": first_arrival[1] if first_arrival else None,
        },
        "last_exit": {
            "timestamp": last_exit[0] if last_exit else None,
            "employee": last_exit[1] if last_exit else None,
        },
    }

    return {
        "summary": summary,
        "employees": employee_summaries,
        "anomalies": anomalies,
    }


__all__ = ["aggregate_attendance", "AttendanceConfig", "build_attendance_config"]
