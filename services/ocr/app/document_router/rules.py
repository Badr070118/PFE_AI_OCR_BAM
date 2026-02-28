from __future__ import annotations

DOC_TYPES = ("invoice", "bank_statement", "payment_receipt", "wire_transfer")
UNKNOWN_DOC_TYPE = "unknown"

# If the best class confidence is below this threshold, we return "unknown".
UNKNOWN_THRESHOLD = 0.55

# Guardrail to avoid high confidence on very weak evidence.
MIN_ABSOLUTE_SCORE = 2.2

KEYWORD_WEIGHTS: dict[str, dict[str, float]] = {
    "invoice": {
        "facture": 1.2,
        "invoice": 1.1,
        "reference facture": 1.0,
        "client": 0.8,
        "fournisseur": 0.9,
        "designation": 0.8,
        "qte": 0.9,
        "quantite": 0.9,
        "prix unitaire": 1.0,
        "total ht": 1.4,
        "tva": 1.3,
        "ttc": 1.3,
        "echeance": 0.8,
        "conditions de paiement": 0.8,
    },
    "bank_statement": {
        "releve de compte": 1.5,
        "statement": 1.0,
        "titulaire": 0.9,
        "compte": 0.8,
        "periode": 1.0,
        "debit": 1.3,
        "credit": 1.3,
        "solde": 1.3,
        "solde debut": 1.1,
        "solde fin": 1.1,
        "total debit": 1.0,
        "total credit": 1.0,
    },
    "payment_receipt": {
        "recu de paiement": 1.5,
        "recu paiement": 1.3,
        "avis de debit": 1.2,
        "canal": 1.0,
        "agence": 0.8,
        "atm": 0.8,
        "en ligne": 0.8,
        "transaction id": 1.2,
        "auth code": 1.2,
        "statut": 0.9,
        "payeur": 1.0,
        "beneficiaire": 1.0,
        "frais": 0.8,
    },
    "wire_transfer": {
        "ordre de virement": 1.6,
        "avis de virement": 1.4,
        "virement": 1.0,
        "emetteur": 1.1,
        "beneficiaire": 1.0,
        "banque beneficiaire": 1.2,
        "iban": 1.0,
        "rib": 1.0,
        "date execution": 1.2,
        "reference": 0.8,
        "motif": 0.8,
        "frais": 0.7,
    },
}

# pattern, weight, reason template
REGEX_RULES: dict[str, list[tuple[str, float, str]]] = {
    "invoice": [
        (r"\binv-\d{4}-\d{4,6}\b", 1.6, "reference facture detectee"),
        (r"\bht\b", 0.9, "champ HT detecte"),
        (r"\btva\b", 1.0, "champ TVA detecte"),
        (r"\bttc\b", 1.0, "champ TTC detecte"),
    ],
    "bank_statement": [
        (r"\bsolde\b", 0.9, "champ Solde detecte"),
        (r"\bdebit\b", 0.9, "champ Debit detecte"),
        (r"\bcredit\b", 0.9, "champ Credit detecte"),
    ],
    "payment_receipt": [
        (r"\btxn-\d{4}-\d{4,6}\b", 1.3, "reference TXN detectee"),
        (r"\bauth(?:orization)?\s*code\b", 1.2, "code d'autorisation detecte"),
        (r"\b(recu|receipt)\b", 0.8, "motif recu detecte"),
    ],
    "wire_transfer": [
        (r"\btrf-\d{4}-\d{4,6}\b", 1.4, "reference TRF detectee"),
        (r"\bma\d{2}[0-9 ]{18,}\b", 1.2, "IBAN marocain plausible detecte"),
        (r"\bvirement\b", 0.9, "motif virement detecte"),
    ],
}
