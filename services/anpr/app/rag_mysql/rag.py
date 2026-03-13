from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable

from langchain_community.utilities import SQLDatabase

from app.rag_mysql.config import get_settings
from app.rag_mysql.db import build_mysql_url, get_engine
from app.rag_mysql.sql_generator import SCHEMA_CONTEXT, heuristic_sql, validate_sql

_EXECUTOR = ThreadPoolExecutor(max_workers=4)
_LLM_CALLER: Callable[[str], str] | None = None


def _load_llm() -> Callable[[str], str] | None:
    global _LLM_CALLER
    if _LLM_CALLER is not None:
        return _LLM_CALLER

    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
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
            model=settings.llm_model,
            temperature=settings.llm_temperature,
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
            model=settings.llm_model,
            temperature=settings.llm_temperature,
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


def _database() -> SQLDatabase:
    return SQLDatabase.from_uri(build_mysql_url())


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
        candidate = _call_with_timeout(llm, prompt, settings.llm_timeout_seconds) or ""
        candidate = candidate.strip().strip("`")
        if validate_sql(candidate):
            return candidate
    return heuristic_sql(question)


def run_query(sql: str) -> list[dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as connection:
        rows = connection.execute(sql).mappings().all()
    return [dict(row) for row in rows]


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
        answer = _call_with_timeout(llm, prompt, settings.llm_timeout_seconds)
        if answer:
            return answer.strip()

    if not rows:
        return "No records were found for that query."

    if len(rows) == 1:
        return f"Result: {rows[0]}"

    preview = rows[:5]
    return f"{len(rows)} rows found. Sample: {preview}"


def ask_question(question: str) -> dict:
    sql = generate_sql(question)
    try:
        rows = run_query(sql)
    except Exception as exc:
        return {"answer": f"Query failed: {exc}", "sql": sql, "rows": []}
    answer = generate_answer(question, sql, rows)
    return {"answer": answer, "sql": sql, "rows": rows}
