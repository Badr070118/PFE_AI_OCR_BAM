from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.document_router.router import detect_document_type


def test_detect_invoice_type() -> None:
    sample = """
    FACTURE
    Reference: INV-2026-000123
    Client: Nord Logistic Maroc
    Designation | Qte | PU | Total
    Maintenance applicative 2 1500.00 3000.00
    Total HT: 3000.00
    TVA 20%: 600.00
    Total TTC: 3600.00
    """
    result = detect_document_type(sample, None)
    assert result["doc_type"] == "invoice"
    assert result["confidence"] >= 0.55


def test_detect_bank_statement_type() -> None:
    sample = """
    RELEVE DE COMPTE
    Titulaire: Sara El Amrani
    Periode: du 01/01/2026 au 31/01/2026
    Date Libelle Debit Credit Solde
    02/01/2026 Paiement TPE 120.50 0.00 5200.40
    04/01/2026 Virement recu 0.00 2200.00 7400.40
    08/01/2026 Facture electricite 450.00 0.00 6950.40
    Total debit: 570.50
    Total credit: 2200.00
    Solde fin: 6950.40
    """
    result = detect_document_type(sample, None)
    assert result["doc_type"] == "bank_statement"
    assert result["confidence"] >= 0.55


def test_detect_payment_receipt_type() -> None:
    sample = """
    RECU DE PAIEMENT
    Reference: TXN-2026-001122
    Date: 12/02/2026 Heure: 14:03:22
    Canal: En ligne
    Payeur: Mehdi Bennani
    Beneficiaire: Atlas Services SARL
    Montant: 1500.00 MAD
    Frais: 5.00 MAD
    Statut: SUCCES
    Transaction ID: TXN-2026-001122
    Auth code: 883921
    """
    result = detect_document_type(sample, None)
    assert result["doc_type"] == "payment_receipt"
    assert result["confidence"] >= 0.55


def test_detect_wire_transfer_type() -> None:
    sample = """
    ORDRE DE VIREMENT
    Reference: TRF-2026-778899
    Emetteur: Youssef Alaoui
    Beneficiaire: Nadia Idrissi
    Banque beneficiaire: CIH Bank
    IBAN: MA64 0112 0000 3300 0012 3456 7890
    RIB: 0112 0000 3300 0012 3456 7890
    Motif: Paiement fournisseur
    Date execution: 14/02/2026
    """
    result = detect_document_type(sample, None)
    assert result["doc_type"] == "wire_transfer"
    assert result["confidence"] >= 0.55
