# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ID_COL = os.environ.get("ID_COL", "Identificacion")
TARGET_COL = os.environ.get("TARGET_COL", "DescRF_Status")

VARS_SEM_1 = [l.strip() for l in Path(os.environ.get("VARS_SEM_1", "templates/vars_sem_1.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_3 = [l.strip() for l in Path(os.environ.get("ADD_SEM_3", "templates/vars_sem_3_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_8 = [l.strip() for l in Path(os.environ.get("ADD_SEM_8", "templates/vars_sem_8_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]
ADD_SEM_12 = [l.strip() for l in Path(os.environ.get("ADD_SEM_12", "templates/vars_sem_12_add.txt")).read_text(encoding="utf-8").splitlines() if l.strip()]


def vars_disponibles(semana: int) -> list[str]:
    v = list(VARS_SEM_1)
    if semana >= 3:
        v += ADD_SEM_3
    if semana >= 8:
        v += ADD_SEM_8
    if semana >= 12:
        v += ADD_SEM_12
    return sorted(set(v))


def sanitize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.astype(str).str.replace(" ", "_", regex=False)
    df.columns = df.columns.str.replace(r"[^A-Za-z0-9_]+", "", regex=True)
    return df


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Genera datasets tabulares por semana (1/3/8/12) para el modelo semanal.")
    parser.add_argument("--base", default=os.environ.get("BASE_IN", "outputs/base_modelo.csv.gz"))
    parser.add_argument("--out-dir", default=os.environ.get("WEEKLY_OUT_DIR", "outputs"))
    parser.add_argument("--weeks", default=os.environ.get("WEEKS", "1,3,8,12"))
    args = parser.parse_args()

    base = Path(args.base)
    if not base.exists():
        raise FileNotFoundError(f"No encuentro base: {base}")

    df = pd.read_csv(base)
    for col in [ID_COL, TARGET_COL]:
        if col not in df.columns:
            raise ValueError(f"Falta columna obligatoria: {col}")

    weeks = [int(x.strip()) for x in args.weeks.split(",") if x.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for w in weeks:
        v = [c for c in vars_disponibles(w) if c in df.columns]
        df_w = df[[ID_COL, TARGET_COL] + v].copy()

        cat = df_w[v].select_dtypes(include=["object", "category"]).columns.tolist()
        df_w_enc = pd.get_dummies(df_w, columns=cat, dummy_na=True)
        df_w_enc = sanitize_cols(df_w_enc)

        out = out_dir / f"dataset_semana_{w}.csv.gz"
        df_w_enc.to_csv(out, index=False, compression="gzip", encoding="utf-8")
        print(f"✅ Semana {w}: {out} | shape={df_w_enc.shape}")


if __name__ == "__main__":
    main()
