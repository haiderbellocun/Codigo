# Permanencia – Modelos (tabular + GRU + semanal)

Repositorio para centralizar modelos de **deserción/permanencia**.

# Permanencia estudiantil – Modelos (6)

Este repositorio organiza **6 modelos** para predicción de **deserción/permanencia**.

## Modelos incluidos

### Modelos Tabulares (una fila por estudiante)
1. **CatBoostClassifier**
2. **LightGBM (LGBMClassifier)**
3. **XGBoost (XGBClassifier)**
4. **Random Forest (RandomForestClassifier)**

> Estos 4 se entrenan y predicen desde consola con `src/train.py` y `src/predict.py`.

### Deep learning / Semana (notebooks)
5. **GRU (secuencial por semanas)** → `notebooks/deep/GRU.ipynb`  
6. **Modelo por Semana** (LightGBM + explicabilidad/SHAP en notebook) → `notebooks/semana/mod_sem_1.ipynb`

> Estos 2 se ejecutan desde los notebooks (por ahora). Si quieres, luego los pasamos a scripts CLI también.

---

## Estructura del repo

```text
permanencia_modelos_repo/
├─ notebooks/                      # notebooks (backup/consulta)
│  ├─ tabular/                     # CatBoost / LightGBM / XGBoost / RandomForest
│  ├─ deep/                        # ✅ GRU (secuencial por semanas)
│  │  └─ GRU.ipynb
│  └─ semana/                      # ✅ Modelo Semana 1
│     └─ mod_sem_1.ipynb
├─ src/
│  ├─ train.py                     # ENTRENAR: métricas + guarda modelo (.joblib)
│  ├─ predict.py                   # PREDICCIÓN: usa un .joblib y genera CSV con probas
│  └─ permanencia_models/
│     ├─ data.py                   # carga dataset + lee features + split X/y
│     ├─ preprocessing.py          # imputación + encoding categóricas (OrdinalEncoder)
│     ├─ metrics.py                # ROC-AUC, F1, accuracy, precision, recall, conf matrix
│     └─ models/
│        ├─ catboost_model.py
│        ├─ lightgbm_model.py
│        ├─ xgboost_model.py
│        ├─ random_forest_model.py
│        └─ __init__.py            # MODEL_REGISTRY
├─ templates/
│  └─ features_default.txt         # columnas útiles (sin target)
├─ docs/
│  ├─ DOCUMENTATION.md             # explicación técnica del pipeline
│  ├─ ADDING_MODELS.md             # cómo agregar próximos modelos/notebooks
│  └─ SECURITY.md                  # qué NO subir a git (data/outputs/.env)
├─ scripts/
│  ├─ run_all.ps1                  # entrena los 4 tabulares (Windows)
│  └─ run_all.sh                   # entrena los 4 tabulares (Linux/Mac)
├─ requirements.txt                # dependencias (catboost, lightgbm, xgboost, etc.)
├─ requirements-dev.txt            # pytest/ruff
├─ .env.example                    # configuración (DATA_PATH, TARGET_COL=Deserto, etc.)
├─ .gitignore                      # ignora data/, outputs/, .env, modelos, etc.
└─ outputs/                        # modelos + reportes (ignorado por git)


## Estructura
- `notebooks/`: notebooks (sanitizados) por categoría
- `src/`: scripts ejecutables por consola
- `templates/`: listas de features y esquemas de datos
- `docs/`: documentación del repo
- `data/`: pon tus datasets (ignorado por git)
- `outputs/`: modelos/reportes (ignorado por git)

## Instalación
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

Para GRU (TensorFlow):
```bash
pip install -r requirements-deep.txt
```

## Configuración
Copia `.env.example` a `.env` y ajusta rutas.

## Entrenar (tabular)
```bash
python src/train_tabular.py --model catboost
python src/train_tabular.py --model lightgbm
python src/train_tabular.py --model xgboost
python src/train_tabular.py --model random_forest
```

## Predicción (tabular)
```bash
python src/predict_tabular.py --model-path outputs/models/model_catboost.joblib --data data/nuevos.csv
```

## Entrenar GRU (secuencial)
```bash
python src/train_gru.py --data data/df_secuencial.csv --id-col estudiante_id --time-col semana --target deserto
```

## modelo por Semanas  (LightGBM + SHAP)
```bash
python src/train_semana1_lgbm.py --export-shap
python src/predict_semana1_lgbm.py --data data/estudiantes_nuevos.csv
```
