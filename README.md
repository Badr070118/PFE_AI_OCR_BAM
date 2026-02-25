# PFE AI OCR BAM - Monorepo OCR + MLPDR

Plateforme unifiee pour Bank Al-Maghrib regroupant :
- un module OCR Documents (upload, extraction, structuration, review)
- un module MLPDR (lecture de plaques / detection + OCR)
- un frontend React unique
- une passerelle Nginx
- une base PostgreSQL partagee
- un service Ollama (fallback LLM pour OCR)

Le projet est organise en monorepo Dockerise pour faciliter le developpement local et le deploiement.

## 1. Vue d'ensemble

### Modules metier
- `OCR Documents` : traitement de documents (images/PDF), extraction OCR, structuration, review et interactions LLM.
- `MLPDR Plaques` : detection de plaques, OCR plaques et exposition des artefacts de traitement.

### Points d'entree
- `http://localhost/` : portail web unifie (React + branding BAM)
- `http://localhost/ocr` : module OCR
- `http://localhost/mlpdr` : module MLPDR
- `http://localhost/anpr` : alias/redirection vers MLPDR (compatibilite)

## 2. Architecture technique

### Services Docker (compose principal)
- `nginx` : reverse proxy + serveur statique du build frontend Vite
- `service-ocr` : API FastAPI wrapper + code legacy OCR monte sous `/api/ocr`
- `service-mlpdr` : API FastAPI wrapper + code legacy MLPDR monte sous `/api/mlpdr`
- `postgres` : base de donnees commune (schemas separes)
- `ollama` : runtime LLM local (fallback)
- `ollama-init` : pull automatique du modele Ollama configure

### Routing (via Nginx)
- `GET /` -> frontend React (fichiers statiques)
- `GET|POST /api/ocr/*` -> `service-ocr`
- `GET|POST /api/mlpdr/*` -> `service-mlpdr`
- `GET|POST /api/anpr/*` -> alias/rewrite vers `/api/mlpdr/*`
- `GET /health/ocr` -> `service-ocr /api/ocr/health`
- `GET /health/mlpdr` -> `service-mlpdr /api/mlpdr/health`
- `GET /health/anpr` -> redirection vers `/health/mlpdr`

## 3. Technologies utilisees

### Frontend (`frontend/`)
- React 18
- Vite 5
- Axios
- CSS custom (branding / portail BAM)

### Backend OCR (`services/ocr/`)
- FastAPI
- Uvicorn
- SQLAlchemy
- Psycopg (PostgreSQL)
- Pydantic / pydantic-settings
- Pillow
- PyMuPDF (`pymupdf`)
- OpenCV (`opencv-python-headless`)
- NumPy
- Tesseract (`pytesseract` + binaire systeme)
- RapidOCR ONNX Runtime (`rapidocr-onnxruntime`)
- Requests (integrations externes / LLM)

### Backend MLPDR (`services/anpr/` -> service `service-mlpdr`)
- FastAPI
- Uvicorn
- OpenCV
- NumPy
- Pillow
- Tesseract (`pytesseract`)
- `arabic-reshaper`, `python-bidi` (rendu texte arabe)
- SQLAlchemy / Psycopg / Pydantic
- Poids YOLO (detection + OCR) via volumes Docker

### Infra / Data / Runtime
- Docker / Docker Compose
- Nginx
- PostgreSQL 16 (Alpine)
- Ollama (LLM local, fallback)

## 4. Structure du repository

```text
.
|- README.md
|- docker-compose.yml
|- docker-compose.dev.yml
|- .env.example
|- db/
|  `- init/
|     `- 001_init_schemas.sql
|- nginx/
|  |- Dockerfile
|  `- nginx.conf
|- frontend/
|  |- public/                 # assets branding BAM utilises par le frontend
|  |- src/
|  |- package.json
|  `- Dockerfile
|- services/
|  |- ocr/
|  |  |- app/
|  |  |  |- api/
|  |  |  |- core/
|  |  |  |- db/
|  |  |  |- services/
|  |  |  `- legacy/
|  |  |- requirements.txt
|  |  `- Dockerfile
|  `- anpr/                  # code MLPDR (nom historique du dossier)
|     |- app/
|     |- src/
|     |- requirements.txt
|     `- Dockerfile
|- Projet_OCR_BAM/           # assets/modeles OCR legacy (volumes)
|- MLPDR-main/               # poids/modeles MLPDR legacy (volumes)
`- assets/                   # ressources source (logo/photo BAM)
```

## 5. Prerequis

- Docker Desktop (ou Docker Engine + Compose v2)
- Ports disponibles : `80`, `5432`, `8001`, `8002` (selon config)
- Fichier `.env` present (copie de `.env.example` si besoin)

## 6. Demarrage rapide (Docker)

### Premiere execution
```bash
docker compose up --build
```

### Executions suivantes
```bash
docker compose up
```

### En arriere-plan
```bash
docker compose up -d
```

### Acces application
- `http://localhost/`
- `http://localhost/ocr`
- `http://localhost/mlpdr`

## 7. Mode developpement (hot reload backend)

Le fichier `docker-compose.dev.yml` sert d'overlay de dev pour monter le code backend et lancer Uvicorn en `--reload`.

### Lancement dev recommande
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Relance sans rebuild
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Ce que fait l'overlay
- bind mount `services/ocr/app` dans `service-ocr`
- bind mount `services/anpr/app` et `services/anpr/src` dans `service-mlpdr`
- `uvicorn --reload` sur les deux APIs
- `postgres`, `nginx`, `ollama` conserves via le compose principal

## 8. Frontend en local (hors Docker)

```bash
cd frontend
npm ci
npm run dev
```

Le frontend Vite appelle les APIs via `/api/ocr/*` et `/api/mlpdr/*` (ou `/api/anpr/*` alias cote Nginx).

## 9. Workflow de rebuild (pratique)

### Apres changement frontend (UI / CSS / React)
```bash
docker compose up -d --build nginx
```

### Apres changement backend OCR
```bash
docker compose up -d --build service-ocr
```

### Apres changement backend MLPDR
```bash
docker compose up -d --build service-mlpdr
```

### Rebuild complet (si besoin)
```bash
docker compose up -d --build
```

## 10. Endpoints principaux

### Sante
#### OCR
- `GET http://localhost:8001/health`
- `GET http://localhost:8001/api/ocr/health`
- `GET http://localhost/health/ocr`

#### MLPDR
- `GET http://localhost:8002/health`
- `GET http://localhost:8002/api/mlpdr/health`
- `GET http://localhost/health/mlpdr`
- `GET http://localhost/health/anpr` (alias)

### OCR (via Nginx)
- `POST /api/ocr/upload`
- `POST /api/ocr/ocr`
- `POST /api/ocr/ocr/invoice-table`
- `GET /api/ocr/documents`
- `POST /api/ocr/documents/{id}/ask`
- `POST /api/ocr/generate_with_llama`
- `POST /api/ocr/process_with_llama`
- `PUT /api/ocr/documents/{id}/data`
- `GET|POST|PUT /api/ocr/review/*`

### MLPDR (via Nginx)
- `POST /api/mlpdr/upload`
- `GET /api/mlpdr/artifacts/{filename}`
- `GET /api/mlpdr/received/{filename}`
- `GET /api/anpr/*` (alias Nginx vers `/api/mlpdr/*`)

## 11. Variables d'environnement importantes (`.env`)

### Application / CORS
- `APP_ENV`
- `PUBLIC_APP_URL`
- `CORS_ALLOW_ORIGINS`

### PostgreSQL
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `DATABASE_URL`

### Schemas DB
- `OCR_DB_SCHEMA` (defaut : `ocr_schema`)
- `MLPDR_DB_SCHEMA` (defaut : `mlpdr_schema`)

### OCR service
- `OCR_SERVICE_PORT`
- `OCR_UPLOAD_DIR`
- `OCR_RESULTS_DIR`
- `LLAMA_CPP_URL`, `LLAMA_CPP_MODEL`
- `LLM_FALLBACK_OLLAMA`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

### MLPDR service
- `MLPDR_SERVICE_PORT`
- `MLPDR_DETECTION_WEIGHTS_PATH`
- `MLPDR_DETECTION_CFG_PATH`
- `MLPDR_OCR_WEIGHTS_PATH`
- `MLPDR_OCR_CFG_PATH`

## 12. Base de donnees

### Initialisation des schemas
Le fichier `db/init/001_init_schemas.sql` cree automatiquement :
- `ocr_schema`
- `mlpdr_schema`

### Isolation par schema
Chaque service reapplique le `search_path` SQLAlchemy sur son schema applicatif (`ocr_schema` / `mlpdr_schema`).

## 13. Volumes et assets

### Volumes Docker
- `postgres_data` : donnees PostgreSQL
- `ollama_data` : modeles Ollama
- `ocr_uploads` : uploads OCR
- `ocr_results` : resultats OCR
- `mlpdr_outputs` : sorties MLPDR
- `nginx_logs` : logs Nginx

### Assets / modeles montes en bind (etat actuel)
- OCR : `./Projet_OCR_BAM/models` -> `/srv/service/models`
- MLPDR : `./MLPDR-main/MLPDR-main/weights` -> `/srv/service/weights`

### Branding BAM (frontend)
- `assets/` : ressources source (photo/logo)
- `frontend/public/bam-logo.png`
- `frontend/public/bam-facade-photo.jpg`
- `frontend/public/bam-facade.svg` (fallback)

## 14. Debug / verification

### Verifier la config compose
```bash
docker compose config
```

### Logs de services
```bash
docker compose logs -f nginx
docker compose logs -f service-ocr
docker compose logs -f service-mlpdr
docker compose logs -f postgres
```

### Healthchecks
```bash
curl http://localhost/health/ocr
curl http://localhost/health/mlpdr
```

### Verifier la configuration dev fusionnee
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
```

## 15. Notes utiles

- Le dossier `services/anpr/` contient le code du module MLPDR (nom de dossier historique, service expose en `service-mlpdr`).
- Le frontend affiche un portail BAM unifie, avec navigation OCR / MLPDR et branding local (`assets` -> `frontend/public`).
- L'alias `/api/anpr/*` est conserve pour compatibilite, mais le prefixe principal actuel est `/api/mlpdr/*`.

## 16. Validation locale (reference)

Commandes de verification deja utilisees sur le projet :
- `npm run build` dans `frontend/`
- `docker compose up -d --build nginx`
- `docker compose config`

---

Pour toute modification UI: rebuild `nginx`.
Pour toute modification backend: rebuild le service concerne (`service-ocr` ou `service-mlpdr`).
