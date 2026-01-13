# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from rematricula_models.scoring import apply_topM_flag, ScoringConfig

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Predice rematrícula usando artefacto .joblib entrenado.")
    parser.add_argument("--model-path", default=os.environ.get("MODEL_PATH", "outputs/models/rematricula_xgb.joblib"))
    parser.add_argument("--data", default=os.environ.get("PREDICT_DATA_PATH", "data/nuevos.csv"))
    parser.add_argument("--out", default=os.environ.get("PREDICT_OUT", "outputs/reports/predicciones.csv"))
    parser.add_argument("--topM", type=int, default=int(os.environ.get("TOPM", "250")))
    args = parser.parse_args()

    bundle = joblib.load(args.model_path)
    pipe = bundle["pipeline"]
    platt = bundle["platt"]
    s = float(bundle.get("count_scalar", 1.0))
    feature_cols = bundle["feature_cols"]

    df = pd.read_csv(args.data)
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas para predecir: {missing[:20]}{'...' if len(missing)>20 else ''}")

    X = df[feature_cols].copy()
    p_raw = pipe.predict_proba(X)[:, 1]
    p_cal = platt.predict(p_raw)
    p_adj = np.clip(p_cal * s, 0, 1)

    out_df = df.copy()
    out_df["p_raw"] = p_raw
    out_df["p_cal"] = p_cal
    out_df["y_proba"] = p_adj

    out_df = apply_topM_flag(out_df, ScoringConfig(topM=args.topM, proba_col="y_proba", flag_col="gestionar"))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"✅ Predicciones guardadas: {out_path}")


if __name__ == "__main__":
    main()
