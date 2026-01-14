# Base de datos – GRU + Modelo Semanal

Repo de **datos** para construir la base necesaria para:

- **GRU (secuencial por semana)** → `outputs/datos_secuenciales_para_gru.csv.gz`
- **Modelo semanal** (semana 1/3/8/12) → `outputs/dataset_semana_<w>.csv.gz`

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
