from __future__ import annotations

import re
from datetime import datetime

ALLOWED_TABLES = {"employees", "access_logs"}

SCHEMA_CONTEXT = """\
Tables:
- employees(id, name, plate_number, department)
- access_logs(id, plate_number, access_time, status)
"""


def validate_sql(sql: str) -> bool:
    if not sql:
        return False
    normalized = sql.strip().strip(";")
    if not re.match(r"(?is)^select\\s", normalized):
        return False
    if re.search(r"(?is)\\b(insert|update|delete|drop|alter|create|truncate)\\b", normalized):
        return False
    tables = re.findall(r"(?is)\\bfrom\\s+([a-zA-Z0-9_\\.]+)|\\bjoin\\s+([a-zA-Z0-9_\\.]+)", normalized)
    for group in tables:
        for table in group:
            if not table:
                continue
            name = table.split(".")[-1].lower()
            if name not in ALLOWED_TABLES:
                return False
    return True


def heuristic_sql(question: str) -> str:
    text = question.lower().strip()
    time_match = re.search(r"(\\d{1,2})[:h](\\d{2})", text)

    if "last 10" in text or "last ten" in text:
        return (
            "SELECT l.plate_number, l.access_time, l.status, e.name, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "ORDER BY l.access_time DESC "
            "LIMIT 10"
        )

    if "entered" in text and ("today" in text or "aujourd" in text):
        return (
            "SELECT e.name, l.plate_number, l.access_time, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "WHERE DATE(l.access_time) = CURRENT_DATE "
            "AND l.status = 'authorized' "
            "ORDER BY l.access_time"
        )

    if ("arrived" in text or "arrive" in text) and time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        target = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        target_iso = target.strftime("%Y-%m-%d %H:%M:%S")
        return (
            "SELECT e.name, l.plate_number, l.access_time, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            f"WHERE l.access_time >= '{target_iso}' "
            "AND l.status = 'authorized' "
            "ORDER BY l.access_time"
        )

    if "authorized" in text and "plate" in text:
        plate_match = re.search(r"([A-Z0-9-]+)", question)
        if plate_match:
            plate = plate_match.group(1)
            return (
                "SELECT e.name, e.plate_number, e.department "
                "FROM employees e "
                f"WHERE e.plate_number = '{plate}'"
            )

    if "currently present" in text or "currently" in text:
        return (
            "SELECT e.name, l.plate_number, MAX(l.access_time) AS last_access, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "GROUP BY l.plate_number, e.name, e.department "
            "HAVING MAX(CASE WHEN l.status='authorized' THEN 1 ELSE 0 END) = 1 "
            "ORDER BY last_access DESC"
        )

    return (
        "SELECT l.plate_number, l.access_time, l.status, e.name, e.department "
        "FROM access_logs l "
        "LEFT JOIN employees e ON e.plate_number = l.plate_number "
        "ORDER BY l.access_time DESC "
        "LIMIT 10"
    )
