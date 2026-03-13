from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Any, Callable

from app.anpr.database import run_query
from app.core.config import get_settings
from app.db import IS_SQLITE

ALLOWED_TABLES = {"vehicles", "parking_logs", "unknown_detections"}

SCHEMA_CONTEXT = """\
Tables:
- vehicles(id, plate_number, owner_name, vehicle_type, status)
- parking_logs(id, plate_number, entry_time, exit_time, status, image_path)
- unknown_detections(id, plate_number, image_path, detected_at)
"""


def _date_today_clause(column: str) -> str:
    if IS_SQLITE:
        return f"DATE({column}) = DATE('now')"
    return f"DATE({column}) = CURRENT_DATE"


def _avg_minutes_expr() -> str:
    if IS_SQLITE:
        return "(julianday(exit_time) - julianday(entry_time)) * 24 * 60"
    return "EXTRACT(EPOCH FROM (exit_time - entry_time)) / 60"


def _normalize_plate(value: str) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("?", "")
    text = re.sub(r"[\s\-\|_/]+", "", text)
    return text.upper()


def _should_fill(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "-", "unknown", "n/a", "na"}
    return False


def _enrich_owner(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    needs_owner = any("plate_number" in row for row in rows)
    if not needs_owner:
        return rows

    vehicles = run_query("SELECT plate_number, owner_name, vehicle_type, status FROM vehicles")
    lookup = {}
    for vehicle in vehicles:
        plate = vehicle.get("plate_number")
        if not plate:
            continue
        lookup[_normalize_plate(plate)] = vehicle

    for row in rows:
        plate = row.get("plate_number")
        if not plate:
            continue
        info = lookup.get(_normalize_plate(plate))
        if not info:
            continue
        if _should_fill(row.get("owner_name")):
            row["owner_name"] = info.get("owner_name")
        if _should_fill(row.get("vehicle_type")):
            row["vehicle_type"] = info.get("vehicle_type")
        if "status" in row and _should_fill(row.get("status")):
            row["status"] = info.get("status")
    return rows


def _validate_sql(sql: str) -> bool:
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


def _heuristic_sql(question: str) -> str:
    text = question.lower().strip()
    text_norm = "".join(
        ch for ch in unicodedata.normalize("NFD", question) if unicodedata.category(ch) != "Mn"
    ).lower()
    time_match = re.search(r"(\\d{1,2})[:h](\\d{2})", text)

    if "unknown" in text_norm and "plate" in text_norm:
        return (
            "SELECT plate_number, detected_at, image_path "
            "FROM unknown_detections "
            f"WHERE {_date_today_clause('detected_at')} "
            "ORDER BY detected_at DESC"
        )

    if "average" in text_norm and ("duration" in text_norm or "parking" in text_norm):
        return (
            "SELECT AVG("
            + _avg_minutes_expr()
            + ") AS average_minutes "
            "FROM parking_logs "
            f"WHERE exit_time IS NOT NULL AND {_date_today_clause('entry_time')}"
        )

    if "how many" in text_norm and ("entered" in text_norm or "entries" in text_norm):
        return (
            "SELECT COUNT(*) AS entries_today "
            "FROM parking_logs "
            f"WHERE {_date_today_clause('entry_time')}"
        )

    if any(token in text_norm for token in ["entre", "entree", "entered", "accede", "acces", "access"]):
        if "aujourd" in text_norm or "today" in text_norm:
            return (
                "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, v.owner_name, v.vehicle_type "
                "FROM parking_logs p "
                "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
                f"WHERE {_date_today_clause('p.entry_time')} "
                "ORDER BY p.entry_time DESC"
            )
        return (
            "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, v.owner_name, v.vehicle_type "
            "FROM parking_logs p "
            "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
            "ORDER BY p.entry_time DESC "
            "LIMIT 20"
        )

    if "present" in text_norm and time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        target = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        target_iso = target.strftime("%Y-%m-%d %H:%M:%S")
        return (
            "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, v.owner_name, v.vehicle_type "
            "FROM parking_logs p "
            "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
            f"WHERE entry_time <= '{target_iso}' "
            f"AND (exit_time IS NULL OR exit_time >= '{target_iso}') "
            "ORDER BY p.entry_time"
        )
    if "present" in text_norm and ("today" in text_norm or "aujourd" in text_norm):
        return (
            "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, v.owner_name, v.vehicle_type "
            "FROM parking_logs p "
            "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
            f"WHERE {_date_today_clause('p.entry_time')} "
            "ORDER BY p.entry_time"
        )
    if "present" in text_norm:
        return (
            "SELECT p.plate_number, p.entry_time, p.exit_time, p.status, v.owner_name, v.vehicle_type "
            "FROM parking_logs p "
            "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
            "WHERE p.exit_time IS NULL "
            "ORDER BY p.entry_time"
        )

    if "arrive" in text_norm or "arrival" in text_norm:
        return (
            "SELECT v.owner_name, v.plate_number, p.entry_time "
            "FROM parking_logs p "
            "LEFT JOIN vehicles v ON v.plate_number = p.plate_number "
            "ORDER BY p.entry_time DESC "
            "LIMIT 10"
        )

    return "SELECT * FROM parking_logs ORDER BY entry_time DESC LIMIT 20"


_LLM_CALLER: Callable[[str], str] | None = None


def _load_llm() -> Callable[[str], str] | None:
    global _LLM_CALLER
    if _LLM_CALLER is not None:
        return _LLM_CALLER

    settings = get_settings()
    provider = settings.anpr_llm_provider.lower().strip()
    if provider in {"none", "disabled", "heuristic"}:
        _LLM_CALLER = None
        return _LLM_CALLER

    if provider in {"openai", "auto"} and settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            return None

        llm = ChatOpenAI(
            model=settings.anpr_llm_model,
            temperature=settings.anpr_llm_temperature,
            api_key=settings.openai_api_key,
        )

        def _call(prompt: str) -> str:
            tpl = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are a precise assistant. Return only the answer text."),
                    ("human", "{input}"),
                ]
            )
            return llm.invoke(tpl.format_messages(input=prompt)).content

        _LLM_CALLER = _call
        return _LLM_CALLER

    if provider in {"ollama", "auto"} and settings.ollama_base_url:
        try:
            from langchain_community.chat_models import ChatOllama
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            return None

        llm = ChatOllama(
            model=settings.anpr_llm_model,
            temperature=settings.anpr_llm_temperature,
            base_url=settings.ollama_base_url,
        )

        def _call(prompt: str) -> str:
            tpl = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are a precise assistant. Return only the answer text."),
                    ("human", "{input}"),
                ]
            )
            return llm.invoke(tpl.format_messages(input=prompt)).content

        _LLM_CALLER = _call
        return _LLM_CALLER

    _LLM_CALLER = None
    return _LLM_CALLER


_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _call_with_timeout(fn: Callable[[str], str], prompt: str, timeout_seconds: float) -> str | None:
    if timeout_seconds <= 0:
        return None
    future = _EXECUTOR.submit(fn, prompt)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        return None
    except Exception:
        return None


def generate_sql(question: str) -> str:
    llm = _load_llm()
    settings = get_settings()
    if llm:
        prompt = (
            "Generate a single SQL SELECT query for the question.\n"
            f"{SCHEMA_CONTEXT}\n"
            "Rules: Use only the tables above. Do not use write operations. "
            "Return only SQL without backticks.\n"
            f"Question: {question}"
        )
        candidate = _call_with_timeout(llm, prompt, settings.anpr_llm_timeout_seconds) or ""
        candidate = candidate.strip()
        candidate = re.sub(r"```.*?\n|```", "", candidate, flags=re.S).strip()
        candidate = candidate.strip("`").strip()
        if _validate_sql(candidate):
            return candidate
    return _heuristic_sql(question)


def generate_answer(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    llm = _load_llm()
    settings = get_settings()
    if llm:
        payload = json.dumps(rows, ensure_ascii=False, default=str)
        prompt = (
            "Answer the question using the SQL result below. "
            "If the result is empty, say no records were found. "
            "Keep the response concise.\n"
            f"Question: {question}\nSQL: {sql}\nResult: {payload}"
        )
        answer = _call_with_timeout(llm, prompt, settings.anpr_llm_timeout_seconds)
        if answer:
            return answer.strip()

    return _format_answer(question, rows)


def _format_answer(question: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No records were found for that query."

    # Single scalar summaries
    if len(rows) == 1:
        row = rows[0]
        if "entries_today" in row:
            return f"Vehicles entered today: {row['entries_today']}."
        if "average_minutes" in row:
            value = row["average_minutes"]
            if value is None:
                return "Average parking duration today: 0 minutes."
            return f"Average parking duration today: {round(float(value), 1)} minutes."

    text = question.lower().strip()

    if "unknown" in text and "plate" in text:
        lines = []
        for item in rows[:8]:
            plate = item.get("plate_number", "-")
            detected = item.get("detected_at", "")
            lines.append(f"- {plate} ({detected})")
        return "Unknown plates detected today:\n" + "\n".join(lines)

    if "present" in text:
        lines = []
        for item in rows[:10]:
            plate = item.get("plate_number", "-")
            owner = item.get("owner_name") or "Unknown"
            status = item.get("status") or ""
            lines.append(f"- {owner} ({plate}) {status}".strip())
        return "Vehicles present at that time:\n" + "\n".join(lines)

    if "arrive" in text or "arrival" in text:
        lines = []
        for item in rows[:8]:
            owner = item.get("owner_name") or "Unknown"
            plate = item.get("plate_number", "-")
            entry = item.get("entry_time", "")
            lines.append(f"- {owner} ({plate}) at {entry}")
        return "Recent arrivals:\n" + "\n".join(lines)

    # Generic fallback: show a concise list without raw SQL or dicts
    lines = []
    for item in rows[:8]:
        plate = item.get("plate_number", "-")
        status = item.get("status", "")
        entry = item.get("entry_time", "")
        lines.append(f"- {plate} {status} {entry}".strip())
    if lines:
        return "Latest records:\n" + "\n".join(lines)
    return "Records retrieved."


def answer_question(question: str) -> dict:
    sql = generate_sql(question)
    try:
        rows = run_query(sql)
    except Exception as exc:
        return {
            "answer": f"Query failed: {exc}",
            "sql": sql,
            "rows": [],
        }
    rows = _enrich_owner(rows)
    answer = generate_answer(question, sql, rows)
    return {"answer": answer, "sql": sql, "rows": rows}
