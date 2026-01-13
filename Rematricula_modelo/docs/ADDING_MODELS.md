# Cómo extender este repo

- Si quieres probar otro algoritmo (p.ej. LightGBM), crea `src/rematricula_models/models/lightgbm_model.py`
- Regístralo en `src/rematricula_models/models/__init__.py` dentro de `MODEL_REGISTRY`
- Ajusta `src/train.py --model <nombre>`
