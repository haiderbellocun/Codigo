# Base de datos – GRU + Modelo Semanal

Repo de **datos** para construir la base necesaria para:

- **GRU (secuencial por semana)** → `outputs/datos_secuenciales_para_gru.csv.gz`
- **Modelo semanal** (semana 1/3/8/12) → `outputs/dataset_semana_<w>.csv.gz`
## Estructura del repo

```text
base_datos_gru_semana_repo/
├─ notebooks/
│  └─ CODIGO_BASE_MODELO.ipynb          # notebook base (sanitizado: sin credenciales)
├─ src/
│  ├─ extract.py                         # CLI: extracción SQL → outputs/base_modelo.csv.gz
│  ├─ build_gru.py                        # CLI: dataset GRU → outputs/datos_secuenciales_para_gru.csv.gz
│  ├─ build_weekly.py                     # CLI: datasets semanales → outputs/dataset_semana_<w>.csv.gz
│  ├─ db/
│  │  ├─ __init__.py
│  │  └─ mssql.py                         # conexión SQL Server (SQLAlchemy + pyodbc) usando .env
│  └─ pipelines/
│     ├─ __init__.py
│     ├─ extract_base_modelo.py           # lógica extracción: lee sql/*.sql y exporta CSV.gz
│     ├─ build_gru_dataset.py             # lógica GRU: semanas 1..16 + one-hot + NaN por variables no disponibles
│     └─ build_weekly_datasets.py         # lógica semanal: week=1/3/8/12 + one-hot + export CSV.gz
├─ sql/
│  └─ base_modelo_query.sql               # plantilla consulta extracción SQL Server
├─ templates/
│  ├─ vars_sem_1.txt
│  ├─ vars_sem_3_add.txt
│  ├─ vars_sem_8_add.txt
│  ├─ vars_sem_12_add.txt
│  ├─ schema_gru.md
│  └─ schema_semanal.md
├─ docs/
│  ├─ DOCUMENTATION.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ run_all.ps1
│  └─ run_all.sh
├─ tests/
│  └─ test_imports.py
├─ data/                                  # ignorado
├─ outputs/                                # ignorado
├─ requirements.txt
├─ .env.example
├─ .gitignore
└─ LICENSE                              # uso interno





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
