from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path

from app.anpr.attendance import aggregate_attendance, build_attendance_config
from app.anpr.database import fetch_attendance_reports, get_attendance_report, insert_attendance_report
from app.anpr.pdf_report import build_attendance_pdf
from app.core.config import get_settings


def resolve_report_period(payload: dict) -> tuple[date, date]:
    report_type = payload.get("report_type")
    if report_type == "daily":
        target = payload.get("date")
        if not target:
            raise ValueError("date is required for daily report")
        return target, target
    if report_type == "weekly":
        year = payload.get("year")
        week = payload.get("week")
        if not year or not week:
            raise ValueError("year and week are required for weekly report")
        start = date.fromisocalendar(int(year), int(week), 1)
        end = date.fromisocalendar(int(year), int(week), 7)
        return start, end
    if report_type == "monthly":
        year = payload.get("year")
        month = payload.get("month")
        if not year or not month:
            raise ValueError("year and month are required for monthly report")
        last_day = calendar.monthrange(int(year), int(month))[1]
        return date(int(year), int(month), 1), date(int(year), int(month), last_day)
    if report_type == "yearly":
        year = payload.get("year")
        if not year:
            raise ValueError("year is required for yearly report")
        return date(int(year), 1, 1), date(int(year), 12, 31)
    if report_type == "custom":
        start = payload.get("start_date")
        end = payload.get("end_date")
        if not start or not end:
            raise ValueError("start_date and end_date are required for custom report")
        if start > end:
            raise ValueError("start_date must be before end_date")
        return start, end
    raise ValueError("Unsupported report_type")


def _serialize_summary(summary: dict) -> dict:
    serialized = dict(summary)
    for key in ("first_arrival", "last_exit"):
        value = serialized.get(key) or {}
        timestamp = value.get("timestamp")
        if isinstance(timestamp, datetime):
            value = dict(value)
            value["timestamp"] = timestamp.isoformat()
            serialized[key] = value
    return serialized


def build_report_payload(payload: dict) -> dict:
    report_type = payload.get("report_type")
    start_date, end_date = resolve_report_period(payload)
    aggregated = aggregate_attendance(start_date, end_date)
    generated_at = datetime.now()
    return {
        "report_type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": generated_at,
        **aggregated,
    }


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

    build_attendance_pdf(report, file_path)

    config = build_attendance_config()
    metadata = {
        "attendance_start": config.standard_start.strftime("%H:%M"),
        "late_minutes": config.late_minutes,
        "dedup_minutes": config.dedup_minutes,
    }

    report_id = insert_attendance_report(
        report_type=report["report_type"],
        start_date=datetime.combine(report["start_date"], datetime.min.time()),
        end_date=datetime.combine(report["end_date"], datetime.min.time()),
        file_path=str(file_path),
        file_name=file_name,
        summary=_serialize_summary(report.get("summary", {})),
        metadata=metadata,
    )

    return {
        **report,
        "report_id": report_id,
        "file_name": file_name,
        "file_path": str(file_path),
    }


def list_reports(limit: int = 50) -> list[dict]:
    return fetch_attendance_reports(limit=limit)


def get_report(report_id: int) -> dict | None:
    return get_attendance_report(report_id)


__all__ = ["build_report_payload", "generate_report", "list_reports", "get_report", "resolve_report_period"]
