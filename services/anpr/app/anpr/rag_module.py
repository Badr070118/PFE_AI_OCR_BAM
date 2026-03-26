from __future__ import annotations

"""RAG facade used by /api/anpr/ask (delegates to the new pipeline)."""

from app.anpr.rag.rag_service import ask_question as _ask_question


def answer_question(question: str) -> dict:
    return _ask_question(question)


__all__ = ["answer_question"]
