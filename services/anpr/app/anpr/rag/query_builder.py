from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable

from app.anpr.rag.intent_router import Intent
from app.db import IS_SQLITE


@dataclass
class QuerySpec:
    sql: str
    params: dict[str, Any]
    intent: Intent
    postprocess: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None


def _date_clause(column: str, param: str) -> str:
    if IS_SQLITE:
        return f"DATE({column}) = DATE(:{param})"
    return f"DATE({column}) = :{param}"


def _date_range_clause(column: str, start_param: str, end_param: str) -> str:
    if IS_SQLITE:
        return f"DATE({column}) BETWEEN DATE(:{start_param}) AND DATE(:{end_param})"
    return f"DATE({column}) BETWEEN :{start_param} AND :{end_param}"


def _time_between_clause(column: str, start_param: str, end_param: str) -> str:
    return f"{_time_expr(column)} BETWEEN :{start_param} AND :{end_param}"


def _time_equals_clause(column: str, param: str) -> str:
    return f"{_time_expr(column)} = :{param}"


def _time_expr(column: str) -> str:
    if IS_SQLITE:
        return f"TIME({column})"
    return f"CAST({column} AS time)"


def _duration_minutes_expr() -> str:
    if IS_SQLITE:
        return "(julianday(COALESCE(exit_time, CURRENT_TIMESTAMP)) - julianday(entry_time)) * 24 * 60"
    return "EXTRACT(EPOCH FROM (COALESCE(exit_time, NOW()) - entry_time)) / 60"


def build_query_for_plate_history(plate: str, date_value: date | None, date_range: tuple[date, date] | None) -> QuerySpec:
    where = ["p.plate_number = :plate"]
    params: dict[str, Any] = {"plate": plate}
    if date_value:
        where.append(_date_clause("p.entry_time", "target_date"))
        params["target_date"] = date_value
    if date_range:
        where.append(_date_range_clause("p.entry_time", "start_date", "end_date"))
        params["start_date"] = date_range[0]
        params["end_date"] = date_range[1]
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department AS department, "
        "v.owner_name AS owner_name, v.vehicle_type AS vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(sql=sql, params=params, intent=Intent.PLATE_HISTORY)


def build_query_for_plate_last_entry(plate: str) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department AS department, "
        "v.owner_name AS owner_name, v.vehicle_type AS vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        "WHERE p.plate_number = :plate "
        "ORDER BY p.entry_time DESC "
        "LIMIT 1"
    )
    return QuerySpec(sql=sql, params={"plate": plate}, intent=Intent.PLATE_LAST_ENTRY)


def build_query_for_present_today(target_date: date, currently_only: bool) -> QuerySpec:
    where = [_date_clause("p.entry_time", "target_date"), "p.status = 'AUTHORIZED'"]
    params: dict[str, Any] = {"target_date": target_date}
    if currently_only:
        where.append("p.exit_time IS NULL")
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department AS department, "
        "v.owner_name AS owner_name, v.vehicle_type AS vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(sql=sql, params=params, intent=Intent.CURRENTLY_PRESENT if currently_only else Intent.PRESENT_TODAY)


def build_query_for_absent_today(target_date: date) -> QuerySpec:
    sql = (
        "SELECT e.full_name, e.department, e.plate_number "
        "FROM employees e "
        "WHERE e.is_active = true "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM parking_logs p "
        "  WHERE p.plate_number = e.plate_number "
        f"  AND {_date_clause('p.entry_time', 'target_date')}"
        ") "
        "ORDER BY e.full_name"
    )
    return QuerySpec(sql=sql, params={"target_date": target_date}, intent=Intent.ABSENT_TODAY)


def build_query_for_late_today(target_date: date, cutoff_time: str) -> QuerySpec:
    sql = (
        "SELECT e.full_name AS employee_name, e.department, p.plate_number, p.entry_time "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        f"WHERE {_date_clause('p.entry_time', 'target_date')} "
        "AND p.status = 'AUTHORIZED' "
        f"AND {_time_expr('p.entry_time')} > :cutoff_time "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(
        sql=sql,
        params={"target_date": target_date, "cutoff_time": cutoff_time},
        intent=Intent.LATE_TODAY,
    )


def build_query_for_access_between_times(
    target_date: date,
    time_range: tuple[str, str],
) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department, v.owner_name, v.vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {_date_clause('p.entry_time', 'target_date')} "
        f"AND {_time_between_clause('p.entry_time', 'start_time', 'end_time')} "
        "ORDER BY p.entry_time"
    )
    return QuerySpec(
        sql=sql,
        params={"target_date": target_date, "start_time": time_range[0], "end_time": time_range[1]},
        intent=Intent.ACCESS_BETWEEN_TIMES,
    )


def build_query_for_access_at_time(target_date: date, time_value: str) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department, v.owner_name, v.vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {_date_clause('p.entry_time', 'target_date')} "
        f"AND {_time_equals_clause('p.entry_time', 'time_value')} "
        "ORDER BY p.entry_time"
    )
    return QuerySpec(
        sql=sql,
        params={"target_date": target_date, "time_value": time_value},
        intent=Intent.ACCESS_AT_TIME,
    )


def build_query_for_denied_today(target_date: date, count_only: bool) -> QuerySpec:
    if count_only:
        sql = (
            "SELECT COUNT(*) AS denied_count "
            "FROM parking_logs p "
            f"WHERE {_date_clause('p.entry_time', 'target_date')} "
            "AND p.status IN ('BLACKLISTED', 'DENIED')"
        )
        return QuerySpec(sql=sql, params={"target_date": target_date}, intent=Intent.COUNT_DENIED_TODAY)
    sql = (
        "SELECT p.plate_number, p.entry_time, p.status, "
        "e.full_name AS employee_name, e.department, v.owner_name, v.vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {_date_clause('p.entry_time', 'target_date')} "
        "AND p.status IN ('BLACKLISTED', 'DENIED') "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(sql=sql, params={"target_date": target_date}, intent=Intent.DENIED_TODAY)


def build_query_for_unknown_today(target_date: date) -> QuerySpec:
    sql = (
        "SELECT u.plate_number, u.detected_at, u.image_path "
        "FROM unknown_detections u "
        f"WHERE {_date_clause('u.detected_at', 'target_date')} "
        "ORDER BY u.detected_at DESC"
    )
    return QuerySpec(sql=sql, params={"target_date": target_date}, intent=Intent.UNKNOWN_PLATES_TODAY)


def build_query_for_entry_without_exit(target_date: date | None) -> QuerySpec:
    where = ["p.exit_time IS NULL"]
    params: dict[str, Any] = {}
    if target_date:
        where.append(_date_clause("p.entry_time", "target_date"))
        params["target_date"] = target_date
    sql = (
        "SELECT p.plate_number, p.entry_time, p.status, "
        "e.full_name AS employee_name, e.department, v.owner_name, v.vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(sql=sql, params=params, intent=Intent.ENTRY_WITHOUT_EXIT)


def build_query_for_multi_scans(target_date: date | None, minutes: int) -> QuerySpec:
    window_start = None
    window_end = None
    params: dict[str, Any] = {"minutes": minutes}
    if target_date:
        window_start = datetime.combine(target_date, datetime.min.time())
        window_end = datetime.combine(target_date, datetime.max.time())
        params["start_time"] = window_start
        params["end_time"] = window_end

    where = []
    if window_start and window_end:
        where.append("p.entry_time BETWEEN :start_time AND :end_time")
    sql = (
        "SELECT p.plate_number, p.entry_time, p.status "
        "FROM parking_logs p "
        + ("WHERE " + " AND ".join(where) + " " if where else "")
        + "ORDER BY p.plate_number, p.entry_time"
    )
    return QuerySpec(sql=sql, params=params, intent=Intent.MULTI_SCANS)


def build_query_for_most_detected(target_range: tuple[date, date]) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, COUNT(*) AS detections "
        "FROM parking_logs p "
        f"WHERE {_date_range_clause('p.entry_time', 'start_date', 'end_date')} "
        "GROUP BY p.plate_number "
        "ORDER BY detections DESC "
        "LIMIT 5"
    )
    return QuerySpec(
        sql=sql,
        params={"start_date": target_range[0], "end_date": target_range[1]},
        intent=Intent.MOST_DETECTED_PLATE,
    )


def build_query_for_last_access(limit: int) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department, v.owner_name, v.vehicle_type "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
        "ORDER BY p.entry_time DESC "
        f"LIMIT {int(limit)}"
    )
    return QuerySpec(sql=sql, params={}, intent=Intent.LAST_N_ACCESS)


def build_query_for_department_present(target_date: date, department: str) -> QuerySpec:
    sql = (
        "SELECT DISTINCT e.full_name AS employee_name, e.department, p.plate_number, p.entry_time "
        "FROM parking_logs p "
        "JOIN employees e ON e.plate_number = p.plate_number "
        f"WHERE {_date_clause('p.entry_time', 'target_date')} "
        "AND e.department = :department "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(
        sql=sql,
        params={"target_date": target_date, "department": department},
        intent=Intent.DEPT_PRESENT_TODAY,
    )


def build_query_for_top_presence(target_range: tuple[date, date]) -> QuerySpec:
    sql = (
        "SELECT p.plate_number, "
        f"SUM({_duration_minutes_expr()}) AS total_minutes, "
        "e.full_name AS employee_name, e.department "
        "FROM parking_logs p "
        "LEFT JOIN employees e ON e.plate_number = p.plate_number "
        f"WHERE {_date_range_clause('p.entry_time', 'start_date', 'end_date')} "
        "AND p.status = 'AUTHORIZED' "
        "GROUP BY p.plate_number, e.full_name, e.department "
        "ORDER BY total_minutes DESC "
        "LIMIT 5"
    )
    return QuerySpec(
        sql=sql,
        params={"start_date": target_range[0], "end_date": target_range[1]},
        intent=Intent.TOP_PRESENCE_TIME,
    )


def build_query_for_employee_history(employee_name: str, date_value: date | None) -> QuerySpec:
    where = ["LOWER(e.full_name) = LOWER(:employee_name)"]
    params: dict[str, Any] = {"employee_name": employee_name}
    if date_value:
        where.append(_date_clause("p.entry_time", "target_date"))
        params["target_date"] = date_value
    sql = (
        "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, "
        "e.full_name AS employee_name, e.department "
        "FROM parking_logs p "
        "JOIN employees e ON e.plate_number = p.plate_number "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY p.entry_time DESC"
    )
    return QuerySpec(sql=sql, params=params, intent=Intent.EMPLOYEE_HISTORY)


def build_query_for_employee_info(employee_name: str) -> QuerySpec:
    sql = (
        "SELECT e.full_name, e.department, e.plate_number, e.employee_code, e.is_active "
        "FROM employees e "
        "WHERE LOWER(e.full_name) = LOWER(:employee_name)"
    )
    return QuerySpec(sql=sql, params={"employee_name": employee_name}, intent=Intent.EMPLOYEE_INFO)


def build_query_for_plate_owner(plate: str, table: str) -> QuerySpec:
    if table == "employees":
        sql = (
            "SELECT e.full_name, e.department, e.plate_number, e.employee_code, e.is_active "
            "FROM employees e "
            "WHERE e.plate_number = :plate"
        )
    else:
        sql = (
            "SELECT v.owner_name, v.vehicle_type, v.plate_number, v.status "
            "FROM vehicles v "
            "WHERE v.plate_number = :plate"
        )
    return QuerySpec(sql=sql, params={"plate": plate}, intent=Intent.PLATE_OWNER)


def build_query_for_plate_status(plate: str) -> QuerySpec:
    sql = (
        "SELECT v.plate_number, v.status, v.owner_name, v.vehicle_type "
        "FROM vehicles v "
        "WHERE v.plate_number = :plate"
    )
    return QuerySpec(sql=sql, params={"plate": plate}, intent=Intent.PLATE_AUTH_STATUS)


__all__ = [
    "QuerySpec",
    "build_query_for_plate_history",
    "build_query_for_plate_last_entry",
    "build_query_for_present_today",
    "build_query_for_absent_today",
    "build_query_for_late_today",
    "build_query_for_access_between_times",
    "build_query_for_access_at_time",
    "build_query_for_denied_today",
    "build_query_for_unknown_today",
    "build_query_for_entry_without_exit",
    "build_query_for_multi_scans",
    "build_query_for_most_detected",
    "build_query_for_last_access",
    "build_query_for_department_present",
    "build_query_for_top_presence",
    "build_query_for_employee_history",
    "build_query_for_employee_info",
    "build_query_for_plate_owner",
    "build_query_for_plate_status",
]
