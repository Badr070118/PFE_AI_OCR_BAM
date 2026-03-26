from __future__ import annotations


def build_rag_prompt(question: str, context: str) -> str:
    system_role = (
        "SYSTEM:\n"
        "Tu es un assistant intelligent pour un systeme de gestion de parking et de presence."
    )
    instructions = (
        "INSTRUCTIONS:\n"
        "- Utilise uniquement les donnees du contexte\n"
        "- Si l'information est absente, reponds: \"information non disponible\"\n"
        "- Ne pas halluciner\n"
        "- Reponse claire, professionnelle et en francais"
    )
    return (
        f"{system_role}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"{instructions}"
    )


__all__ = ["build_rag_prompt"]
