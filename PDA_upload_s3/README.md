# PDA → S3 Uploader (AWS)

Repo para subir archivos (por ejemplo PDFs/Excels de PDA) desde una carpeta local a un **bucket S3**.

## Estructura

```text
pda_upload_s3_repo/
├─ notebooks/
│  └─ cargade_pda_s3.ipynb         # notebook original (sanitizado)
├─ src/
│  ├─ upload_s3.py                 # CLI principal
│  └─ pda_s3_uploader/
│     ├─ config.py                 # configuración desde .env
│     ├─ scanner.py                # busca archivos + arma keys S3
│     ├─ manifest.py               # resume (archivos ya subidos)
│     └─ uploader.py               # subida concurrente (boto3)
├─ docs/
│  ├─ DOCUMENTATION.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ run_upload.ps1
│  └─ run_upload.sh
├─ data/                           # NO se sube (archivos locales)
├─ outputs/                        # manifest/logs (NO se sube)
├─ requirements.txt
├─ requirements-dev.txt
├─ .env.example
└─ .gitignore
```

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` → `.env` y ajusta:
- `S3_BUCKET` (obligatorio)
- `S3_PREFIX` (opcional)
- `LOCAL_DIR` (carpeta local)
- `FILE_PATTERN` (ej: `*.pdf`, `**/*.pdf`, `*.xlsx`)

## Ejecutar

```bash
python src/upload_s3.py
```

Ejemplos:

```bash
python src/upload_s3.py --pattern "*.pdf" --prefix "PDA/2026_01/"
python src/upload_s3.py --dry-run
python src/upload_s3.py --skip-if-exists
```

## Resume (reanudar)

El archivo `outputs/manifest.json` guarda qué ya se subió.
