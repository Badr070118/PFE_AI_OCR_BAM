from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from app.anpr.plate_utils import normalize_plate


@dataclass
class Entities:
    plate_raw: str | None = None
    plate_normalized: str | None = None
    employee_name: str | None = None
    department: str | None = None
    date_value: date | None = None
    date_range: tuple[date, date] | None = None
    time_value: str | None = None
    time_range: tuple[str, str] | None = None
    status_keyword: str | None = None


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    base = unicodedata.normalize("NFKD", text)
    base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
    base = base.replace("’", "'")
    base = base.replace("`", "'")
    base = re.sub(r"\s+", " ", base)
    return base.lower().strip()


def _parse_date_literal(token: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    return None


def _week_range(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def _month_range(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1, day=1)
    else:
        next_month = start.replace(month=start.month + 1, day=1)
    end = next_month - timedelta(days=1)
    return start, end


def _year_range(today: date) -> tuple[date, date]:
    start = date(today.year, 1, 1)
    end = date(today.year, 12, 31)
    return start, end


def extract_plate(question: str) -> tuple[str | None, str | None]:
    if not question:
        return None, None
    patterns = [
        r"(\d{3,6}\s*[-–]\s*[\u0600-\u06FF]\s*[-–]\s*\d{1,3})",
        r"(\d{3,6}\s*[-–]\s*[A-Z]\s*[-–]\s*\d{1,3})",
        r"plaque\s+['\"]?([A-Za-z0-9\u0600-\u06FF\-\s]{3,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            normalized = normalize_plate(raw)
            return raw, normalized
    return None, None


def extract_time_range(question: str) -> tuple[str, str] | None:
    if not question:
        return None
    match = re.search(r"entre\s+(\d{1,2}[:h]\d{2})\s+et\s+(\d{1,2}[:h]\d{2})", question, re.IGNORECASE)
    if not match:
        match = re.search(r"de\s+(\d{1,2}[:h]\d{2})\s+a\s+(\d{1,2}[:h]\d{2})", question, re.IGNORECASE)
    if not match:
        return None
    start = match.group(1).replace("h", ":")
    end = match.group(2).replace("h", ":")
    return (f"{start}:00" if len(start) == 5 else start, f"{end}:00" if len(end) == 5 else end)


def extract_time_value(question: str) -> str | None:
    if not question:
        return None
    match = re.search(r"(?:a|à)\s*(\d{1,2}[:h]\d{2})", question, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).replace("h", ":")
    return f"{value}:00" if len(value) == 5 else value


def extract_date(question: str, today: date) -> tuple[date | None, tuple[date, date] | None]:
    if not question:
        return None, None
    norm = _normalize_text(question)

    for token in re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", question):
        parsed = _parse_date_literal(token)
        if parsed:
            return parsed, None

    if "aujourd" in norm:
        return today, None
    if "hier" in norm:
        return today - timedelta(days=1), None

    if "semaine derniere" in norm or "semaine dernière" in norm:
        start, end = _week_range(today - timedelta(days=7))
        return None, (start, end)
    if "cette semaine" in norm:
        start, end = _week_range(today)
        return None, (start, end)

    if "mois dernier" in norm:
        last_month = today.replace(day=1) - timedelta(days=1)
        start, end = _month_range(last_month)
        return None, (start, end)
    if "ce mois" in norm or "mois-ci" in norm:
        start, end = _month_range(today)
        return None, (start, end)

    if "annee derniere" in norm or "année dernière" in norm:
        last_year = date(today.year - 1, 6, 15)
        start, end = _year_range(last_year)
        return None, (start, end)
    if "cette annee" in norm or "cette année" in norm:
        start, end = _year_range(today)
        return None, (start, end)

    return None, None


def extract_department(question: str, departments: Iterable[str]) -> str | None:
    if not question:
        return None
    norm = _normalize_text(question)
    for dept in sorted(departments, key=len, reverse=True):
        if not dept:
            continue
        dept_norm = _normalize_text(dept)
        if dept_norm and dept_norm in norm:
            return dept
    match = re.search(r"departement\s+([a-zA-Z0-9_-]{2,30})", norm)
    if match:
        return match.group(1).upper()
    return None


def extract_employee_name(question: str, employees: Iterable[str]) -> str | None:
    if not question:
        return None
    norm = _normalize_text(question)
    best = None
    for name in sorted(employees, key=len, reverse=True):
        if not name:
            continue
        name_norm = _normalize_text(name)
        if name_norm and name_norm in norm:
            best = name
            break
    return best


def extract_status_keyword(question: str) -> str | None:
    norm = _normalize_text(question)
    if any(token in norm for token in ["refus", "blacklist", "bloque", "bloqué"]):
        return "DENIED"
    if "autorise" in norm or "autorisé" in norm:
        return "AUTHORIZED"
    if "inconnu" in norm or "unknown" in norm:
        return "UNKNOWN"
    return None


def extract_entities(
    question: str,
    employees: Iterable[str],
    departments: Iterable[str],
    now: datetime | None = None,
) -> Entities:
    now = now or datetime.now()
    today = now.date()
    plate_raw, plate_normalized = extract_plate(question)
    date_value, date_range = extract_date(question, today)
    time_range = extract_time_range(question)
    time_value = extract_time_value(question) if not time_range else None
    employee_name = extract_employee_name(question, employees)
    department = extract_department(question, departments)
    status_keyword = extract_status_keyword(question)
    return Entities(
        plate_raw=plate_raw,
        plate_normalized=plate_normalized,
        employee_name=employee_name,
        department=department,
        date_value=date_value,
        date_range=date_range,
        time_value=time_value,
        time_range=time_range,
        status_keyword=status_keyword,
    )


__all__ = [
    "Entities",
    "extract_entities",
    "extract_plate",
    "extract_time_range",
    "extract_time_value",
    "extract_date",
    "extract_department",
    "extract_employee_name",
    "extract_status_keyword",
]
