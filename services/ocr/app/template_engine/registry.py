from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.template_engine.anchors import ANCHORS_BY_DOC_TYPE
from app.template_engine.schemas import (
    REQUIRED_FIELDS_BY_DOC_TYPE,
    SUPPORTED_DOC_TYPES,
    TEMPLATE_FILE_BY_DOC_TYPE,
    schema_for,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates_generated"


def _default_template(doc_type: str) -> dict[str, Any]:
    fields_rules: dict[str, list[dict[str, Any]]] = {
        "invoice": {
            "invoice_number": [
                {"type": "regex", "pattern": r"Reference\s*:\s*(INV-\d{4}-\d{6})"},
                {"type": "after_colon", "labels": ["Reference"]},
            ],
            "invoice_date": [{"type": "regex", "pattern": r"Date\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"}],
            "due_date": [{"type": "regex", "pattern": r"Echeance\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"}],
            "total_ht": [{"type": "regex", "pattern": r"Total HT\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "tva_20": [{"type": "regex", "pattern": r"TVA\s*20%\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "total_ttc": [{"type": "regex", "pattern": r"Total TTC\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "currency": [{"type": "after_colon", "labels": ["Devise"]}],
            "payment_terms": [
                {"type": "regex", "pattern": r"(Paiement\s+a\s+[^\n.]+(?:\.)?)", "group": 1}
            ],
        },
        "bank_statement": {
            "reference": [
                {"type": "regex", "pattern": r"Reference\s*:\s*(STM-\d{4}-\d{6})"},
                {"type": "after_colon", "labels": ["Reference"]},
            ],
            "bank_name": [{"type": "after_colon", "labels": ["Banque"]}],
            "account_holder": [{"type": "after_colon", "labels": ["Titulaire"]}],
            "account_number": [{"type": "after_colon", "labels": ["Compte"]}],
            "iban": [{"type": "after_colon", "labels": ["IBAN"]}],
            "period": [{"type": "after_colon", "labels": ["Periode"]}],
            "total_debit": [{"type": "regex", "pattern": r"Total debit\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "total_credit": [{"type": "regex", "pattern": r"Total credit\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "opening_balance": [{"type": "regex", "pattern": r"Solde debut\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "closing_balance": [{"type": "regex", "pattern": r"Solde fin\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "currency": [{"type": "regex", "pattern": r"\b(MAD)\b"}],
        },
        "payment_receipt": {
            "reference": [
                {"type": "regex", "pattern": r"Reference\s*:\s*(TXN-\d{4}-\d{6})"},
                {"type": "after_colon", "labels": ["Reference"]},
            ],
            "date": [{"type": "regex", "pattern": r"Date\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"}],
            "time": [{"type": "regex", "pattern": r"Heure\s*:\s*([0-9]{2}:[0-9]{2}:[0-9]{2})"}],
            "channel": [{"type": "after_colon", "labels": ["Canal"]}],
            "status": [{"type": "after_colon", "labels": ["Statut"]}],
            "purpose": [{"type": "after_colon", "labels": ["Motif"]}],
            "amount": [{"type": "regex", "pattern": r"Montant\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "fees": [{"type": "regex", "pattern": r"Frais\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "total_debited": [{"type": "regex", "pattern": r"Total debite\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "currency": [{"type": "after_colon", "labels": ["Devise"]}],
            "transaction_id": [{"type": "after_colon", "labels": ["Transaction ID"]}],
            "auth_code": [{"type": "after_colon", "labels": ["Auth code"]}],
            "secure_channel": [{"type": "after_colon", "labels": ["Canal securise"]}],
        },
        "wire_transfer": {
            "reference": [
                {"type": "regex", "pattern": r"Reference\s*:\s*(TRF-\d{4}-\d{6})"},
                {"type": "after_colon", "labels": ["Reference"]},
            ],
            "sender_name": [{"type": "after_colon", "labels": ["Nom"]}],
            "sender_bank": [{"type": "after_colon", "labels": ["Banque"]}],
            "sender_account": [{"type": "after_colon", "labels": ["Compte"]}],
            "sender_address": [{"type": "after_colon", "labels": ["Adresse"]}],
            "beneficiary_bank": [{"type": "after_colon", "labels": ["Banque beneficiaire"]}],
            "beneficiary_iban": [{"type": "after_colon", "labels": ["IBAN"]}],
            "beneficiary_rib": [{"type": "after_colon", "labels": ["RIB"]}],
            "purpose": [{"type": "after_colon", "labels": ["Motif"]}],
            "amount": [{"type": "regex", "pattern": r"Montant\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "fees": [{"type": "regex", "pattern": r"Frais\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "total": [{"type": "regex", "pattern": r"Total\s*:\s*([0-9\s.,]+\s*MAD)"}],
            "currency": [{"type": "after_colon", "labels": ["Devise"]}],
            "order_date": [{"type": "regex", "pattern": r"Date ordre\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"}],
            "execution_date": [
                {"type": "regex", "pattern": r"Date execution\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"}
            ],
            "status": [{"type": "after_colon", "labels": ["Statut"]}],
        },
    }
    return {
        "doc_type": doc_type,
        "schema": schema_for(doc_type),
        "anchors": deepcopy(ANCHORS_BY_DOC_TYPE.get(doc_type, {})),
        "fields_rules": deepcopy(fields_rules.get(doc_type, {})),
        "required_fields": deepcopy(REQUIRED_FIELDS_BY_DOC_TYPE.get(doc_type, [])),
        "template_file": TEMPLATE_FILE_BY_DOC_TYPE.get(doc_type, ""),
    }


def _normalize_template(raw_template: dict[str, Any], doc_type: str) -> dict[str, Any]:
    template = _default_template(doc_type)
    if not isinstance(raw_template, dict):
        return template
    if isinstance(raw_template.get("schema"), dict):
        template["schema"] = raw_template["schema"]
    if isinstance(raw_template.get("anchors"), dict):
        template["anchors"] = raw_template["anchors"]
    if isinstance(raw_template.get("fields_rules"), dict):
        template["fields_rules"] = raw_template["fields_rules"]
    if isinstance(raw_template.get("required_fields"), list):
        template["required_fields"] = [str(item) for item in raw_template["required_fields"]]
    template["template_file"] = str(
        raw_template.get("template_file")
        or TEMPLATE_FILE_BY_DOC_TYPE.get(doc_type, "")
    )
    template["doc_type"] = doc_type
    return template


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    for doc_type in SUPPORTED_DOC_TYPES:
        filename = TEMPLATE_FILE_BY_DOC_TYPE.get(doc_type)
        path = TEMPLATES_DIR / filename if filename else None
        loaded: dict[str, Any] = {}
        if path and path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                loaded = {}
        templates[doc_type] = _normalize_template(loaded, doc_type)
    return templates


def list_templates() -> dict[str, dict[str, Any]]:
    return deepcopy(_load_registry())


def get_template(doc_type: str) -> dict[str, Any] | None:
    if doc_type not in SUPPORTED_DOC_TYPES:
        return None
    return deepcopy(_load_registry().get(doc_type))

