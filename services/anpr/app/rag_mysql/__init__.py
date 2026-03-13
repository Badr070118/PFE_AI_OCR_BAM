"""RAG assistant for Smart Parking backed by MySQL."""

from app.rag_mysql.rag import ask_question

__all__ = ["ask_question"]
