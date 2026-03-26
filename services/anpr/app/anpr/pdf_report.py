from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_date(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d")


def _fmt_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def _fmt_minutes(minutes: float | int | None) -> str:
    if minutes is None:
        return "-"
    total = int(round(minutes))
    hours = total // 60
    mins = total % 60
    return f"{hours:02d}:{mins:02d}"


def _status_label(value: str) -> str:
    mapping = {
        "present": "Present",
        "absent": "Absent",
        "late": "Retard",
        "incomplete": "Incomplet",
        "anomalie": "Anomalie",
        "retard": "Retard",
        "inactive": "Inactif",
    }
    return mapping.get(value, value)


def _report_type_label(report_type: str) -> str:
    return {
        "daily": "Quotidien",
        "weekly": "Hebdomadaire",
        "monthly": "Mensuel",
        "yearly": "Annuel",
        "custom": "Personnalise",
    }.get(report_type, report_type)


def _anomaly_label(value: str) -> str:
    return {
        "entry_without_exit": "Entree sans sortie",
        "incoherent": "Evenements incoherents",
        "duplicates": "Doublons rapproches",
        "unknown_plates": "Plaques inconnues",
        "blacklisted": "Plaques blacklistes",
        "no_plate": "Aucune plaque detectee",
    }.get(value, value)


def _build_kv_table(rows: Iterable[tuple[str, str]]) -> Table:
    table = Table([[key, value] for key, value in rows], colWidths=[7 * cm, 9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def build_attendance_pdf(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLarge", fontSize=18, leading=22, spaceAfter=10))
    styles.add(ParagraphStyle(name="SectionTitle", fontSize=12, leading=15, spaceBefore=10, spaceAfter=6))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        title="Rapport de presence",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    summary = report.get("summary", {})
    employees = report.get("employees", [])
    anomalies = report.get("anomalies", {})

    story = []

    story.append(Paragraph("Rapport de presence", styles["TitleLarge"]))
    story.append(Paragraph(f"Type: {_report_type_label(report.get('report_type', ''))}", styles["Normal"]))
    story.append(
        Paragraph(
            f"Periode: {_fmt_date(report.get('start_date'))} au {_fmt_date(report.get('end_date'))}",
            styles["Normal"],
        )
    )
    story.append(Paragraph(f"Genere le: {_fmt_datetime(report.get('generated_at'))}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resume global", styles["SectionTitle"]))
    summary_rows = [
        ("Total employes suivis", str(summary.get("total_employees", 0))),
        ("Employes presents", str(summary.get("employees_present", 0))),
        ("Total presences", str(summary.get("total_presences", 0))),
        ("Total retards", str(summary.get("total_late", 0))),
        ("Total anomalies", str(summary.get("total_anomalies", 0))),
        ("Temps total cumule", _fmt_minutes(summary.get("total_presence_minutes"))),
        ("Temps moyen par jour", _fmt_minutes(summary.get("avg_presence_minutes"))),
        ("Premier arrive", _fmt_datetime((summary.get("first_arrival") or {}).get("timestamp"))),
        ("Dernier sorti", _fmt_datetime((summary.get("last_exit") or {}).get("timestamp"))),
    ]
    story.append(_build_kv_table(summary_rows))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Synthese par employe", styles["SectionTitle"]))
    employee_table_data = [
        [
            "Employe",
            "Plaque",
            "Service",
            "Jours presents",
            "Jours absents",
            "Retards",
            "Temps total",
            "Temps moyen",
            "Statut",
            "Anomalies",
        ]
    ]
    for emp in employees:
        employee_table_data.append(
            [
                emp.get("full_name") or "-",
                emp.get("plate_number") or "-",
                emp.get("department") or "-",
                str(emp.get("days_present", 0)),
                str(emp.get("days_absent", 0)),
                str(emp.get("late_count", 0)),
                _fmt_minutes(emp.get("total_minutes")),
                _fmt_minutes(emp.get("avg_minutes")),
                _status_label(emp.get("status", "-")),
                str(emp.get("anomalies_count", 0)),
            ]
        )

    employee_table = Table(employee_table_data, repeatRows=1)
    employee_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(employee_table)

    story.append(PageBreak())
    story.append(Paragraph("Details journaliers", styles["SectionTitle"]))

    for emp in employees:
        story.append(Paragraph(f"{emp.get('full_name')} - {emp.get('plate_number')}", styles["Normal"]))
        daily_rows = [
            ["Date", "Premiere entree", "Derniere sortie", "Duree", "Statut", "Retard", "Anomalie"],
        ]
        for day in emp.get("daily", []) or []:
            daily_rows.append(
                [
                    _fmt_date(day.get("date")),
                    _fmt_datetime(day.get("first_entry")),
                    _fmt_datetime(day.get("last_exit")),
                    _fmt_minutes(day.get("total_minutes")),
                    _status_label(day.get("status", "-")),
                    "Oui" if day.get("late") else "Non",
                    ", ".join(day.get("anomalies") or []) or "-",
                ]
            )
        table = Table(daily_rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 10))

    story.append(PageBreak())
    story.append(Paragraph("Anomalies detectees", styles["SectionTitle"]))
    for key, items in anomalies.items():
        story.append(Paragraph(_anomaly_label(key), styles["Normal"]))
        if not items:
            story.append(Paragraph("Aucune", styles["Normal"]))
            continue
        rows = [["Plaque", "Horodatage", "Note"]]
        for item in items:
            rows.append(
                [
                    item.get("plate_number") or "-",
                    _fmt_datetime(item.get("entry_time") or item.get("detected_at")),
                    item.get("note") or "-",
                ]
            )
        table = Table(rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8))

    doc.build(story)


__all__ = ["build_attendance_pdf"]
