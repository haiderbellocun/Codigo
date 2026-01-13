# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from permanencia.tabular.models import build_model
from permanencia.tabular.preprocessing import make_preprocessor
from permanencia.tabular.metrics import classification_metrics

load_dotenv()


def read_feature_list(path: str) -> list[str]:
    p = Path(path)
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Entrena modelos tabulares de permanencia (CatBoost/LGBM/XGB/RF).")
    parser.add_argument("--data", default=os.environ.get("DATA_PATH", "data/df_final.csv"), help="CSV con dataset.")
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", "catboost"), help="catboost/lightgbm/xgboost/random_forest")
    parser.add_argument("--features", default=os.environ.get("FEATURES_FILE", "templates/features_default.txt"), help="Archivo con lista de features.")
    parser.add_argument("--target", default=os.environ.get("TARGET_COL", "Deserto"), help="Columna target (0/1).")
    parser.add_argument("--test-size", type=float, default=float(os.environ.get("TEST_SIZE", "0.2")), help="Proporción test.")
    parser.add_argument("--seed", type=int, default=int(os.environ.get("RANDOM_STATE", "42")), help="Random seed.")
    parser.add_argument("--out-dir", default=os.environ.get("MODEL_DIR", "outputs/models"), help="Carpeta salida de modelos.")
    parser.add_argument("--threshold", type=float, default=float(os.environ.get("THRESHOLD", "0.5")), help="Umbral para métricas.")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    feature_cols = read_feature_list(args.features)
    missing = [c for c in feature_cols + [args.target] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el dataset: {missing[:20]}{'...' if len(missing)>20 else ''}")

    X = df[feature_cols].copy()
    y = df[args.target].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    pre, num_cols, cat_cols = make_preprocessor(df, feature_cols)
    model = build_model(args.model, params={"random_state": args.seed})

    pipe = Pipeline(steps=[
        ("pre", pre),
        ("model", model),
    ])

    pipe.fit(X_train, y_train)

    # proba
    if hasattr(pipe, "predict_proba"):
        y_prob = pipe.predict_proba(X_test)[:, 1]
    else:
        # fallback
        y_prob = pipe.predict(X_test)

    metrics = classification_metrics(y_test, y_prob, threshold=args.threshold)
    metrics["model"] = args.model
    metrics["n_train"] = int(len(X_train))
    metrics["n_test"] = int(len(X_test))
    metrics["num_cols"] = num_cols
    metrics["cat_cols"] = cat_cols

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / f"model_{args.model}.joblib"
    joblib.dump({"pipeline": pipe, "feature_cols": feature_cols, "target": args.target}, model_path)

    report_dir = Path(os.environ.get("REPORT_DIR", "outputs/reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"report_{args.model}.json"
    report_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Modelo guardado: {model_path}")
    print(f"📄 Reporte: {report_path}")
    print(metrics)


if __name__ == "__main__":
    main()
