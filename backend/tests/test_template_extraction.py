from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVICE_OCR_DIR = ROOT_DIR / "services" / "ocr"
if str(SERVICE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_OCR_DIR))

from app.template_engine.extractor import extract_with_template


def test_receipt_template_extraction_has_essential_fields() -> None:
    sample = """
    RECU DE PAIEMENT
    Reference: TXN-2026-958793
    DETAILS RECU
    Date: 19/02/2026 Heure: 11:43:10
    Canal: Agence
    Statut: SUCCES
    PAYEUR BENEFICIAIRE
    Imane Dubois Sara Bennani
    Compte: 4246 7656 6876 7665 Compte: 8934 2164 8265 5724
    MONTANTS ET MOTIF
    Motif: Remboursement avance
    Montant: 23 778.80 MAD
    Frais: 76.43 MAD
    Total debite: 23 855.23 MAD
    Devise: MAD
    INFORMATIONS TRANSACTION
    Transaction ID: TXN-2026-658663
    Auth code: 484228
    """
    payload = extract_with_template("payment_receipt", sample, None)
    data = payload["data"]
    assert data.get("reference")
    assert data.get("date")
    assert data.get("amount")
    assert data.get("transaction_id")


def test_invoice_template_extraction_has_essential_fields() -> None:
    sample = """
    FACTURE
    Reference: INV-2025-057089
    Date: 02/10/2025
    Echeance: 01/11/2025
    FOURNISSEUR CLIENT
    Ribat Solutions SARL AU Nord Logistic Maroc
    Designation Qte PU Total
    Support utilisateur 2 4 332.47 MAD 8 664.94 MAD
    CONDITIONS DE PAIEMENT TOTAUX
    Paiement a 45 jours par virement bancaire.
    Total HT: 79 809.68 MAD
    TVA 20%: 15 961.94 MAD
    Total TTC: 95 771.62 MAD
    """
    payload = extract_with_template("invoice", sample, None)
    data = payload["data"]
    assert data.get("invoice_number")
    assert data.get("total_ttc")


def test_statement_template_extraction_has_essential_fields() -> None:
    sample = """
    RELEVE DE COMPTE
    Reference: STM-2026-605276
    INFORMATIONS COMPTE
    Banque: Banque Centrale Populaire
    Titulaire: Pierre Bernard
    Compte: 0104 8603 7200 3630
    IBAN: MA73 2287 2041 9938 3294 2016 3473
    Periode: du 01/02/2026 au 28/02/2026
    Date Libelle Debit Credit Solde
    02/02/2026 Retrait GAB 4 977.05 MAD 46 101.82 MAD
    SYNTHESE PERIODE
    Total debit: 25 158.71 MAD
    Total credit: 15 720.00 MAD
    Solde fin: 31 686.06 MAD
    """
    payload = extract_with_template("bank_statement", sample, None)
    data = payload["data"]
    assert data.get("period")
    assert data.get("closing_balance")


def test_transfer_template_extraction_has_essential_fields() -> None:
    sample = """
    ORDRE DE VIREMENT
    Reference: TRF-2026-519862
    EMETTEUR
    Nom: Youssef Bennani
    BENEFICIAIRE
    Nom: Karim Leroy
    DETAILS VIREMENT
    Montant: 113 432.59 MAD
    EXECUTION
    Date execution: 30/01/2026
    """
    payload = extract_with_template("wire_transfer", sample, None)
    data = payload["data"]
    assert data.get("reference")
    assert data.get("amount")
    assert data.get("execution_date")

