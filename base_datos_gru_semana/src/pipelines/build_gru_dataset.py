# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ID_COL = os.environ.get("ID_COL", "Identificacion")
TARGET_COL = os.environ.get("TARGET_COL", "DescRF_Status")
SEMANAS_TOTALES = int(os.environ.get("SEMANAS_TOTALES", "16"))

VARS_SEM_1 = [l.strip() for l in Path(os.environ.get("VARS_SEM_1", "templates/vars_sem_1.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_3 = [l.strip() for l in Path(os.environ.get("ADD_SEM_3", "templates/vars_sem_3_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_8 = [l.strip() for l in Path(os.environ.get("ADD_SEM_8", "templates/vars_sem_8_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_12 = [l.strip() for l in Path(os.environ.get("ADD_SEM_12", "templates/vars_sem_12_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]


def sanitize_cols(cols: pd.Index) -> pd.Index:
    c = cols.astype(str).str.replace(" ", "_", regex=False)
    c = c.str.replace(r"[^A-Za-z0-9_]+", "", regex=True)
    return c


def vars_disponibles_por_semana(semana: int) -> list[str]:
    v = list(VARS_SEM_1)
    if semana >= 3:
        v.extend(ADD_SEM_3)
    if semana >= 8:
        v.extend(ADD_SEM_8)
    if semana >= 12:
        v.extend(ADD_SEM_12)
    return sorted(set(v))


def encoded_cols_for_var(encoded_cols: list[str], var: str) -> list[str]:
    prefix = var + "_"
    return [c for c in encoded_cols if c == var or c.startswith(prefix)]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Construye dataset secuencial (long) para GRU.")
    parser.add_argument("--base", default=os.environ.get("BASE_IN", "outputs/base_modelo.csv.gz"),
                        help="CSV base (salida del extractor).")
    parser.add_argument("--out", default=os.environ.get("GRU_OUT", "outputs/datos_secuenciales_para_gru.csv.gz"),
                        help="Salida del dataset secuencial (gzip).")
    args = parser.parse_args()

    base_path = Path(args.base)
    if not base_path.exists():
        raise FileNotFoundError(f"No encuentro base: {base_path}")

    base_modelo = pd.read_csv(base_path)
    base_modelo = base_modelo.loc[:, ~base_modelo.columns.duplicated()]

    for col in [ID_COL, TARGET_COL]:
        if col not in base_modelo.columns:
            raise ValueError(f"Falta columna obligatoria: {col}")

    vars_max = vars_disponibles_por_semana(12)
    vars_max = [v for v in vars_max if v in base_modelo.columns]

    categoricas = base_modelo[vars_max].select_dtypes(include=["object", "category"]).columns.tolist()
    base_modelo_encoded = pd.get_dummies(base_modelo, columns=categoricas, dummy_na=True)

    base_modelo_encoded.columns = sanitize_cols(base_modelo_encoded.columns)
    base_modelo_encoded = base_modelo_encoded.loc[:, ~base_modelo_encoded.columns.duplicated()]

    encoded_cols = base_modelo_encoded.columns.tolist()
    feature_cols = [c for c in encoded_cols if c not in {ID_COL, TARGET_COL}]

    var_to_encoded = {}
    for v in vars_max:
        v_san = re.sub(r"[^A-Za-z0-9_]+", "", v.replace(" ", "_"))
        cols = set(encoded_cols_for_var(feature_cols, v))
        cols |= set(encoded_cols_for_var(feature_cols, v_san))
        var_to_encoded[v] = sorted(cols)

    frames = []
    for semana in range(1, SEMANAS_TOTALES + 1):
        vars_disp = [v for v in vars_disponibles_por_semana(semana) if v in var_to_encoded]
        cols_disp = set()
        for v in vars_disp:
            cols_disp.update(var_to_encoded[v])

        df_sem = pd.DataFrame({
            ID_COL: base_modelo_encoded[ID_COL].values,
            TARGET_COL: base_modelo_encoded[TARGET_COL].values,
            "semana": semana,
        })

        for c in feature_cols:
            df_sem[c] = base_modelo_encoded[c].values if c in cols_disp else np.nan

        frames.append(df_sem)

    df_secuencial = pd.concat(frames, ignore_index=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_secuencial.to_csv(out_path, index=False, compression="gzip", encoding="utf-8")
    print(f"✅ GRU dataset: {out_path} | shape={df_secuencial.shape}")


if __name__ == "__main__":
    main()
