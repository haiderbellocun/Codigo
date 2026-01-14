from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
from sqlalchemy import text


@dataclass
class UploadResult:
    rows_excel: int
    rows_inserted: int
    temp_table: str


def bracket(name: str) -> str:
    return f"[{name.replace(']', '')}]"


def fq(schema: str, table: str) -> str:
    return f"{bracket(schema)}.{bracket(table)}"


def create_staging_like_destination(conn, schema: str, table: str, staging_table: str):
    dest = fq(schema, table)
    stg = fq(schema, staging_table)

    # Drop staging if exists, then clone structure
    conn.execute(text(f"""IF OBJECT_ID(N'{schema}.{staging_table}', N'U') IS NOT NULL
    DROP TABLE {stg};
SELECT TOP 0 *
INTO {stg}
FROM {dest};
"""))


def upload_dataframe(
    engine,
    df: pd.DataFrame,
    *,
    schema: str,
    table: str,
    staging_suffix: str = "_TEMP_CARGA",
    chunksize: int = 1000,
    truncate_destination: bool = False,
) -> UploadResult:
    staging_table = f"{table}{staging_suffix}"
    dest_full = fq(schema, table)
    stg_full = fq(schema, staging_table)

    with engine.begin() as conn:
        create_staging_like_destination(conn, schema, table, staging_table)

        # Cargar a staging
        df.to_sql(
            name=staging_table,
            con=conn,
            schema=schema,
            if_exists="append",
            index=False,
            chunksize=chunksize,
            method=None,  # evita límite 2100 parámetros de method="multi"
        )

        # (Opcional) truncar destino antes de insertar
        if truncate_destination:
            conn.execute(text(f"TRUNCATE TABLE {dest_full};"))

        cols = [bracket(c) for c in df.columns.tolist()]
        cols_sql = ", ".join(cols)

        # Insertar al destino
        conn.execute(text(f"""INSERT INTO {dest_full} ({cols_sql})
SELECT {cols_sql}
FROM {stg_full};
"""))

        # Conteo insertado (desde staging)
        rows_inserted = conn.execute(text(f"SELECT COUNT(1) FROM {stg_full};")).scalar() or 0

        # Borrar staging
        conn.execute(text(f"DROP TABLE {stg_full};"))

    return UploadResult(rows_excel=len(df), rows_inserted=int(rows_inserted), temp_table=f"{schema}.{staging_table}")
