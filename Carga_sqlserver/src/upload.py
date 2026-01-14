# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dotenv import load_dotenv

from excel_to_sql.db.mssql import load_config_from_env, make_engine
from excel_to_sql.schema import fetch_table_schema
from excel_to_sql.io import load_excel
from excel_to_sql.convert import convert_dataframe_to_sql_schema
from excel_to_sql.load import upload_dataframe

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Carga masiva Excel → SQL Server usando staging table.")
    parser.add_argument("--input", default=os.environ.get("INPUT_EXCEL", "data/subida.xlsx"), help="Ruta del Excel.")
    parser.add_argument("--sheet", default=os.environ.get("INPUT_SHEET", "Sheet1"), help="Hoja del Excel.")
    parser.add_argument("--schema", default=os.environ.get("DEST_SCHEMA", "COE"), help="Schema destino.")
    parser.add_argument("--table", default=os.environ.get("DEST_TABLE", "CLTIENE_LLAMADAS"), help="Tabla destino.")
    parser.add_argument("--chunksize", type=int, default=int(os.environ.get("CHUNKSIZE", "1000")), help="Batch size.")
    parser.add_argument("--truncate-destination", action="store_true", help="TRUNCATE antes de insertar (PELIGROSO).")
    parser.add_argument("--no-strict", action="store_true", help="No falla si una conversión produce NULL en NOT NULL.")
    args = parser.parse_args()

    cfg = load_config_from_env()
    engine = make_engine(cfg)

    df = load_excel(args.input, sheet=args.sheet)
    print(f"📄 Excel cargado: shape={df.shape}")

    schema_df = fetch_table_schema(engine, args.schema, args.table)
    print(f"🧱 Esquema SQL leído: {len(schema_df)} columnas")

    df_conv = convert_dataframe_to_sql_schema(df, schema_df, strict=not args.no_strict)
    print("✅ Tipos convertidos/validados contra SQL Server")

    result = upload_dataframe(
        engine,
        df_conv,
        schema=args.schema,
        table=args.table,
        chunksize=args.chunksize,
        truncate_destination=args.truncate_destination,
    )

    print(f"✅ Insertados: {result.rows_inserted:,} | temp={result.temp_table}")


if __name__ == "__main__":
    main()
