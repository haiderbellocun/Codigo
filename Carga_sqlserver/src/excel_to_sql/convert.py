from __future__ import annotations

import pandas as pd


def _map_bit(x):
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    if s in {"1","true","t","si","sí","s","y","yes"}:
        return 1
    if s in {"0","false","f","no","n"}:
        return 0
    return None


def convert_dataframe_to_sql_schema(df_in: pd.DataFrame, schema_df: pd.DataFrame, *, strict: bool = True) -> pd.DataFrame:
    """
    Convierte df_in a los tipos que espera SQL Server según INFORMATION_SCHEMA.COLUMNS.

    - Normaliza nombres de columnas (case-insensitive) contra COLUMN_NAME.
    - Elimina columnas extra que no estén en la tabla.
    - Valida no-nullables: si había valor y quedó NULL por conversión, falla si strict=True.
    """

    # 1) Normalizar nombres (case-insensitive)
    sql_cols = schema_df["COLUMN_NAME"].tolist()
    sql_map = {c.lower(): c for c in sql_cols}
    in_cols = list(df_in.columns)

    rename = {}
    for c in in_cols:
        key = str(c).strip().lower()
        if key in sql_map:
            rename[c] = sql_map[key]

    df = df_in.rename(columns=rename).copy()

    # faltantes / sobrantes
    faltantes = set(sql_cols) - set(df.columns)
    sobrantes = set(df.columns) - set(sql_cols)

    if faltantes:
        raise ValueError(f"El Excel/DF NO tiene columnas requeridas por {faltantes}")

    if sobrantes:
        # se ignoran
        df = df.drop(columns=list(sobrantes))

    # 2) Conversión por tipo
    errores = []
    out = df.copy()

    for _, row in schema_df.iterrows():
        col = row["COLUMN_NAME"]
        tipo = str(row["DATA_TYPE"]).lower()
        max_len = row.get("CHARACTER_MAXIMUM_LENGTH")
        is_nullable = row.get("IS_NULLABLE", "YES")

        serie = out[col]

        try:
            if tipo in ("int","bigint","smallint","tinyint"):
                serie_new = pd.to_numeric(serie, errors="coerce").astype("Int64")

            elif tipo in ("decimal","numeric","float","real","money","smallmoney"):
                serie_new = pd.to_numeric(serie, errors="coerce")

            elif tipo in ("date","datetime","datetime2","smalldatetime","datetimeoffset","time"):
                serie_new = pd.to_datetime(serie, errors="coerce")

            elif tipo == "bit":
                serie_new = serie.map(_map_bit).astype("Int64")

            else:
                # texto / otros
                serie_new = serie.astype("string")
                if pd.notna(max_len) and max_len is not None and int(max_len) > 0:
                    serie_new = serie_new.str.slice(0, int(max_len))

            # Validación no-null (si existía valor "real" y quedó nulo)
            if strict and str(is_nullable).upper() == "NO":
                mask_in = serie.notna() & (serie.astype(str).str.strip() != "")
                mask_out_null = serie_new.isna()
                if (mask_in & mask_out_null).any():
                    n = int((mask_in & mask_out_null).sum())
                    errores.append(f"Columna '{col}' ({tipo}) tiene {n} valores no convertibles y NO admite NULL.")

            out[col] = serie_new

        except Exception as e:
            errores.append(f"Error convirtiendo '{col}' ({tipo}): {e}")

    if errores:
        msg = "Errores de conversión:\n- " + "\n- ".join(errores)
        raise ValueError(msg)

    # ordenar columnas como en SQL
    out = out[sql_cols]
    return out
