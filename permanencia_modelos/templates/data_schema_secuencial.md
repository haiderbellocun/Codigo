# Esquema mínimo (secuencial / GRU)

Para GRU (serie temporal por estudiante) se recomienda un CSV con:

- `SEQ_ID_COL` (por defecto: `estudiante_id`)
- `SEQ_TIME_COL` (por defecto: `semana`) – debe ser ordenable (1..16)
- `SEQ_TARGET_COL` (por defecto: `deserto`) – 0/1
- columnas numéricas/categóricas (features)

El script agrupa por estudiante, ordena por semana y arma tensores:
`(n_estudiantes, n_semanas, n_features)`.

Si tienes semanas faltantes, el script rellena con NaN y usa Masking.
