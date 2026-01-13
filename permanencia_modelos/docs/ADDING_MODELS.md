# Cómo agregar más modelos

1) Sube el notebook a `notebooks/<categoria>/`.
2) Si el modelo es tabular:
   - crea una función en `src/permanencia/tabular/models.py` (si necesitas un builder nuevo)
   - o usa `src/train_tabular.py` si encaja con CatBoost/LGBM/XGB/RF.
3) Si el modelo es secuencial:
   - crea `src/train_<modelo>.py` en `src/permanencia/deep/`
   - documenta el esquema de datos en `templates/`
4) Actualiza README con:
   - cómo entrenar
   - qué inputs necesita
   - outputs que genera
