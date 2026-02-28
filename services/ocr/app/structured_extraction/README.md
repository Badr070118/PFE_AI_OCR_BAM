# Structured Extraction (PDF Native vs Scan)

## Overview

This module adds a safe structured extraction layer used by `/api/ocr/upload` and `/api/ocr/ocr`:

- Detects PDF kind: `native` vs `scan`
- Native PDF path: `pdfplumber` text/lines + table extraction (`camelot` when available)
- Scan/image path: `PaddleOCR` + `PP-Structure` (with fallback to legacy OCR)
- Keeps existing response fields and adds:
  - `structured_extraction`
  - `tables_html`
  - `pdf_kind_detection` (PDF only)
  - `structured_extraction_error` (non-blocking)

## Optional Dependencies

Base dependencies are installed from:

- `services/ocr/requirements.txt`

Optional extras:

- `services/ocr/requirements.structured_optional.txt`

Install optional extras manually:

```powershell
python -m pip install -r services/ocr/requirements.structured_optional.txt
```

## Docker

Default build installs base dependencies only.

To enable optional extras in Docker:

```powershell
docker compose build --build-arg INSTALL_STRUCTURED_EXTRAS=1 service-ocr
docker compose up -d service-ocr
```

## Windows Poppler

`pdf2image` needs Poppler binaries.

Options:

1. `winget install oschwartz10612.poppler`
2. or `choco install poppler`
3. Add Poppler `bin` directory to `PATH`

## Camelot

Camelot table extraction is optional.
If Camelot or Ghostscript is not available, the pipeline logs a warning and continues with `pdfplumber` only.

## Response Example

```json
{
  "raw_text": "...",
  "doc_type_detection": { "doc_type": "invoice", "confidence": 0.82, "reasons": ["..."] },
  "pdf_kind_detection": { "kind": "native", "has_text": true, "text_char_count": 742, "page_count": 1 },
  "structured_extraction": {
    "doc_kind": "native",
    "engine": "camelot",
    "raw_text": "...",
    "lines": [{ "text": "Facture ...", "bbox": [30, 40, 500, 55], "page": 1, "confidence": 1.0 }],
    "tables": [{ "page": 1, "bbox": null, "html": "<table>...</table>", "cells": [] }],
    "meta": { "table_count": 1 }
  },
  "tables_html": [{ "page": 1, "html": "<table>...</table>" }]
}
```
