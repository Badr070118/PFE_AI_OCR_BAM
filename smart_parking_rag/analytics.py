from __future__ import annotations

from typing import Any


def build_late_arrivals_query(cutoff: str = "09:00:00", limit: int = 10) -> str:
    return (
        "SELECT e.name, e.plate_number, e.department, COUNT(*) AS late_count "
        "FROM access_logs l "
        "LEFT JOIN employees e ON e.plate_number = l.plate_number "
        "WHERE l.status = 'authorized' "
        f"AND TIME(l.access_time) > '{cutoff}' "
        "GROUP BY e.name, e.plate_number, e.department "
        "ORDER BY late_count DESC "
        f"LIMIT {int(limit)}"
    )


def format_late_arrivals(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Aucun retard détecté dans les journaux."

    top = rows[0]
    name = top.get("name") or "Un employé"
    count = top.get("late_count") or 0
    if len(rows) == 1:
        return (
            "Selon les journaux d’accès du parking, "
            f"{name} arrive souvent en retard. "
            f"Il est entré après 09h00 à {count} reprises."
        )

    lines = []
    for item in rows[:5]:
        n = item.get("name") or "Inconnu"
        c = item.get("late_count") or 0
        lines.append(f"- {n}: {c} retards")
    return (
        "Employés arrivant souvent en retard (après 09h00):\n"
        + "\n".join(lines)
    )
