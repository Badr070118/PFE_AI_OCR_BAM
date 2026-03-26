from __future__ import annotations

import logging
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import create_engine, text

from analytics import build_late_arrivals_query, format_late_arrivals

loog = logging.getLogger(__name__)
ALLOWED_TABLES = {"employees", "access_logs"}
SCHEMA_CONTEXT = """\
Tables:
- employees(id, name, plate_number, department)
- access_logs(id, plate_number, access_time, status)
"""

_EXECUTOR = ThreadPoolExecutor(max_workers=4)
_LLM_CALLER: Callable[[str], str] | None = None


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value is not None else default


def build_mysql_url() -> str:
    url = _env("MYSQL_URL")
    if url:
        return url
    host = _env("MYSQL_HOST", "127.0.0.1")
    port = _env("MYSQL_PORT", "3306")
    user = _env("MYSQL_USER", "root")
    password = _env("MYSQL_PASSWORD", "")
    database = _env("MYSQL_DATABASE", "smart_parking")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def get_engine():
    return create_engine(build_mysql_url(), pool_pre_ping=True)


def _load_llm() -> Callable[[str], str] | None:
    global _LLM_CALLER
    if _LLM_CALLER is not None:
        return _LLM_CALLER

    provider = (_env("RAG_LLM_PROVIDER", "auto") or "auto").lower().strip()
    model = _env("RAG_LLM_MODEL", "gpt-4o-mini")
    temperature = float(_env("RAG_LLM_TEMPERATURE", "0.1") or 0.1)
    openai_api_key = _env("OPENAI_API_KEY")
    ollama_base_url = _env("OLLAMA_BASE_URL")

    if provider in {"none", "disabled", "heuristic"}:
        _LLM_CALLER = None
        return _LLM_CALLER

    if provider in {"openai", "auto"} and openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            return None

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=openai_api_key,
        )

        def _call(prompt: str) -> str:
            tpl = ChatPromptTemplate.from_messages(
                [
                    ("system", "Tu es un assistant précis. Réponds uniquement avec le texte final."),
                    ("human", "{input}"),
                ]
            )
            return llm.invoke(tpl.format_messages(input=prompt)).content

        _LLM_CALLER = _call
        return _LLM_CALLER

    if provider in {"ollama", "auto"} and ollama_base_url:
        try:
            from langchain_community.chat_models import ChatOllama
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            return None

        llm = ChatOllama(
            model=model,
            temperature=temperature,
            base_url=ollama_base_url,
        )

        def _call(prompt: str) -> str:
            tpl = ChatPromptTemplate.from_messages(
                [
                    ("system", "Tu es un assistant précis. Réponds uniquement avec le texte final."),
                    ("human", "{input}"),
                ]
            )
            return llm.invoke(tpl.format_messages(input=prompt)).content

        _LLM_CALLER = _call
        return _LLM_CALLER

    _LLM_CALLER = None
    return _LLM_CALLER


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
    text_q = question.lower().strip()
    time_match = re.search(r"(\\d{1,2})[:h](\\d{2})", text_q)

    if "retard" in text_q:
        return build_late_arrivals_query()

    if "10 derniers" in text_q or "dix derniers" in text_q:
        return (
            "SELECT l.plate_number, l.access_time, l.status, e.name, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "ORDER BY l.access_time DESC "
            "LIMIT 10"
        )

    if "autorisé" in text_q or "autorise" in text_q:
        return (
            "SELECT e.name, e.plate_number, e.department "
            "FROM employees e "
            "ORDER BY e.name"
        )

    if "refus" in text_q or "refusé" in text_q or "refuse" in text_q:
        return (
            "SELECT l.plate_number, l.access_time, l.status, e.name, e.department "
            "FROM access_logs l "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "WHERE l.status = 'denied' "
            "ORDER BY l.access_time DESC "
            "LIMIT 20"
        )

    if "présent" in text_q or "present" in text_q:
        return (
            "SELECT e.name, l.plate_number, l.access_time, e.department, l.status "
            "FROM access_logs l "
            "JOIN ("
            "  SELECT plate_number, MAX(access_time) AS max_time "
            "  FROM access_logs "
            "  GROUP BY plate_number"
            ") t ON t.plate_number = l.plate_number AND t.max_time = l.access_time "
            "LEFT JOIN employees e ON e.plate_number = l.plate_number "
            "WHERE DATE(l.access_time) = CURRENT_DATE AND l.status = 'authorized' "
            "ORDER BY l.access_time DESC"
        )

    if "entré" in text_q or "entre" in text_q or "accédé" in text_q or "accede" in text_q:
        if "aujourd" in text_q:
            return (
                "SELECT e.name, l.plate_number, l.access_time, e.department "
                "FROM access_logs l "
                "LEFT JOIN employees e ON e.plate_number = l.plate_number "
                "WHERE DATE(l.access_time) = CURRENT_DATE "
                "AND l.status = 'authorized' "
                "ORDER BY l.access_time"
            )

    if time_match:
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

    return (
        "SELECT l.plate_number, l.access_time, l.status, e.name, e.department "
        "FROM access_logs l "
        "LEFT JOIN employees e ON e.plate_number = l.plate_number "
        "ORDER BY l.access_time DESC "
        "LIMIT 10"
    )


def generate_sql(question: str) -> str:
    llm = _load_llm()
    timeout_seconds = float(_env("RAG_LLM_TIMEOUT_SECONDS", "3") or 3)
    if llm:
        prompt = (
            "Génère une requête SQL SELECT pour répondre à la question.\n"
            f"{SCHEMA_CONTEXT}\n"
            "Règles: utiliser uniquement ces tables, aucune écriture. "
            "Ne renvoyer que le SQL sans backticks.\n"
            f"Question: {question}"
        )
        candidate = _call_with_timeout(llm, prompt, timeout_seconds) or ""
        candidate = candidate.strip().strip("`")
        if validate_sql(candidate):
            return candidate
    return heuristic_sql(question)


def run_query(sql: str) -> list[dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as connection:
        rows = connection.execute(text(sql)).mappings().all()
    return [dict(row) for row in rows]


def _format_answer(question: str, rows: list[dict[str, Any]]) -> str:
    text_q = question.lower().strip()
    if not rows:
        return "Aucun résultat trouvé."

    if "retard" in text_q:
        return format_late_arrivals(rows)

    if "10 derniers" in text_q or "dix derniers" in text_q:
        lines = []
        for item in rows:
            name = item.get("name") or "Inconnu"
            plate = item.get("plate_number", "-")
            when = item.get("access_time", "")
            status = item.get("status", "")
            lines.append(f"- {name} ({plate}) {status} à {when}")
        return "Derniers accès:\n" + "\n".join(lines)

    if "autorisé" in text_q or "autorise" in text_q:
        lines = []
        for item in rows[:15]:
            name = item.get("name") or "Inconnu"
            plate = item.get("plate_number", "-")
            dept = item.get("department", "")
            lines.append(f"- {name} ({plate}) {dept}".strip())
        return "Plaques autorisées:\n" + "\n".join(lines)

    if "refus" in text_q or "refusé" in text_q or "refuse" in text_q:
        lines = []
        for item in rows[:15]:
            name = item.get("name") or "Inconnu"
            plate = item.get("plate_number", "-")
            when = item.get("access_time", "")
            lines.append(f"- {name} ({plate}) à {when}")
        return "Accès refusés:\n" + "\n".join(lines)

    if "présent" in text_q or "present" in text_q:
        lines = []
        for item in rows[:20]:
            name = item.get("name") or "Inconnu"
            plate = item.get("plate_number", "-")
            dept = item.get("department", "")
            lines.append(f"- {name} ({plate}) {dept}".strip())
        return "Employés présents:\n" + "\n".join(lines)

    if "entré" in text_q or "entre" in text_q or "accédé" in text_q or "accede" in text_q:
        lines = []
        for item in rows[:20]:
            name = item.get("name") or "Inconnu"
            when = item.get("access_time", "")
            lines.append(f"- {name} à {when}")
        return "Entrées du parking:\n" + "\n".join(lines)

    if len(rows) == 1:
        return f"Résultat: {rows[0]}"

    preview = rows[:5]
    return f"{len(rows)} lignes trouvées. Exemple: {preview}"


def generate_answer(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    llm = _load_llm()
    timeout_seconds = float(_env("RAG_LLM_TIMEOUT_SECONDS", "3") or 3)
    if llm:
        payload = json.dumps(rows, ensure_ascii=False, default=str)
        prompt = (
            "Réponds en français à la question en utilisant les données ci-dessous. "
            "Si le résultat est vide, indique qu'il n'y a pas de données. "
            "Réponse courte et claire.\n"
            f"Question: {question}\nSQL: {sql}\nResult: {payload}"
        )
        answer = _call_with_timeout(llm, prompt, timeout_seconds)
        if answer:
            return answer.strip()
    return _format_answer(question, rows)


def ask_question(question: str) -> dict:
    sql = generate_sql(question)
    logging.info(f"Generated SQL: {sql}")
    try:
        rows = run_query(sql)
    except Exception as exc:
        return {"answer": f"Erreur SQL: {exc}", "sql": sql, "rows": []}
    answer = generate_answer(question, sql, rows)
    return {"answer": answer, "sql": sql, "rows": rows}
