# Esquema de salida para GRU (long format)

El pipeline genera `outputs/datos_secuenciales_para_gru.csv.gz` con:

- `Identificacion` (ID estudiante/registro)
- `semana` (1..16)
- `DescRF_Status` (target; ajusta si tu target difiere)
- Features numéricas (one-hot + numéricas) con **NaN** en variables no disponibles en semanas tempranas.

Luego el entrenamiento GRU suele convertir este long format a tensores:
`(n_estudiantes, n_semanas, n_features)` agrupando por `Identificacion`.
