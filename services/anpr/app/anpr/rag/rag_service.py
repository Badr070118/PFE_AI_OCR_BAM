from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

from app.anpr.plate_utils import normalize_plate, plate_loose_key
from app.anpr.rag.answer_formatter import format_answer
from app.anpr.rag.entity_extractor import Entities, extract_entities
from app.anpr.rag.intent_router import Intent, detect_intent
from app.anpr.rag.query_builder import (
    QuerySpec,
    build_query_for_absent_today,
    build_query_for_access_at_time,
    build_query_for_access_between_times,
    build_query_for_denied_today,
    build_query_for_department_present,
    build_query_for_employee_history,
    build_query_for_employee_info,
    build_query_for_entry_without_exit,
    build_query_for_last_access,
    build_query_for_late_today,
    build_query_for_most_detected,
    build_query_for_multi_scans,
    build_query_for_plate_history,
    build_query_for_plate_last_entry,
    build_query_for_plate_owner,
    build_query_for_plate_status,
    build_query_for_present_today,
    build_query_for_top_presence,
    build_query_for_unknown_today,
)
from app.anpr.rag.sql_validator import validate_sql
from app.core.config import get_settings
from app.db import engine

LOGGER = logging.getLogger(__name__)


def _run_query(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with engine.begin() as connection:
        rows = connection.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def _fetch_employees() -> list[dict[str, Any]]:
    sql = "SELECT full_name, department, plate_number, is_active FROM employees"
    return _run_query(sql, {})


def _fetch_departments() -> list[str]:
    sql = "SELECT DISTINCT department FROM employees WHERE department IS NOT NULL"
    rows = _run_query(sql, {})
    return [row.get("department") for row in rows if row.get("department")]


def _fetch_all_plates() -> list[str]:
    sql = (
        "SELECT plate_number FROM employees "
        "UNION "
        "SELECT plate_number FROM vehicles"
    )
    rows = _run_query(sql, {})
    return [row.get("plate_number") for row in rows if row.get("plate_number")]


def _compute_late_cutoff() -> str:
    settings = get_settings()
    start_time = settings.attendance_start_time or "09:00"
    late_minutes = settings.attendance_late_minutes
    parsed = datetime.strptime(start_time, "%H:%M")
    cutoff = parsed + timedelta(minutes=late_minutes)
    return cutoff.strftime("%H:%M:%S")


def _resolve_exact_plate(plate_raw: str | None, plate_normalized: str | None) -> list[str]:
    candidates: list[str] = []
    if plate_raw:
        candidates.append(plate_raw)
    if plate_normalized and plate_normalized not in candidates:
        candidates.append(plate_normalized)
    return candidates


def _suggest_close_plates(target_plate: str) -> list[str]:
    if not target_plate:
        return []
    target_norm = normalize_plate(target_plate)
    target_key = plate_loose_key(target_plate)
    suggestions: list[str] = []
    for plate in _fetch_all_plates():
        if not plate:
            continue
        if normalize_plate(plate) == target_norm or plate_loose_key(plate) == target_key:
            suggestions.append(plate)
    return list(dict.fromkeys(suggestions))


def _postprocess_multi_scans(rows: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    if not rows:
        return []
    by_plate: dict[str, list[datetime]] = {}
    for row in rows:
        plate = row.get("plate_number")
        ts = row.get("entry_time")
        if not plate or not ts:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                continue
        by_plate.setdefault(plate, []).append(ts)

    findings: list[dict[str, Any]] = []
    for plate, times in by_plate.items():
        times.sort()
        count = 1
        max_count = 1
        for idx in range(1, len(times)):
            delta = times[idx] - times[idx - 1]
            if delta.total_seconds() <= minutes * 60:
                count += 1
                max_count = max(max_count, count)
            else:
                count = 1
        if max_count >= 2:
            findings.append({"plate_number": plate, "count": max_count})
    findings.sort(key=lambda item: item.get("count", 0), reverse=True)
    return findings


def _coerce_employee_names(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    for row in rows:
        if row.get("employee_name"):
            continue
        if row.get("full_name"):
            row["employee_name"] = row.get("full_name")
            continue
        if row.get("owner_name"):
            row["employee_name"] = row.get("owner_name")
    return rows


def _build_query(intent: Intent, entities: Entities) -> QuerySpec | None:
    today = datetime.now().date()

    if intent == Intent.PLATE_HISTORY and entities.plate_normalized:
        return build_query_for_plate_history(entities.plate_normalized, entities.date_value, entities.date_range)
    if intent == Intent.PLATE_LAST_ENTRY and entities.plate_normalized:
        return build_query_for_plate_last_entry(entities.plate_normalized)
    if intent == Intent.PLATE_AUTH_STATUS and entities.plate_normalized:
        return build_query_for_plate_status(entities.plate_normalized)
    if intent in {Intent.PRESENT_TODAY, Intent.CURRENTLY_PRESENT}:
        return build_query_for_present_today(entities.date_value or today, intent == Intent.CURRENTLY_PRESENT)
    if intent == Intent.ABSENT_TODAY:
        return build_query_for_absent_today(entities.date_value or today)
    if intent == Intent.LATE_TODAY:
        return build_query_for_late_today(entities.date_value or today, _compute_late_cutoff())
    if intent == Intent.ACCESS_BETWEEN_TIMES and entities.time_range:
        return build_query_for_access_between_times(entities.date_value or today, entities.time_range)
    if intent == Intent.ACCESS_AT_TIME and entities.time_value:
        return build_query_for_access_at_time(entities.date_value or today, entities.time_value)
    if intent in {Intent.DENIED_TODAY, Intent.COUNT_DENIED_TODAY}:
        return build_query_for_denied_today(entities.date_value or today, intent == Intent.COUNT_DENIED_TODAY)
    if intent == Intent.UNKNOWN_PLATES_TODAY:
        return build_query_for_unknown_today(entities.date_value or today)
    if intent == Intent.ENTRY_WITHOUT_EXIT:
        return build_query_for_entry_without_exit(entities.date_value)
    if intent == Intent.MULTI_SCANS:
        spec = build_query_for_multi_scans(entities.date_value, minutes=get_settings().attendance_dedup_minutes)
        spec.postprocess = lambda rows: _postprocess_multi_scans(rows, get_settings().attendance_dedup_minutes)
        return spec
    if intent == Intent.MOST_DETECTED_PLATE:
        date_range = entities.date_range
        if not date_range:
            today = datetime.now().date()
            start = today - timedelta(days=today.weekday())
            date_range = (start, start + timedelta(days=6))
        return build_query_for_most_detected(date_range)
    if intent == Intent.TOP_PRESENCE_TIME:
        date_range = entities.date_range
        if not date_range:
            today = datetime.now().date()
            start = today - timedelta(days=today.weekday())
            date_range = (start, start + timedelta(days=6))
        return build_query_for_top_presence(date_range)
    if intent == Intent.LAST_N_ACCESS:
        return build_query_for_last_access(10)
    if intent == Intent.DEPT_PRESENT_TODAY and entities.department:
        return build_query_for_department_present(entities.date_value or today, entities.department)
    if intent == Intent.EMPLOYEE_HISTORY and entities.employee_name:
        return build_query_for_employee_history(entities.employee_name, entities.date_value)
    if intent == Intent.EMPLOYEE_INFO and entities.employee_name:
        return build_query_for_employee_info(entities.employee_name)

    return None


def ask_question(question: str) -> dict[str, Any]:
    employees = _fetch_employees()
    departments = _fetch_departments()
    entities = extract_entities(
        question,
        employees=[item.get("full_name") for item in employees],
        departments=departments,
        now=datetime.now(),
    )

    intent_result = detect_intent(question, entities)
    intent = intent_result.intent

    if intent == Intent.UNKNOWN:
        return {
            "answer": "Question ambiguë. Pouvez-vous préciser la plaque, le nom ou la période ?",
            "sql": "",
            "rows": [],
            "intent": intent.value,
            "confidence": intent_result.confidence,
        }

    # Exact plate owner / auth lookup handled separately for strictness
    if intent in {Intent.PLATE_OWNER, Intent.PLATE_AUTH_STATUS} and entities.plate_normalized:
        candidates = _resolve_exact_plate(entities.plate_raw, entities.plate_normalized)
        rows: list[dict[str, Any]] = []
        sql_used = ""
        for plate in candidates:
            if intent == Intent.PLATE_OWNER:
                spec = build_query_for_plate_owner(plate, "employees")
            else:
                spec = build_query_for_plate_status(plate)
            sql_used = spec.sql
            if validate_sql(spec.sql):
                rows = _run_query(spec.sql, spec.params)
            if rows:
                break
        if not rows and intent == Intent.PLATE_OWNER:
            for plate in candidates:
                spec = build_query_for_plate_owner(plate, "vehicles")
                sql_used = spec.sql
                if validate_sql(spec.sql):
                    rows = _run_query(spec.sql, spec.params)
                if rows:
                    break
        if rows and intent == Intent.PLATE_OWNER:
            for row in rows:
                if row.get("full_name") and not row.get("owner_name"):
                    row["owner_name"] = row.get("full_name")
                if row.get("owner_name") and not row.get("full_name"):
                    row["full_name"] = row.get("owner_name")
                if row.get("department") and not row.get("vehicle_type"):
                    row["vehicle_type"] = row.get("department")
        if not rows:
            suggestions = _suggest_close_plates(entities.plate_raw or entities.plate_normalized or "")
            if suggestions:
                suggestion_text = ", ".join(suggestions[:5])
                answer = (
                    "Aucune correspondance exacte pour cette plaque. "
                    f"Plaques proches trouvées: {suggestion_text}."
                )
            else:
                answer = "Aucune correspondance exacte pour cette plaque."
            return {
                "answer": answer,
                "sql": sql_used,
                "rows": [],
                "intent": intent.value,
                "confidence": intent_result.confidence,
            }
        answer = format_answer(intent, question, rows)
        return {
            "answer": answer,
            "sql": sql_used,
            "rows": rows,
            "intent": intent.value,
            "confidence": intent_result.confidence,
        }

    spec = _build_query(intent, entities)
    if not spec:
        return {
            "answer": "Je ne peux pas répondre précisément sans plaque, nom ou période.",
            "sql": "",
            "rows": [],
            "intent": intent.value,
            "confidence": intent_result.confidence,
        }

    if not validate_sql(spec.sql):
        return {
            "answer": "Requête invalide pour cette question.",
            "sql": spec.sql,
            "rows": [],
            "intent": intent.value,
            "confidence": intent_result.confidence,
        }

    LOGGER.info("RAG intent=%s sql=%s", intent.value, spec.sql)
    rows = _run_query(spec.sql, spec.params)
    if spec.postprocess:
        rows = spec.postprocess(rows)
    rows = _coerce_employee_names(rows)
    answer = format_answer(intent, question, rows)
    return {
        "answer": answer,
        "sql": spec.sql,
        "rows": rows,
        "intent": intent.value,
        "confidence": intent_result.confidence,
    }


__all__ = ["ask_question"]
