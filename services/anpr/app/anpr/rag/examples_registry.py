from __future__ import annotations

from dataclasses import dataclass

from app.anpr.rag.intent_router import Intent


@dataclass(frozen=True)
class Example:
    question: str
    intent: Intent


EXAMPLES: list[Example] = [
    Example("Qui a la plaque exacte 38119-و-1 ?", Intent.PLATE_OWNER),
    Example("À qui appartient la plaque 38119-و-1 ?", Intent.PLATE_OWNER),
    Example("Historique de la plaque 38119-و-1", Intent.PLATE_HISTORY),
    Example("Derniere entree de la plaque 38119-و-1", Intent.PLATE_LAST_ENTRY),
    Example("Cette plaque est-elle autorisee ?", Intent.PLATE_AUTH_STATUS),
    Example("Qui est present aujourd'hui ?", Intent.PRESENT_TODAY),
    Example("Qui est actuellement present ?", Intent.CURRENTLY_PRESENT),
    Example("Qui est arrive en retard aujourd'hui ?", Intent.LATE_TODAY),
    Example("Qui est absent aujourd'hui ?", Intent.ABSENT_TODAY),
    Example("Quels acces ont ete refuses aujourd'hui ?", Intent.DENIED_TODAY),
    Example("Quels vehicules inconnus ont ete detectes aujourd'hui ?", Intent.UNKNOWN_PLATES_TODAY),
    Example("Qui est entre entre 08:00 et 09:00 ?", Intent.ACCESS_BETWEEN_TIMES),
    Example("Historique d'acces de Badr El Khadir", Intent.EMPLOYEE_HISTORY),
    Example("Employes du departement DSI presents aujourd'hui", Intent.DEPT_PRESENT_TODAY),
    Example("Quels sont les 10 derniers acces ?", Intent.LAST_N_ACCESS),
    Example("Quelle plaque a ete detectee le plus souvent cette semaine ?", Intent.MOST_DETECTED_PLATE),
    Example("Qui est entre sans sortie ?", Intent.ENTRY_WITHOUT_EXIT),
]


__all__ = ["Example", "EXAMPLES"]
