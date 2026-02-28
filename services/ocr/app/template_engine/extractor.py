from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.template_engine.matchers import (
    find_block_between,
    regex_search,
    value_after_colon,
    value_next_line,
    value_right_of_label_using_bbox,
)
from app.template_engine.registry import get_template
from app.template_engine.schemas import SUPPORTED_DOC_TYPES
from app.template_engine.utils import (
    clean_value,
    first_non_empty,
    normalize_line_entries,
    normalize_text,
    split_text_lines,
)


def _amount_tokens(value: str) -> list[str]:
    return re.findall(r"\d[\d\s]*[.,]\d{2}\s*MAD", value or "", flags=re.IGNORECASE)


def _extract_using_rule(
    rule: dict[str, Any],
    *,
    raw_text: str,
    raw_lines: list[str],
    line_entries: list[dict[str, Any]],
) -> tuple[str, str]:
    rule_type = str(rule.get("type", "")).strip().lower()
    if not rule_type:
        return "", ""

    if rule_type == "regex":
        pattern = str(rule.get("pattern", "")).strip()
        if not pattern:
            return "", ""
        group = int(rule.get("group", 1))
        return regex_search(raw_text, pattern, group=group)

    labels = [str(item) for item in (rule.get("labels") or []) if str(item).strip()]
    if rule_type == "after_colon":
        return value_after_colon(raw_lines, labels)
    if rule_type == "next_line":
        return value_next_line(raw_lines, labels)
    if rule_type == "right_of_label_using_bbox":
        return value_right_of_label_using_bbox(line_entries, labels)

    return "", ""


def _extract_generic_fields(
    *,
    fields_rules: dict[str, Any],
    raw_text: str,
    raw_lines: list[str],
    line_entries: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    data: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for field, rules in fields_rules.items():
        if not isinstance(rules, list):
            continue
        value = ""
        source = ""
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            value, source = _extract_using_rule(
                rule, raw_text=raw_text, raw_lines=raw_lines, line_entries=line_entries
            )
            if value:
                break
        if value:
            data[field] = clean_value(value)
            evidence[field] = clean_value(source) or clean_value(value)
    return data, evidence


def _extract_invoice_parties(raw_lines: list[str], data: dict[str, Any], evidence: dict[str, str]) -> None:
    header_idx = -1
    for idx, line in enumerate(raw_lines):
        if normalize_text(line) == normalize_text("FOURNISSEUR CLIENT"):
            header_idx = idx
            break
    if header_idx < 0 or header_idx + 1 >= len(raw_lines):
        return

    names_line = clean_value(raw_lines[header_idx + 1])
    if " AU " in names_line:
        left, right = names_line.split(" AU ", 1)
        supplier = clean_value(left)
        client = clean_value(f"AU {right}")
    elif "  " in names_line:
        left, right = re.split(r"\s{2,}", names_line, maxsplit=1)
        supplier = clean_value(left)
        client = clean_value(right)
    else:
        supplier = clean_value(names_line)
        client = ""

    if supplier and not data.get("supplier_name"):
        data["supplier_name"] = supplier
        evidence["supplier_name"] = raw_lines[header_idx + 1]
    if client and not data.get("client_name"):
        data["client_name"] = client
        evidence["client_name"] = raw_lines[header_idx + 1]

    if header_idx + 2 < len(raw_lines):
        address_line = raw_lines[header_idx + 2]
        if " Maroc" in address_line:
            parts = re.split(r"\s{2,}", address_line)
            if len(parts) >= 2:
                if not data.get("supplier_address"):
                    data["supplier_address"] = clean_value(parts[0])
                    evidence["supplier_address"] = address_line
                if not data.get("client_address"):
                    data["client_address"] = clean_value(parts[-1])
                    evidence["client_address"] = address_line


def _extract_receipt_parties(raw_lines: list[str], data: dict[str, Any], evidence: dict[str, str]) -> None:
    header_idx = -1
    for idx, line in enumerate(raw_lines):
        if normalize_text(line) == normalize_text("PAYEUR BENEFICIAIRE"):
            header_idx = idx
            break
    if header_idx < 0:
        return

    if header_idx + 1 < len(raw_lines):
        names_line = clean_value(raw_lines[header_idx + 1])
        parts = re.split(r"\s{2,}", names_line)
        if len(parts) >= 2:
            if not data.get("payer_name"):
                data["payer_name"] = clean_value(parts[0])
                evidence["payer_name"] = names_line
            if not data.get("beneficiary_name"):
                data["beneficiary_name"] = clean_value(parts[-1])
                evidence["beneficiary_name"] = names_line

    if header_idx + 2 < len(raw_lines):
        accounts_line = clean_value(raw_lines[header_idx + 2])
        matches = re.findall(r"Compte\s*:\s*([0-9 ]{10,})", accounts_line, flags=re.IGNORECASE)
        if len(matches) >= 1 and not data.get("payer_account"):
            data["payer_account"] = clean_value(matches[0])
            evidence["payer_account"] = accounts_line
        if len(matches) >= 2 and not data.get("beneficiary_account"):
            data["beneficiary_account"] = clean_value(matches[1])
            evidence["beneficiary_account"] = accounts_line


def _extract_wire_names(raw_lines: list[str], data: dict[str, Any], evidence: dict[str, str]) -> None:
    sender_block = find_block_between(raw_lines, ["EMETTEUR"], ["BENEFICIAIRE"])
    beneficiary_block = find_block_between(raw_lines, ["BENEFICIAIRE"], ["DETAILS VIREMENT", "EXECUTION"])

    for line in sender_block:
        if normalize_text(line).startswith("nom:"):
            value = clean_value(line.split(":", 1)[1])
            if value and not data.get("sender_name"):
                data["sender_name"] = value
                evidence["sender_name"] = line
            break
    for line in beneficiary_block:
        if normalize_text(line).startswith("nom:"):
            value = clean_value(line.split(":", 1)[1])
            if value and not data.get("beneficiary_name"):
                data["beneficiary_name"] = value
                evidence["beneficiary_name"] = line
            break


def _extract_invoice_items(raw_lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    rows = find_block_between(
        raw_lines,
        ["Designation Qte PU Total"],
        ["CONDITIONS DE PAIEMENT", "TOTAUX", "Total HT"],
    )
    for row in rows:
        row_clean = clean_value(row)
        qty_match = re.search(r"\s(\d+)\s+\d[\d\s]*[.,]\d{2}\s*MAD", row_clean, flags=re.IGNORECASE)
        amounts = _amount_tokens(row_clean)
        if not qty_match or len(amounts) < 2:
            continue
        qty = qty_match.group(1)
        designation = clean_value(row_clean[: qty_match.start(1)])
        unit_price = clean_value(amounts[-2])
        line_total = clean_value(amounts[-1])
        if designation and qty and unit_price and line_total:
            items.append(
                {
                    "designation": designation,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )
    return items


def _extract_statement_transactions(raw_lines: list[str]) -> list[dict[str, Any]]:
    transactions: list[dict[str, Any]] = []
    rows = find_block_between(
        raw_lines,
        ["Date Libelle Debit Credit Solde"],
        ["SYNTHESE PERIODE", "Total debit"],
    )
    credit_keywords = ("recu", "encaissement", "versement", "credit")

    for row in rows:
        line = clean_value(row)
        if not re.match(r"^\d{2}/\d{2}/\d{4}\s+", line):
            continue
        date = line[:10]
        rest = line[10:].strip()
        amounts = _amount_tokens(rest)
        if len(amounts) < 2:
            continue
        balance = clean_value(amounts[-1])
        move_amount = clean_value(amounts[-2])
        label = clean_value(rest.replace(amounts[-1], "").replace(amounts[-2], ""))
        debit = ""
        credit = ""
        if len(amounts) >= 3:
            debit = clean_value(amounts[-3])
            credit = move_amount
            label = clean_value(rest.replace(amounts[-3], "").replace(amounts[-2], "").replace(amounts[-1], ""))
        else:
            label_norm = normalize_text(label)
            if any(keyword in label_norm for keyword in credit_keywords):
                credit = move_amount
            else:
                debit = move_amount
        transactions.append(
            {
                "date": date,
                "label": label,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )
    return transactions


def _compute_confidence(data: dict[str, Any], expected_fields: list[str]) -> tuple[float, list[str]]:
    if not expected_fields:
        return 0.0, []
    missing: list[str] = []
    filled = 0
    for field in expected_fields:
        value = data.get(field)
        if isinstance(value, list):
            if len(value) > 0:
                filled += 1
            else:
                missing.append(field)
            continue
        if value is None or str(value).strip() == "":
            missing.append(field)
            continue
        filled += 1
    confidence = filled / max(1, len(expected_fields))
    return round(confidence, 4), missing


def extract_with_template(
    doc_type: str,
    raw_text: str,
    lines: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized_doc_type = (doc_type or "").strip().lower()
    raw_text = raw_text or ""
    line_entries = normalize_line_entries(lines)
    raw_lines = split_text_lines(raw_text)

    if normalized_doc_type not in SUPPORTED_DOC_TYPES:
        return {
            "data": {},
            "meta": {
                "doc_type": normalized_doc_type or "unknown",
                "confidence": 0.0,
                "missing_fields": [],
                "used_template": "",
                "evidence": {},
            },
        }

    template = get_template(normalized_doc_type)
    if not isinstance(template, dict):
        return {
            "data": {},
            "meta": {
                "doc_type": normalized_doc_type,
                "confidence": 0.0,
                "missing_fields": [],
                "used_template": "",
                "evidence": {},
            },
        }

    data = deepcopy(template.get("schema") or {})
    fields_rules = template.get("fields_rules") or {}
    generic_data, evidence = _extract_generic_fields(
        fields_rules=fields_rules,
        raw_text=raw_text,
        raw_lines=raw_lines,
        line_entries=line_entries,
    )
    data.update({key: value for key, value in generic_data.items() if value not in ("", None)})

    if normalized_doc_type == "invoice":
        _extract_invoice_parties(raw_lines, data, evidence)
        data["items"] = _extract_invoice_items(raw_lines)
    elif normalized_doc_type == "bank_statement":
        data["transactions"] = _extract_statement_transactions(raw_lines)
    elif normalized_doc_type == "payment_receipt":
        _extract_receipt_parties(raw_lines, data, evidence)
    elif normalized_doc_type == "wire_transfer":
        _extract_wire_names(raw_lines, data, evidence)

    # Use bboxes as a fallback source for key fields when available.
    bbox_backfill_labels = {
        "reference": ["Reference"],
        "invoice_number": ["Reference"],
        "amount": ["Montant"],
        "total_ttc": ["Total TTC"],
        "closing_balance": ["Solde fin"],
        "transaction_id": ["Transaction ID"],
    }
    for field, labels in bbox_backfill_labels.items():
        if field in data and str(data.get(field, "")).strip():
            continue
        value, source = value_right_of_label_using_bbox(line_entries, labels)
        if value:
            data[field] = value
            evidence[field] = source or first_non_empty(labels)

    required_fields = template.get("required_fields")
    if not isinstance(required_fields, list) or not required_fields:
        required_fields = [key for key in data.keys() if not isinstance(data.get(key), list)]
    confidence, missing_fields = _compute_confidence(data, [str(field) for field in required_fields])

    return {
        "data": data,
        "meta": {
            "doc_type": normalized_doc_type,
            "confidence": confidence,
            "missing_fields": missing_fields,
            "used_template": str(template.get("template_file", "")),
            "evidence": evidence,
        },
    }

