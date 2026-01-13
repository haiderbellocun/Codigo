# Modelo de Rematrícula (CUN)

Repositorio para entrenar y desplegar un modelo de **rematrícula** usando:
- **XGBoost** (con opción GPU y fallback a CPU)
- **Calibración Platt (OOF)** con `TimeSeriesSplit`
- **Ajuste de conteo** (scalar) para alinear la suma de probabilidades con los reales en validación
- Export de scoring + tablas de control por **Programa** y **Sede**

## Estructura

```text
rematricula_modelo_repo/
├─ notebooks/
│  └─ rematricula.ipynb            # notebook original (sanitizado: sin credenciales)
├─ src/
│  ├─ train.py                     # entrena + calibra + exporta artefactos
│  ├─ predict.py                   # predice con artefacto .joblib
│  └─ rematricula_models/
│     ├─ data.py                   # carga CSV/SQL + label + split temporal
│     ├─ preprocessing.py          # OneHotEncoder + num passthrough
│     ├─ metrics.py                # AUC/AP/Brier + KPI + tablas de control
│     ├─ calibration.py            # Platt + ajuste de conteo
│     ├─ scoring.py                # Top-M threshold + flag gestionar
│     └─ models/
│        ├─ xgboost_model.py
│        └─ __init__.py            # MODEL_REGISTRY
├─ sql/
│  └─ extract.sql                  # plantilla de extracción (rellenar)
├─ templates/
│  └─ periodos_orden.txt           # orden de periodos usado para split
├─ docs/
│  ├─ DOCUMENTATION.md
│  ├─ ADDING_MODELS.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ run_train.ps1
│  └─ run_predict.ps1
├─ requirements.txt
├─ requirements-dev.txt
├─ .env.example
├─ .gitignore
└─ outputs/                        # modelos + reportes (ignorado por git)
```

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` → `.env` y ajusta.

## Entrenar

CSV:
```bash
python src/train.py --source csv
```

SQL:
```bash
python src/train.py --source sql --sql sql/extract.sql
```

## Predecir

```bash
python src/predict.py --data data/nuevos.csv --out outputs/reports/predicciones.csv
```

## Salidas

- `outputs/models/rematricula_xgb.joblib`
- `outputs/reports/report.json`
- `outputs/reports/scoring_valid.csv`
- `outputs/reports/control_programa.csv`
- `outputs/reports/control_sede.csv`
