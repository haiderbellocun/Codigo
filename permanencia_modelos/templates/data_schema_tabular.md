# Esquema mínimo (tabular)

Tu dataset debe tener:

- **Target**: `Deserto` (0 = continúa, 1 = deserta)
- **Features**: ver `templates/features_default.txt`
- Opcional: columna ID (`DescRF_Identificacion`) para trazabilidad.

Formato recomendado: CSV en `data/df_final.csv`.

Ejemplo de carga:
```python
import pandas as pd
df = pd.read_csv("data/df_final.csv")
```
