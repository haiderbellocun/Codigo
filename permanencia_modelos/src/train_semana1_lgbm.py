# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from permanencia.tabular.preprocessing import make_preprocessor
from permanencia.tabular.metrics import classification_metrics

load_dotenv()


def read_feature_list(path: str) -> list[str]:
    p = Path(path)
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Modelo Semana 1 (LightGBM) + export de SHAP (opcional).")
    parser.add_argument("--data", default=os.environ.get("DATA_PATH", "data/df_final.csv"))
    parser.add_argument("--target", default=os.environ.get("TARGET_COL", "Deserto"))
    parser.add_argument("--features", default=os.environ.get("FEATURES_FILE", "templates/features_default.txt"))
    parser.add_argument("--test-size", type=float, default=float(os.environ.get("TEST_SIZE", "0.2")))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("RANDOM_STATE", "42")))
    parser.add_argument("--out-dir", default=os.environ.get("MODEL_DIR", "outputs/models"))
    parser.add_argument("--export-shap", action="store_true", help="Genera SHAP para una muestra del test.")
    parser.add_argument("--shap-sample", type=int, default=int(os.environ.get("SHAP_SAMPLE", "500")))
    args = parser.parse_args()

    try:
        from lightgbm import LGBMClassifier
    except Exception as e:
        raise ImportError("lightgbm no está instalado. Instala requirements.txt") from e

    df = pd.read_csv(args.data)
    feature_cols = read_feature_list(args.features)

    missing = [c for c in feature_cols + [args.target] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing[:20]}{'...' if len(missing)>20 else ''}")

    X = df[feature_cols].copy()
    y = df[args.target].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    pre, num_cols, cat_cols = make_preprocessor(df, feature_cols)

    model = LGBMClassifier(
        n_estimators=2000,
        learning_rate=0.03,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=args.seed,
        n_jobs=-1,
    )

    pipe = Pipeline(steps=[("pre", pre), ("model", model)])
    pipe.fit(X_train, y_train)

    y_prob = pipe.predict_proba(X_test)[:, 1]
    metrics = classification_metrics(y_test, y_prob, threshold=float(os.environ.get("THRESHOLD", "0.5")))
    metrics.update({"model": "semana1_lightgbm", "num_cols": num_cols, "cat_cols": cat_cols})

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = {"pipeline": pipe, "feature_cols": feature_cols, "target": args.target}
    model_path = out_dir / "model_semana1_lightgbm.joblib"
    joblib.dump(bundle, model_path)

    report_dir = Path(os.environ.get("REPORT_DIR", "outputs/reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report_semana1_lightgbm.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Modelo guardado: {model_path}")

    if args.export_shap:
        try:
            import shap
        except Exception as e:
            raise ImportError("shap no está instalado. Instala requirements.txt") from e

        # sample
        sample_n = min(args.shap_sample, len(X_test))
        Xs = X_test.sample(sample_n, random_state=args.seed)
        # obtener matriz ya transformada
        Xs_trans = pipe.named_steps["pre"].transform(Xs)
        explainer = shap.TreeExplainer(pipe.named_steps["model"])
        shap_values = explainer.shap_values(Xs_trans)

        # shap_values puede ser list en clasif binaria
        if isinstance(shap_values, list):
            shap_mat = shap_values[1]
        else:
            shap_mat = shap_values

        # nombres de columnas después del preprocessor
        cols = num_cols + cat_cols
        df_shap = pd.DataFrame(shap_mat, columns=cols).round(4)
        df_shap["prob_desercion"] = pipe.predict_proba(Xs)[:, 1].round(4)

        out_csv = report_dir / "shap_semana1_lightgbm_sample.csv"
        df_shap.to_csv(out_csv, index=False, encoding="utf-8")
        print(f"📄 SHAP sample: {out_csv}")


if __name__ == "__main__":
    main()
