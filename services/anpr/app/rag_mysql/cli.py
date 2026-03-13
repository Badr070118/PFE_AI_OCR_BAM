from __future__ import annotations

from app.rag_mysql.rag import ask_question


def main() -> None:
    print("Smart Parking RAG (MySQL). Type 'exit' to quit.")
    while True:
        try:
            question = input("User> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        response = ask_question(question)
        print(f"Assistant> {response['answer']}")


if __name__ == "__main__":
    main()
