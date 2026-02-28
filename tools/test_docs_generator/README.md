# Test OCR Documents Generator

Generateur de documents de test OCR (PDF A4 + PNG 300 DPI) pour 4 types de documents:
- `invoices/`
- `bank_statements/`
- `payment_receipts/`
- `wire_transfers/`

Chaque type genere exactement 5 documents avec structure fixe et contenu variable.

## Prerequis

- Python 3.9+
- Dependances Python:
  - `reportlab`
  - `pdf2image`
- Poppler installe (necessaire pour la conversion PDF -> PNG)

## Installation

Depuis la racine du repo:

```powershell
python -m pip install -r tools/test_docs_generator/requirements.txt
```

### Poppler sur Windows

`pdf2image` a besoin des executables Poppler (`pdfinfo`, `pdftoppm`).

Options courantes:
- `winget install oschwartz10612.poppler`
- ou installer un binaire Poppler et ajouter son dossier `bin` au `PATH`.

## Execution

Depuis la racine du repo:

```powershell
python tools/test_docs_generator/generator.py
```

Sortie generee dans:

```text
test_ocr_docs/
  invoices/
  bank_statements/
  payment_receipts/
  wire_transfers/
```

Nommage:
- `invoices/invoice_01.pdf` ... `invoice_05.pdf` + PNG associes
- `bank_statements/statement_01.*` ... `statement_05.*`
- `payment_receipts/receipt_01.*` ... `receipt_05.*`
- `wire_transfers/transfer_01.*` ... `transfer_05.*`

## Notes OCR

- Documents propres et lisibles (pas de rotation, pas de filigrane, pas de decoration)
- Polices standards (`Helvetica`)
- Tableaux et sections traces de maniere stable pour faciliter l'extraction OCR
