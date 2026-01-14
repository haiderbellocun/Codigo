# Carga masiva: Excel → SQL Server (staging table)

Este repo convierte y carga un Excel a una tabla de **SQL Server** de forma robusta:

- Lee un Excel (`.xlsx`)
- Consulta el esquema real de la tabla destino (`INFORMATION_SCHEMA.COLUMNS`)
- Convierte tipos (int/decimal/datetime/bit/text) y valida **NOT NULL**
- Carga usando una **tabla staging física** (`<TABLA>_TEMP_CARGA`)
- Inserta al destino y elimina la staging

## Estructura

```text
carga_excel_sqlserver_repo/
├─ notebooks/
│  └─ subir_archivos_sql.ipynb       # notebook original (sanitizado)
├─ src/
│  ├─ upload.py                      # CLI principal
│  └─ excel_to_sql/
│     ├─ io.py                       # lectura Excel
│     ├─ schema.py                   # leer esquema SQL (INFORMATION_SCHEMA)
│     ├─ convert.py                  # conversión/validación de tipos
│     ├─ load.py                     # staging → insert destino
│     └─ db/
│        └─ mssql.py                 # conexión SQL Server + fast_executemany
├─ docs/
│  ├─ DOCUMENTATION.md               # guía técnica
│  └─ SECURITY.md                    # qué NO subir a git
├─ scripts/
│  ├─ run_upload.ps1                 # Windows
│  └─ run_upload.sh                  # Linux/Mac
├─ data/                             # NO se sube (ejemplos locales)
├─ outputs/                          # NO se sube (logs/artefactos)
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

- `SQL_SERVER`, `SQL_DB`, `SQL_DRIVER`
- `SQL_TRUSTED=yes` (Windows/AD) **o** `SQL_TRUSTED=no` + `SQL_USER`/`SQL_PASSWORD`
- `DEST_SCHEMA`, `DEST_TABLE`
- `INPUT_EXCEL`, `INPUT_SHEET`

## Ejecutar

```bash
python src/upload.py
```

Opciones:

- `--chunksize 1000` (batch)
- `--truncate-destination` (⚠️ borra la tabla destino antes de insertar)
- `--no-strict` (no falla si un NOT NULL se vuelve NULL por conversión)

## Notas importantes

- El Excel debe tener **las mismas columnas** que la tabla (no importa mayúsculas/minúsculas).
- Si el Excel trae columnas extra, se ignoran.
- Si faltan columnas requeridas, el proceso falla con error claro.
