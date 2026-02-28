from __future__ import annotations


ANCHORS_BY_DOC_TYPE: dict[str, dict[str, list[str]]] = {
    "invoice": {
        "document_title": ["FACTURE"],
        "reference": ["Reference"],
        "invoice_date": ["Date"],
        "due_date": ["Echeance"],
        "supplier_client_block": ["FOURNISSEUR CLIENT"],
        "items_header": ["Designation Qte PU Total"],
        "payment_terms_block": ["CONDITIONS DE PAIEMENT", "Paiement a"],
        "totals_block": ["TOTAUX", "Total HT", "TVA 20%", "Total TTC", "Devise"],
    },
    "bank_statement": {
        "document_title": ["RELEVE DE COMPTE"],
        "reference": ["Reference"],
        "account_info_block": ["INFORMATIONS COMPTE", "Titulaire", "Compte", "IBAN", "Periode"],
        "transactions_header": ["Date Libelle Debit Credit Solde"],
        "summary_block": ["SYNTHESE PERIODE", "Total debit", "Total credit", "Solde debut", "Solde fin"],
    },
    "payment_receipt": {
        "document_title": ["RECU DE PAIEMENT"],
        "reference": ["Reference"],
        "details_block": ["DETAILS RECU", "Date", "Heure", "Canal", "Statut"],
        "parties_block": ["PAYEUR BENEFICIAIRE", "Compte"],
        "amounts_block": ["MONTANTS ET MOTIF", "Motif", "Montant", "Frais", "Total debite", "Devise"],
        "transaction_block": ["INFORMATIONS TRANSACTION", "Transaction ID", "Auth code", "Canal securise"],
    },
    "wire_transfer": {
        "document_title": ["ORDRE DE VIREMENT"],
        "reference": ["Reference"],
        "sender_block": ["EMETTEUR", "Nom", "Banque", "Compte", "Adresse"],
        "beneficiary_block": ["BENEFICIAIRE", "Nom", "Banque beneficiaire", "IBAN", "RIB"],
        "transfer_block": ["DETAILS VIREMENT", "Motif", "Montant", "Frais", "Total", "Devise"],
        "execution_block": ["EXECUTION", "Date ordre", "Date execution", "Statut"],
    },
}

