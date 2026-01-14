# Base de datos – GRU + Modelo Semanal

Repo de **datos** para construir la base necesaria para:

- **GRU (secuencial por semana)** → `outputs/datos_secuenciales_para_gru.csv.gz`
- **Modelo semanal** (semana 1/3/8/12) → `outputs/dataset_semana_<w>.csv.gz`
base_datos_gru_semana_repo/
├─ notebooks/
│  └─ CODIGO_BASE_MODELO.ipynb          # notebook base (sanitizado: sin credenciales)
├─ src/
│  ├─ extract.py                         # CLI: ejecuta extracción SQL → outputs/base_modelo.csv.gz
│  ├─ build_gru.py                        # CLI: construye dataset secuencial GRU → outputs/datos_secuenciales_para_gru.csv.gz
│  ├─ build_weekly.py                     # CLI: genera datasets por semana → outputs/dataset_semana_<w>.csv.gz
│  ├─ db/
│  │  ├─ __init__.py
│  │  └─ mssql.py                         # conexión SQL Server (SQLAlchemy + pyodbc) usando .env
│  └─ pipelines/
│     ├─ __init__.py
│     ├─ extract_base_modelo.py           # lógica extracción: lee sql/*.sql y exporta CSV.gz
│     ├─ build_gru_dataset.py             # lógica GRU: semanas 1..16 + one-hot + NaN por variables no disponibles
│     └─ build_weekly_datasets.py         # lógica semanal: week=1/3/8/12 + one-hot + export CSV.gz
├─ sql/
│  └─ base_modelo_query.sql               # plantilla de consulta para extraer la base desde SQL Server
├─ templates/
│  ├─ vars_sem_1.txt                      # variables disponibles desde semana 1
│  ├─ vars_sem_3_add.txt                  # variables que se agregan desde semana 3
│  ├─ vars_sem_8_add.txt                  # variables que se agregan desde semana 8
│  ├─ vars_sem_12_add.txt                 # variables que se agregan desde semana 12
│  ├─ schema_gru.md                       # esquema esperado de salida para GRU (long format)
│  └─ schema_semanal.md                   # esquema esperado de salida para datasets semanales
├─ docs/
│  ├─ DOCUMENTATION.md                    # explicación técnica del pipeline (pasos + comandos)
│  └─ SECURITY.md                         # qué NO subir (PII, outputs, .env)
├─ scripts/
│  ├─ run_all.ps1                         # corre todo (Windows): extract → gru → weekly
│  └─ run_all.sh                          # corre todo (Linux/Mac): extract → gru → weekly
├─ tests/
│  └─ test_imports.py                     # smoke test de imports
├─ data/                                  # (ignorado) si quieres poner insumos locales
├─ outputs/                               # (ignorado) aquí se generan CSV.gz (base/gru/weekly)
├─ requirements.txt                       # dependencias del pipeline (pandas, sqlalchemy, pyodbc, dotenv)
├─ .env.example                           # variables de entorno (SQL + rutas + nombres columnas)
├─ .gitignore                             # ignora data/, outputs/, .env, csv, etc.
└─ LICENSE                                # uso interno





## Instalación
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración
Copia `.env.example` → `.env` y ajusta credenciales/paths.

## Ejecutar pipeline
```bash
python src/extract.py
python src/build_gru.py
python src/build_weekly.py --weeks 1,3,8,12
```

## Notebooks
- `notebooks/CODIGO_BASE_MODELO.ipynb` (sanitizado: sin credenciales).
