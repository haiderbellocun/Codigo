# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from db.mssql import load_mssql_config_from_env, make_engine

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extrae la base del modelo (MSSQL) a CSV comprimido.")
    parser.add_argument("--sql", default=os.environ.get("SQL_QUERY_FILE", "sql/base_modelo_query.sql"),
                        help="Archivo .sql con la consulta de extracción.")
    parser.add_argument("--out", default=os.environ.get("BASE_OUT", "outputs/base_modelo.csv.gz"),
                        help="Ruta salida CSV gzip.")
    args = parser.parse_args()

    sql_path = Path(args.sql)
    if not sql_path.exists():
        raise FileNotFoundError(f"No encuentro el SQL: {sql_path}")

    query = sql_path.read_text(encoding="utf-8")
    cfg = load_mssql_config_from_env()
    engine = make_engine(cfg)

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, compression="gzip", encoding="utf-8")
    print(f"✅ Extraído: {out_path} | filas={len(df):,} cols={df.shape[1]:,}")


if __name__ == "__main__":
    main()
