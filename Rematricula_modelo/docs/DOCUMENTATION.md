# Modelo de Rematrícula (XGBoost + Calibración)

Este proyecto entrena un modelo para estimar probabilidad de **rematrícula** (`y_rematricula`).

## Flujo
1) Cargar datos (CSV o SQL)
2) Normalizar periodos y crear `periodo_orden`
3) Crear etiqueta `y_rematricula` (si no existe)
4) Split temporal: último periodo como validación
5) Entrenar XGBoost
6) Calibración Platt (OOF con `TimeSeriesSplit`)
7) Ajuste de conteo (scalar) para alinear esperados con reales en validación
8) Exportar artefactos + scoring

## Entrenar
### Desde CSV
- Pon tu CSV en `data/df_rematricula.csv` o ajusta `DATA_PATH` en `.env`

```bash
python src/train.py --source csv
```

### Desde SQL
- Completa `sql/extract.sql`
- Configura `.env` con `SQL_SERVER`, `SQL_DB`, etc.

```bash
python src/train.py --source sql --sql sql/extract.sql
```

## Predicción
```bash
python src/predict.py --model-path outputs/models/rematricula_xgb.joblib --data data/nuevos.csv --out outputs/reports/predicciones.csv
```

Genera:
- `p_raw`: probabilidad sin calibrar
- `p_cal`: Platt calibrada
- `y_proba`: calibrada + ajuste de conteo
- `gestionar`: flag Top-M según capacidad (`TOPM`)
