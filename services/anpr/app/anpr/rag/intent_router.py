from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from enum import Enum

from app.anpr.rag.entity_extractor import Entities


class Intent(str, Enum):
    PLATE_OWNER = "plate_owner"
    PLATE_AUTH_STATUS = "plate_auth_status"
    PLATE_HISTORY = "plate_history"
    PLATE_LAST_ENTRY = "plate_last_entry"
    EMPLOYEE_HISTORY = "employee_history"
    EMPLOYEE_INFO = "employee_info"
    EMPLOYEE_PRESENCE = "employee_presence"
    EMPLOYEE_LATE = "employee_late"
    PRESENT_TODAY = "present_today"
    CURRENTLY_PRESENT = "currently_present"
    ABSENT_TODAY = "absent_today"
    LATE_TODAY = "late_today"
    ACCESS_BETWEEN_TIMES = "access_between_times"
    ACCESS_AT_TIME = "access_at_time"
    DENIED_TODAY = "denied_today"
    COUNT_DENIED_TODAY = "count_denied_today"
    UNKNOWN_PLATES_TODAY = "unknown_plates_today"
    ENTRY_WITHOUT_EXIT = "entry_without_exit"
    MULTI_SCANS = "multi_scans"
    MOST_DETECTED_PLATE = "most_detected_plate"
    LAST_N_ACCESS = "last_n_access"
    DEPT_PRESENT_TODAY = "dept_present_today"
    TOP_PRESENCE_TIME = "top_presence_time"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float
    reason: str


def _normalize_intent_text(text: str) -> str:
    if not text:
        return ""
    base = unicodedata.normalize("NFKC", text)
    base = "".join(ch for ch in base if unicodedata.category(ch) != "Cf")
    base = unicodedata.normalize("NFKD", base)
    base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
    base = base.replace("\u00e2\u20ac\u2122", "'")
    base = base.replace("\u2019", "'").replace("\u2018", "'")
    base = base.replace("`", "'")
    base = re.sub(r"\s+", " ", base)
    return base.lower().strip()


def detect_intent(question: str, entities: Entities) -> IntentResult:
    text = _normalize_intent_text(question)
    reason = "keywords"

    if entities.plate_normalized:
        if any(token in text for token in ["historique", "logs", "journal"]):
            return IntentResult(Intent.PLATE_HISTORY, 0.9, "plate + historique")
        if any(token in text for token in ["derniere", "last"]):
            return IntentResult(Intent.PLATE_LAST_ENTRY, 0.85, "plate + dernier")
        if any(token in text for token in ["autorise", "statut"]):
            return IntentResult(Intent.PLATE_AUTH_STATUS, 0.85, "plate + statut")
        if any(token in text for token in ["appartient", "proprietaire", "owner", "qui a"]):
            return IntentResult(Intent.PLATE_OWNER, 0.9, "plate + owner")
        return IntentResult(Intent.PLATE_OWNER, 0.7, "plate default")

    if entities.employee_name:
        if any(token in text for token in ["historique", "logs", "journal"]):
            return IntentResult(Intent.EMPLOYEE_HISTORY, 0.85, "employee + historique")
        if "retard" in text:
            return IntentResult(Intent.EMPLOYEE_LATE, 0.8, "employee + retard")
        if "present" in text:
            return IntentResult(Intent.EMPLOYEE_PRESENCE, 0.75, "employee + presence")
        return IntentResult(Intent.EMPLOYEE_INFO, 0.7, "employee default")

    if any(token in text for token in ["10 derniers", "dix derniers", "derniers acces"]):
        return IntentResult(Intent.LAST_N_ACCESS, 0.7, reason)

    if any(token in text for token in ["entre", "de "]) and entities.time_range:
        return IntentResult(Intent.ACCESS_BETWEEN_TIMES, 0.7, "time range")

    if entities.time_value and any(token in text for token in ["entre", "entree", "access", "acces", "present", "presence", "arrive"]):
        return IntentResult(Intent.ACCESS_AT_TIME, 0.65, "time value")

    if "retard" in text:
        return IntentResult(Intent.LATE_TODAY, 0.7, reason)

    if "absent" in text:
        return IntentResult(Intent.ABSENT_TODAY, 0.7, reason)

    if any(token in text for token in ["actuellement", "en ce moment"]):
        if "present" in text:
            return IntentResult(Intent.CURRENTLY_PRESENT, 0.7, reason)

    if "present" in text:
        if entities.department or "departement" in text:
            return IntentResult(Intent.DEPT_PRESENT_TODAY, 0.75, "department present")
        return IntentResult(Intent.PRESENT_TODAY, 0.65, reason)

    if any(token in text for token in ["refus", "refuse", "refusee", "refusees", "blacklist"]):
        if any(token in text for token in ["combien", "nombre"]):
            return IntentResult(Intent.COUNT_DENIED_TODAY, 0.75, "count denied")
        return IntentResult(Intent.DENIED_TODAY, 0.7, reason)

    if any(token in text for token in ["inconnu", "unknown"]):
        return IntentResult(Intent.UNKNOWN_PLATES_TODAY, 0.7, reason)

    if any(token in text for token in ["sans sortie", "sortie sans"]):
        return IntentResult(Intent.ENTRY_WITHOUT_EXIT, 0.7, reason)

    if any(token in text for token in ["scan", "doublon", "rapproch"]):
        return IntentResult(Intent.MULTI_SCANS, 0.65, reason)

    if any(token in text for token in ["plus souvent", "plus detect", "plus detecte", "plus detectee"]):
        return IntentResult(Intent.MOST_DETECTED_PLATE, 0.65, reason)

    if any(token in text for token in ["plus de temps", "cumule", "cumulee"]):
        return IntentResult(Intent.TOP_PRESENCE_TIME, 0.6, reason)

    return IntentResult(Intent.UNKNOWN, 0.2, "no match")


__all__ = ["Intent", "IntentResult", "detect_intent"]
