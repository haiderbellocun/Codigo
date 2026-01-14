# Base de datos para GRU y modelo semanal

Este repositorio contiene el **pipeline de datos** (no el entrenamiento) para generar:

- Dataset secuencial (long) para GRU: `outputs/datos_secuenciales_para_gru.csv.gz`
- Datasets tabulares por semana (1/3/8/12): `outputs/dataset_semana_<w>.csv.gz`

## Flujo

1) **Extracción** desde SQL Server:
- lee `sql/base_modelo_query.sql`
- conecta con variables en `.env`
- genera `outputs/base_modelo.csv.gz`

2) **GRU dataset**:
- one-hot de categóricas (variables hasta semana 12 por defecto)
- construye semanas 1..16
- pone NaN en variables no disponibles en semanas tempranas
- exporta `outputs/datos_secuenciales_para_gru.csv.gz`

3) **Datasets semanales**:
- por semana, selecciona variables disponibles hasta esa semana
- one-hot y export

## Comandos

```bash
pip install -r requirements.txt

python src/extract.py
python src/build_gru.py
python src/build_weekly.py --weeks 1,3,8,12
```

Ajusta:
- `templates/vars_sem_*.txt` para variables por semana
- `sql/base_modelo_query.sql` para tu consulta real
