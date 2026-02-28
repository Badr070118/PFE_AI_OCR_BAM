from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPORTED_DOC_TYPES = ("invoice", "bank_statement", "payment_receipt", "wire_transfer")

TEMPLATE_FILE_BY_DOC_TYPE = {
    "invoice": "invoice_template.json",
    "bank_statement": "bank_statement_template.json",
    "payment_receipt": "payment_receipt_template.json",
    "wire_transfer": "wire_transfer_template.json",
}

DEFAULT_SCHEMA_BY_DOC_TYPE: dict[str, dict[str, Any]] = {
    "invoice": {
        "invoice_number": "",
        "invoice_date": "",
        "due_date": "",
        "supplier_name": "",
        "supplier_address": "",
        "client_name": "",
        "client_address": "",
        "payment_terms": "",
        "currency": "MAD",
        "total_ht": "",
        "tva_20": "",
        "total_ttc": "",
        "items": [],
    },
    "bank_statement": {
        "reference": "",
        "bank_name": "",
        "account_holder": "",
        "account_number": "",
        "iban": "",
        "period": "",
        "total_debit": "",
        "total_credit": "",
        "opening_balance": "",
        "closing_balance": "",
        "currency": "MAD",
        "transactions": [],
    },
    "payment_receipt": {
        "reference": "",
        "date": "",
        "time": "",
        "channel": "",
        "status": "",
        "payer_name": "",
        "payer_account": "",
        "beneficiary_name": "",
        "beneficiary_account": "",
        "purpose": "",
        "amount": "",
        "fees": "",
        "total_debited": "",
        "currency": "MAD",
        "transaction_id": "",
        "auth_code": "",
        "secure_channel": "",
    },
    "wire_transfer": {
        "reference": "",
        "sender_name": "",
        "sender_bank": "",
        "sender_account": "",
        "sender_address": "",
        "beneficiary_name": "",
        "beneficiary_bank": "",
        "beneficiary_iban": "",
        "beneficiary_rib": "",
        "purpose": "",
        "amount": "",
        "fees": "",
        "total": "",
        "currency": "MAD",
        "order_date": "",
        "execution_date": "",
        "status": "",
    },
}

REQUIRED_FIELDS_BY_DOC_TYPE: dict[str, list[str]] = {
    "invoice": ["invoice_number", "invoice_date", "total_ttc"],
    "bank_statement": ["period", "closing_balance"],
    "payment_receipt": ["reference", "date", "amount", "transaction_id"],
    "wire_transfer": ["reference", "amount", "execution_date"],
}


def schema_for(doc_type: str) -> dict[str, Any]:
    schema = DEFAULT_SCHEMA_BY_DOC_TYPE.get(doc_type, {})
    return deepcopy(schema)

