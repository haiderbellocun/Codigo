from __future__ import annotations

import pandas as pd
from sqlalchemy import text


SCHEMA_QUERY = text("""
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = :schema
  AND TABLE_NAME   = :table
ORDER BY ORDINAL_POSITION;
""")


def fetch_table_schema(engine, schema: str, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(SCHEMA_QUERY, conn, params={"schema": schema, "table": table})
    if df.empty:
        raise ValueError(f"No encontré columnas para {schema}.{table}. ¿Existe la tabla y tienes permisos?")
    return df
