from __future__ import annotations

from typing import Any

from app.anpr.rag.intent_router import Intent


def _format_list(prefix: str, rows: list[dict[str, Any]], line_builder) -> str:
    if not rows:
        return "Aucune donnee trouvee pour cette question."
    lines = []
    for row in rows[:10]:
        lines.append(line_builder(row))
    return prefix + "\n" + "\n".join(lines)


def format_answer(
    intent: Intent,
    question: str,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> str:
    if not rows:
        return "Aucune donnee trouvee pour cette question."

    if intent == Intent.PLATE_OWNER:
        row = rows[0]
        name = row.get("full_name") or row.get("owner_name") or "-"
        plate = row.get("plate_number") or "-"
        dept = row.get("department") or row.get("vehicle_type") or "-"
        return f"La plaque {plate} est liée à {name} ({dept})."

    if intent == Intent.PLATE_AUTH_STATUS:
        row = rows[0]
        plate = row.get("plate_number") or "-"
        status = row.get("status") or "-"
        return f"Statut de la plaque {plate}: {status}."

    if intent == Intent.PLATE_LAST_ENTRY:
        row = rows[0]
        plate = row.get("plate_number") or "-"
        when = row.get("entry_time") or "-"
        status = row.get("status") or "-"
        return f"Dernière entrée de {plate}: {when} (statut {status})."

    if intent in {Intent.PLATE_HISTORY, Intent.EMPLOYEE_HISTORY, Intent.LAST_N_ACCESS}:
        return _format_list(
            "Historique d'accès:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('entry_time','-')} | {r.get('status','-')}",
        )

    if intent in {Intent.PRESENT_TODAY, Intent.CURRENTLY_PRESENT, Intent.DEPT_PRESENT_TODAY}:
        return _format_list(
            "Employés/plaques présents:",
            rows,
            lambda r: f"- {r.get('employee_name') or r.get('owner_name') or '-'} ({r.get('plate_number','-')})",
        )

    if intent == Intent.ABSENT_TODAY:
        return _format_list(
            "Employés absents aujourd'hui:",
            rows,
            lambda r: f"- {r.get('full_name','-')} ({r.get('plate_number','-')})",
        )

    if intent == Intent.LATE_TODAY:
        return _format_list(
            "Employés arrivés en retard:",
            rows,
            lambda r: f"- {r.get('employee_name','-')} ({r.get('plate_number','-' )}) à {r.get('entry_time','-')}",
        )

    if intent in {Intent.ACCESS_BETWEEN_TIMES, Intent.ACCESS_AT_TIME}:
        return _format_list(
            "Accès sur le créneau demandé:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('entry_time','-')} | {r.get('status','-')}",
        )

    if intent in {Intent.DENIED_TODAY, Intent.COUNT_DENIED_TODAY}:
        if intent == Intent.COUNT_DENIED_TODAY:
            count = rows[0].get("denied_count", 0)
            return f"Accès refusés aujourd'hui: {count}."
        return _format_list(
            "Accès refusés aujourd'hui:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('entry_time','-')} | {r.get('status','-')}",
        )

    if intent == Intent.UNKNOWN_PLATES_TODAY:
        return _format_list(
            "Plaques inconnues détectées aujourd'hui:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('detected_at','-')}",
        )

    if intent == Intent.ENTRY_WITHOUT_EXIT:
        return _format_list(
            "Entrées sans sortie:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('entry_time','-')}",
        )

    if intent == Intent.MULTI_SCANS:
        return _format_list(
            "Scans rapprochés détectés:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('count', 0)} scans",
        )

    if intent == Intent.MOST_DETECTED_PLATE:
        return _format_list(
            "Plaques les plus détectées:",
            rows,
            lambda r: f"- {r.get('plate_number','-')} | {r.get('detections', 0)} fois",
        )

    if intent == Intent.TOP_PRESENCE_TIME:
        return _format_list(
            "Temps de présence cumulé (top):",
            rows,
            lambda r: f"- {r.get('employee_name') or r.get('plate_number','-')} | {round(float(r.get('total_minutes', 0)), 1)} min",
        )

    if intent == Intent.EMPLOYEE_INFO:
        row = rows[0]
        name = row.get("full_name") or "-"
        dept = row.get("department") or "-"
        plate = row.get("plate_number") or "-"
        return f"{name} ({dept}) — plaque {plate}."

    return "Aucune donnee trouvee pour cette question."


__all__ = ["format_answer"]
