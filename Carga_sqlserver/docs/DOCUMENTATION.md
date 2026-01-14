# Documentación técnica

## ¿Por qué staging table?

En SQL Server, para carga masiva desde pandas es común:
- evitar inserts gigantes con demasiados parámetros
- mantener consistencia con el esquema del destino

Este pipeline crea una tabla staging:

1. `DROP TABLE` staging si existe
2. `SELECT TOP 0 * INTO staging FROM destino` (clona estructura)
3. `df.to_sql(... if_exists="append")` hacia staging
4. `INSERT INTO destino SELECT ... FROM staging`
5. `DROP TABLE staging`

## Conversión de tipos

Se basa en `INFORMATION_SCHEMA.COLUMNS`:

- int/bigint/smallint/tinyint → `pd.to_numeric(...).astype("Int64")`
- decimal/numeric/float/... → `pd.to_numeric(...)`
- date/datetime/... → `pd.to_datetime(..., errors="coerce")`
- bit → mapeo {si/sí/true/1}→1 y {no/false/0}→0
- texto → `string` + truncado a `CHARACTER_MAXIMUM_LENGTH`

Validación:
- si una columna es `IS_NULLABLE=NO` y había dato “no vacío” pero quedó NULL por conversión, el pipeline falla (modo estricto).

## Recomendaciones

- Usa `SQL_TRUSTED=yes` si estás en red corporativa/AD (Windows).
- Si usas usuario/clave: `SQL_TRUSTED=no` y setea `SQL_USER`/`SQL_PASSWORD`.
- Mantén `.env` fuera del repo.
