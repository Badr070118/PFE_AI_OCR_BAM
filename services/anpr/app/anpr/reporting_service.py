from __future__ import annotations

"""
Presence reporting service (real data only).

Schema inspected in mlpdr_schema:
- employees: id, full_name, plate_number, department, employee_code, is_active, created_at
- parking_logs: id, plate_number, entry_time, exit_time, status, image_path
- unknown_detections: id, plate_number, image_path, detected_at
- attendance_reports: id, report_type, start_date, end_date, generated_at, file_path, file_name, summary, metadata

Relations used:
- employees.plate_number <-> parking_logs.plate_number
- unknown_detections are treated as anomalies only (never employees)

Strategy:
- Employees come ONLY from employees table.
- Logs are grouped by plate_number and time for the requested period.
- Presence metrics are computed from entry_time/exit_time pairs.
- Unknown plates are excluded from employee lists and kept in anomalies.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable
from pathlib import Path

from app.anpr.database import (
    fetch_attendance_reports,
    fetch_employees,
    fetch_parking_logs_range,
    fetch_unknown_detections_range,
    fetch_vehicles,
    get_attendance_report,
    insert_attendance_report,
)
from app.anpr.pdf_report import build_presence_pdf
from app.anpr.plate_utils import normalize_plate, plate_loose_key
from app.core.config import get_settings


@dataclass(frozen=True)
class PresenceConfig:
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


def _build_presence_config() -> PresenceConfig:
    settings = get_settings()
    return PresenceConfig(
        standard_start=_parse_time(settings.attendance_start_time, time(hour=9, minute=0)),
        late_minutes=max(int(settings.attendance_late_minutes), 0),
        dedup_minutes=max(int(settings.attendance_dedup_minutes), 0),
    )


def _date_range(start_date: date, end_date: date) -> Iterable[date]:
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += timedelta(days=1)


def _fetch_employees_real() -> list[dict]:
    employees = fetch_employees()
    directory_by_plate: dict[str, dict] = {}
    for employee in employees:
        plate = employee.get("plate_number")
        if not plate:
            continue
        directory_by_plate[plate] = {
            "full_name": employee.get("full_name"),
            "plate_number": plate,
            "department": employee.get("department"),
            "employee_code": employee.get("employee_code"),
            "is_active": bool(employee.get("is_active", True)),
        }

    vehicles = fetch_vehicles(active_only=True)
    for vehicle in vehicles:
        plate = vehicle.get("plate_number")
        if not plate:
            continue
        entry = directory_by_plate.get(plate)
        if not entry:
            directory_by_plate[plate] = {
                "full_name": vehicle.get("owner_name"),
                "plate_number": plate,
                "department": vehicle.get("vehicle_type"),
                "employee_code": None,
                "is_active": True,
            }
        else:
            if not entry.get("full_name"):
                entry["full_name"] = vehicle.get("owner_name")
            if not entry.get("department"):
                entry["department"] = vehicle.get("vehicle_type")

    directory = list(directory_by_plate.values())
    directory.sort(key=lambda item: (item.get("full_name") or "").lower())
    return directory


def _build_employee_plate_index(employees: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_plate: dict[str, dict] = {}
    by_loose: dict[str, dict] = {}
    for employee in employees:
        plate = employee.get("plate_number")
        if not plate:
            continue
        by_plate.setdefault(plate, employee)
        normalized = normalize_plate(plate)
        if normalized:
            by_plate.setdefault(normalized, employee)
        loose_key = plate_loose_key(plate)
        if loose_key:
            by_loose.setdefault(loose_key, employee)
    return by_plate, by_loose


def _resolve_employee_for_plate(
    plate_number: str | None,
    employees_by_plate: dict[str, dict],
    employees_by_loose: dict[str, dict],
) -> dict | None:
    if not plate_number:
        return None
    employee = employees_by_plate.get(plate_number)
    if employee:
        return employee
    normalized = normalize_plate(plate_number)
    if normalized:
        employee = employees_by_plate.get(normalized)
        if employee:
            return employee
    loose_key = plate_loose_key(plate_number)
    if loose_key:
        return employees_by_loose.get(loose_key)
    return None


def detectRealAnomaliesFromLogs(logs: list[dict], options: dict | None = None) -> dict:
    options = options or {}
    employees_by_plate: dict[str, dict] = options.get("employees_by_plate") or {}
    config: PresenceConfig = options.get("config") or _build_presence_config()

    known_keys: set[str] = set()
    for key in employees_by_plate.keys():
        if not key:
            continue
        known_keys.add(key)
        normalized = normalize_plate(key)
        if normalized:
            known_keys.add(normalized)
        loose_key = plate_loose_key(key)
        if loose_key:
            known_keys.add(loose_key)

    def _is_known_plate(plate: str | None) -> bool:
        if not plate:
            return False
        if plate in known_keys:
            return True
        normalized = normalize_plate(plate)
        if normalized and normalized in known_keys:
            return True
        loose_key = plate_loose_key(plate)
        if loose_key and loose_key in known_keys:
            return True
        return False

    anomalies: dict[str, list[dict]] = {
        "entry_without_exit": [],
        "incoherent": [],
        "duplicates": [],
        "unknown_plates": [],
        "blacklisted": [],
        "orphan_exit": [],
    }
    day_anomalies: dict[str, dict[date, list[str]]] = {}
    duplicate_ids: set[int] = set()

    def add_day_anomaly(plate: str, when: datetime | None, label: str) -> None:
        if not plate or when is None:
            return
        day = when.date()
        day_anomalies.setdefault(plate, {}).setdefault(day, []).append(label)

    last_entry_by_plate: dict[str, datetime] = {}
    dedup_window = timedelta(minutes=config.dedup_minutes)

    for log in sorted(logs, key=lambda item: item.get("entry_time") or datetime.min):
        plate = log.get("plate_number")
        entry_time = log.get("entry_time")
        exit_time = log.get("exit_time")
        status = (log.get("status") or "").upper()

        if entry_time is None and exit_time is not None and plate:
            anomalies["orphan_exit"].append({"plate_number": plate, "exit_time": exit_time})
            add_day_anomaly(plate, exit_time, "orphan_exit")
            continue

        if not plate or entry_time is None:
            continue

        if not _is_known_plate(plate):
            anomalies["unknown_plates"].append(
                {
                    "plate_number": plate,
                    "entry_time": entry_time,
                    "status": status or None,
                }
            )
            add_day_anomaly(plate, entry_time, "unknown")

        if status == "BLACKLISTED":
            anomalies["blacklisted"].append({"plate_number": plate, "entry_time": entry_time})
            add_day_anomaly(plate, entry_time, "blacklisted")

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
            log_id = log.get("id")
            if isinstance(log_id, int):
                duplicate_ids.add(log_id)
            continue
        last_entry_by_plate[plate] = entry_time

        if exit_time is None:
            anomalies["entry_without_exit"].append({"plate_number": plate, "entry_time": entry_time})
            add_day_anomaly(plate, entry_time, "entry_without_exit")
        elif exit_time < entry_time:
            anomalies["incoherent"].append({"plate_number": plate, "entry_time": entry_time, "exit_time": exit_time})
            add_day_anomaly(plate, entry_time, "incoherent")

    return {
        "anomalies": anomalies,
        "day_anomalies": day_anomalies,
        "duplicate_ids": duplicate_ids,
    }


def computeEmployeePresenceMetrics(employee: dict, logs: list[dict], options: dict | None = None) -> dict:
    options = options or {}
    config: PresenceConfig = options.get("config") or _build_presence_config()
    start_date: date = options["start_date"]
    end_date: date = options["end_date"]
    day_anomalies: dict[str, dict[date, list[str]]] = options.get("day_anomalies") or {}

    daily_records: dict[date, dict] = {}
    for log in logs:
        entry_time = log.get("entry_time")
        exit_time = log.get("exit_time")
        if entry_time is None:
            continue
        day = entry_time.date()
        bucket = daily_records.setdefault(
            day,
            {
                "first_entry": None,
                "last_exit": None,
                "total_minutes": 0.0,
                "late": False,
                "incomplete": False,
            },
        )

        if bucket["first_entry"] is None or entry_time < bucket["first_entry"]:
            bucket["first_entry"] = entry_time

        if exit_time is None:
            bucket["incomplete"] = True
            continue

        if exit_time < entry_time:
            # Incoherent logs are already marked as anomalies; skip duration.
            continue

        if bucket["last_exit"] is None or exit_time > bucket["last_exit"]:
            bucket["last_exit"] = exit_time
        duration_minutes = (exit_time - entry_time).total_seconds() / 60.0
        if duration_minutes > 0:
            bucket["total_minutes"] += duration_minutes

    for day, bucket in daily_records.items():
        if bucket["first_entry"] is None:
            continue
        expected = datetime.combine(day, config.standard_start) + timedelta(minutes=config.late_minutes)
        bucket["late"] = bucket["first_entry"] > expected

    employee_days: list[dict] = []
    days_present = 0
    late_count = 0
    anomalies_count = 0
    total_minutes = 0.0

    plate = employee.get("plate_number")
    for day in _date_range(start_date, end_date):
        record = daily_records.get(day)
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

        if record["first_entry"]:
            days_present += 1
        total_minutes += record["total_minutes"]

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

        if status in {"incomplete", "anomalie"}:
            anomalies_count += 1

    days_absent = (end_date - start_date).days + 1 - days_present
    avg_minutes = total_minutes / days_present if days_present else 0.0

    return {
        "daily": employee_days,
        "days_present": days_present,
        "days_absent": days_absent,
        "late_count": late_count,
        "total_minutes": round(total_minutes, 2),
        "avg_minutes": round(avg_minutes, 2),
        "anomalies_count": anomalies_count,
    }


def _build_report_for_period(report_type: str, start_date: date, end_date: date) -> dict:
    config = _build_presence_config()
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)

    employees = _fetch_employees_real()
    employees_by_plate, employees_by_loose = _build_employee_plate_index(employees)

    logs = fetch_parking_logs_range(start_dt, end_dt)
    unknown_detections = fetch_unknown_detections_range(start_dt, end_dt)

    anomaly_result = detectRealAnomaliesFromLogs(
        logs,
        options={"employees_by_plate": employees_by_plate, "config": config},
    )
    anomalies = anomaly_result["anomalies"]
    day_anomalies = anomaly_result["day_anomalies"]
    duplicate_ids = anomaly_result["duplicate_ids"]

    logs_by_plate: dict[str, list[dict]] = {}
    accesses: list[dict] = []
    for log in logs:
        log_id = log.get("id")
        if isinstance(log_id, int) and log_id in duplicate_ids:
            continue
        plate = log.get("plate_number")
        if not plate:
            continue
        logs_by_plate.setdefault(plate, []).append(log)
        employee = _resolve_employee_for_plate(plate, employees_by_plate, employees_by_loose)
        accesses.append(
            {
                "employee_name": employee.get("full_name") if employee else None,
                "plate_number": plate,
                "entry_time": log.get("entry_time"),
                "exit_time": log.get("exit_time"),
                "status": log.get("status") or "-",
            }
        )

    accesses.sort(key=lambda item: item.get("entry_time") or datetime.min, reverse=True)

    employee_summaries: list[dict] = []
    total_presence_minutes = 0.0
    total_days_present = 0
    total_late = 0
    first_arrival: tuple[datetime, dict] | None = None
    last_exit: tuple[datetime, dict] | None = None

    for employee in employees:
        plate = employee.get("plate_number")
        metrics = computeEmployeePresenceMetrics(
            employee,
            logs_by_plate.get(plate, []) if plate else [],
            options={
                "config": config,
                "start_date": start_date,
                "end_date": end_date,
                "day_anomalies": day_anomalies,
            },
        )

        total_presence_minutes += metrics["total_minutes"]
        total_days_present += metrics["days_present"]
        total_late += metrics["late_count"]

        first_entry_times = [day["first_entry"] for day in metrics["daily"] if day.get("first_entry")]
        last_exit_times = [day["last_exit"] for day in metrics["daily"] if day.get("last_exit")]

        if first_entry_times:
            earliest = min(first_entry_times)
            if first_arrival is None or earliest < first_arrival[0]:
                first_arrival = (earliest, employee)
        if last_exit_times:
            latest = max(last_exit_times)
            if last_exit is None or latest > last_exit[0]:
                last_exit = (latest, employee)

        if not employee.get("is_active", True):
            status_global = "inactive"
        elif metrics["anomalies_count"] > 0:
            status_global = "anomalie"
        elif metrics["late_count"] > 0:
            status_global = "retard"
        elif metrics["days_present"] > 0:
            status_global = "present"
        else:
            status_global = "absent"

        employee_summaries.append(
            {
                "full_name": employee.get("full_name"),
                "plate_number": plate,
                "department": employee.get("department"),
                "employee_code": employee.get("employee_code"),
                "is_active": bool(employee.get("is_active", True)),
                "days_present": metrics["days_present"],
                "days_absent": metrics["days_absent"],
                "late_count": metrics["late_count"],
                "total_minutes": metrics["total_minutes"],
                "avg_minutes": metrics["avg_minutes"],
                "status": status_global,
                "anomalies_count": metrics["anomalies_count"],
                "daily": metrics["daily"],
            }
        )

    anomalies["unknown_plates"].extend(
        {
            "plate_number": item.get("plate_number"),
            "detected_at": item.get("detected_at"),
        }
        for item in unknown_detections
    )

    total_anomalies = sum(len(items) for items in anomalies.values())
    employees_present = sum(1 for emp in employee_summaries if emp["days_present"] > 0)

    summary = {
        "total_employees": len(employee_summaries),
        "employees_present": employees_present,
        "employees_absent": len(employee_summaries) - employees_present,
        "total_presences": total_days_present,
        "total_late": total_late,
        "total_anomalies": total_anomalies,
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
        "report_type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "employees": employee_summaries,
        "anomalies": anomalies,
        "accesses": accesses,
    }


def buildDailyReportFromDatabase(target_date: date) -> dict:
    return _build_report_for_period("daily", target_date, target_date)


def buildWeeklyReportFromDatabase(start_date: date, end_date: date) -> dict:
    return _build_report_for_period("weekly", start_date, end_date)


def buildMonthlyReportFromDatabase(year: int, month: int) -> dict:
    last_day = calendar.monthrange(int(year), int(month))[1]
    start_date = date(int(year), int(month), 1)
    end_date = date(int(year), int(month), last_day)
    return _build_report_for_period("monthly", start_date, end_date)


def buildYearlyReportFromDatabase(year: int) -> dict:
    start_date = date(int(year), 1, 1)
    end_date = date(int(year), 12, 31)
    return _build_report_for_period("yearly", start_date, end_date)


def resolve_report_period(payload: dict) -> tuple[str, date, date]:
    report_type = payload.get("report_type")
    if report_type == "daily":
        target = payload.get("date")
        if not target:
            raise ValueError("date is required for daily report")
        return report_type, target, target
    if report_type == "weekly":
        start = payload.get("start_date")
        end = payload.get("end_date")
        if start and end:
            if start > end:
                raise ValueError("start_date must be before end_date")
            return report_type, start, end
        year = payload.get("year")
        week = payload.get("week")
        if not year or not week:
            raise ValueError("year/week or start_date/end_date are required for weekly report")
        start = date.fromisocalendar(int(year), int(week), 1)
        end = date.fromisocalendar(int(year), int(week), 7)
        return report_type, start, end
    if report_type == "monthly":
        year = payload.get("year")
        month = payload.get("month")
        if not year or not month:
            raise ValueError("year and month are required for monthly report")
        last_day = calendar.monthrange(int(year), int(month))[1]
        return report_type, date(int(year), int(month), 1), date(int(year), int(month), last_day)
    if report_type == "yearly":
        year = payload.get("year")
        if not year:
            raise ValueError("year is required for yearly report")
        return report_type, date(int(year), 1, 1), date(int(year), 12, 31)
    if report_type == "custom":
        start = payload.get("start_date")
        end = payload.get("end_date")
        if not start or not end:
            raise ValueError("start_date and end_date are required for custom report")
        if start > end:
            raise ValueError("start_date must be before end_date")
        return report_type, start, end
    raise ValueError("Unsupported report_type")


def build_report_payload(payload: dict) -> dict:
    report_type, start_date, end_date = resolve_report_period(payload)
    report = _build_report_for_period(report_type, start_date, end_date)
    report["generated_at"] = datetime.now()
    return report


def _serialize_summary(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize_summary(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_summary(item) for item in value]
    return value


def generate_report(payload: dict) -> dict:
    report = build_report_payload(payload)
    settings = get_settings()
    output_dir = Path(settings.anpr_reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = report["generated_at"].strftime("%Y%m%d_%H%M%S")
    start_str = report["start_date"].strftime("%Y%m%d")
    end_str = report["end_date"].strftime("%Y%m%d")
    file_name = f"anpr_report_{report['report_type']}_{start_str}_{end_str}_{timestamp}.pdf"
    file_path = output_dir / file_name

    build_presence_pdf(report, file_path)

    config = _build_presence_config()
    metadata = {
        "attendance_start": config.standard_start.strftime("%H:%M"),
        "late_minutes": config.late_minutes,
        "dedup_minutes": config.dedup_minutes,
    }

    summary_payload = _serialize_summary(report.get("summary") or {})
    report_id = insert_attendance_report(
        report_type=report["report_type"],
        start_date=datetime.combine(report["start_date"], datetime.min.time()),
        end_date=datetime.combine(report["end_date"], datetime.min.time()),
        file_path=str(file_path),
        file_name=file_name,
        summary=summary_payload,
        metadata=metadata,
    )

    report["report_id"] = report_id
    report["file_name"] = file_name
    report["file_path"] = str(file_path)
    return report


def list_reports(limit: int = 50) -> list[dict]:
    return fetch_attendance_reports(limit=limit)


def get_report(report_id: int) -> dict | None:
    return get_attendance_report(report_id)


__all__ = [
    "buildDailyReportFromDatabase",
    "buildWeeklyReportFromDatabase",
    "buildMonthlyReportFromDatabase",
    "buildYearlyReportFromDatabase",
    "computeEmployeePresenceMetrics",
    "detectRealAnomaliesFromLogs",
    "resolve_report_period",
    "build_report_payload",
    "generate_report",
    "list_reports",
    "get_report",
]
