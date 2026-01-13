# Permanencia – Modelos (tabular + GRU + semanal)

Repositorio para centralizar modelos de **deserción/permanencia**.

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

## Semana 1 (LightGBM + SHAP)
```bash
python src/train_semana1_lgbm.py --export-shap
python src/predict_semana1_lgbm.py --data data/estudiantes_nuevos.csv
```
