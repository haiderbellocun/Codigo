# Permanencia – Monorepo de modelos (tabular + GRU + semanal)

Este repo está pensado para que metas **muchos modelos** de deserción/permanencia sin que se vuelva un caos.

## 1) Modelos tabulares (CatBoost/LGBM/XGB/RF)
- Entrena: `python src/train_tabular.py --model catboost`
- Predice: `python src/predict_tabular.py --model-path outputs/models/model_catboost.joblib --data data/nuevos.csv`

Usa features en `templates/features_default.txt` y target `Deserto`.

## 2) Modelo secuencial GRU (por semana)
- Entrena: `python src/train_gru.py --data data/df_secuencial.csv --id-col estudiante_id --time-col semana --target deserto`

Dataset recomendado: ver `templates/data_schema_secuencial.md`.

## 3) Semana 1 – LightGBM + SHAP (general)
- Entrena: `python src/train_semana1_lgbm.py --export-shap`
- Predice: `python src/predict_semana1_lgbm.py`

> Nota: el notebook `mod_sem_1.ipynb` original tenía credenciales hardcodeadas. Aquí lo dejamos **sanitizado** y todo va por `.env`.
