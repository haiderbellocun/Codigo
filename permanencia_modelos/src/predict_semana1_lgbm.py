# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Predicción (Semana 1 LightGBM).")
    parser.add_argument("--model-path", default=os.environ.get("SEMANA1_MODEL_PATH", "outputs/models/model_semana1_lightgbm.joblib"))
    parser.add_argument("--data", default=os.environ.get("PREDICT_DATA_PATH", "data/estudiantes_nuevos.csv"))
    parser.add_argument("--out", default=os.environ.get("PREDICT_OUT", "outputs/pred_semana1.csv"))
    args = parser.parse_args()

    bundle = joblib.load(args.model_path)
    pipe = bundle["pipeline"]
    feature_cols = bundle["feature_cols"]

    df = pd.read_csv(args.data)
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing[:20]}{'...' if len(missing)>20 else ''}")

    X = df[feature_cols].copy()
    prob = pipe.predict_proba(X)[:, 1]

    out_df = df.copy()
    out_df["prob_desercion"] = prob
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False, encoding="utf-8")

    print(f"✅ Guardado: {out_path}")


if __name__ == "__main__":
    main()
