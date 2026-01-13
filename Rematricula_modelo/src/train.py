# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline

from rematricula_models.data import DataConfig, add_label_and_period_order, load_dataset, time_split_last_period
from rematricula_models.preprocessing import infer_feature_sets, make_preprocessor
from rematricula_models.models import MODEL_REGISTRY
from rematricula_models.calibration import fit_platt_from_oof, count_adjustment_scalar
from rematricula_models.metrics import base_metrics, kpi_block, tabla_control

load_dotenv()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Entrena modelo de rematrícula (XGBoost + Platt OOF + ajuste de conteo).")
    parser.add_argument("--source", choices=["csv", "sql"], default=os.environ.get("SOURCE", "csv"))
    parser.add_argument("--sql", default=os.environ.get("SQL_FILE", "sql/extract.sql"))
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", "xgboost"), help="xgboost/xgb")
    parser.add_argument("--out-dir", default=os.environ.get("OUT_DIR", "outputs"))
    parser.add_argument("--topM", type=int, default=int(os.environ.get("TOPM", "250")))
    parser.add_argument("--ts-splits", type=int, default=int(os.environ.get("TS_SPLITS", "5")))
    parser.add_argument("--prefer-gpu", action="store_true", default=os.environ.get("PREFER_GPU", "1").lower() in {"1","true","yes","y"})
    args = parser.parse_args()

    cfg = DataConfig()
    df = load_dataset(cfg, source=args.source, sql_path=args.sql)
    df = add_label_and_period_order(df, cfg)

    # Split: último periodo como validación
    df_train, df_valid, periodo_obj = time_split_last_period(df, cfg)
    if df_train.empty or df_valid.empty:
        raise SystemExit("Split train/valid vacío. Revisa periodos o filtros.")

    # Features
    drop_extra = [cfg.col_id, cfg.col_periodo, cfg.col_periodo_paga, cfg.col_periodo_orden]
    feat_cols, num_cols, cat_cols = infer_feature_sets(df_train, cfg.col_target, drop_extra)

    pre = make_preprocessor(num_cols, cat_cols)

    # Ordena train por periodo_orden para TimeSeriesSplit
    df_train = df_train.sort_values([cfg.col_periodo_orden, cfg.col_id]).reset_index(drop=True)

    X_tr = df_train[feat_cols]
    y_tr = df_train[cfg.col_target].astype(int).to_numpy()

    X_va = df_valid[feat_cols]
    y_va = df_valid[cfg.col_target].astype(int).to_numpy()

    # Modelo (con fallback a CPU)
    builder = MODEL_REGISTRY.get(args.model.lower())
    if builder is None:
        raise ValueError(f"Modelo no soportado: {args.model}. Opciones: {list(MODEL_REGISTRY)}")

    def build_clf(y):
        return builder(y, prefer_gpu=args.prefer_gpu)

    pipe = Pipeline([("prep", pre), ("clf", build_clf(y_tr))])

    # OOF para Platt (TimeSeriesSplit)
    tscv = TimeSeriesSplit(n_splits=args.ts_splits)
    proba_oof = np.zeros(len(X_tr), dtype=float)

    for tr_idx, te_idx in tscv.split(X_tr, y_tr):
        pipe_fold = Pipeline([("prep", pre), ("clf", build_clf(y_tr[tr_idx]))])
        try:
            pipe_fold.fit(X_tr.iloc[tr_idx], y_tr[tr_idx])
        except Exception:
            # fallback a CPU si GPU falla
            pipe_fold = Pipeline([("prep", pre), ("clf", builder(y_tr[tr_idx], prefer_gpu=False))])
            pipe_fold.fit(X_tr.iloc[tr_idx], y_tr[tr_idx])

        proba_oof[te_idx] = pipe_fold.predict_proba(X_tr.iloc[te_idx])[:, 1]

    platt = fit_platt_from_oof(proba_oof, y_tr)

    # Entrena final
    try:
        pipe.fit(X_tr, y_tr)
    except Exception:
        pipe = Pipeline([("prep", pre), ("clf", builder(y_tr, prefer_gpu=False))])
        pipe.fit(X_tr, y_tr)

    proba_valid_raw = pipe.predict_proba(X_va)[:, 1]
    proba_valid_cal = platt.predict(proba_valid_raw)

    # Ajuste de conteo (scalar s)
    s = count_adjustment_scalar(y_va, proba_valid_cal, clip=(0.6, 1.4))
    proba_valid_adj = np.clip(proba_valid_cal * s, 0, 1)

    # Reportes
    metrics_raw = base_metrics(y_va, proba_valid_raw)
    metrics_cal = base_metrics(y_va, proba_valid_cal)
    metrics_adj = base_metrics(y_va, proba_valid_adj)

    out_dir = Path(args.out_dir)
    (out_dir / "models").mkdir(parents=True, exist_ok=True)
    (out_dir / "reports").mkdir(parents=True, exist_ok=True)

    bundle = {
        "pipeline": pipe,
        "platt": platt,
        "count_scalar": s,
        "feature_cols": feat_cols,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "periodo_obj": periodo_obj,
        "cfg": cfg,
    }
    model_path = out_dir / "models" / "rematricula_xgb.joblib"
    joblib.dump(bundle, model_path)

    # Scoring valid
    scoring = df_valid[[cfg.col_id, cfg.col_periodo, cfg.seg_programa, cfg.seg_sede]].copy()
    scoring["y"] = y_va
    scoring["p_raw"] = proba_valid_raw
    scoring["p_cal"] = proba_valid_cal
    scoring["y_proba"] = proba_valid_adj

    scoring_path = out_dir / "reports" / "scoring_valid.csv"
    scoring.to_csv(scoring_path, index=False, encoding="utf-8-sig")

    # Tabla control (errores por segmento)
    ctrl_prog = tabla_control(scoring, cfg.seg_programa, y_col="y", proba_col="y_proba")
    ctrl_sede = tabla_control(scoring, cfg.seg_sede, y_col="y", proba_col="y_proba")
    ctrl_prog.to_csv(out_dir / "reports" / "control_programa.csv", index=False, encoding="utf-8-sig")
    ctrl_sede.to_csv(out_dir / "reports" / "control_sede.csv", index=False, encoding="utf-8-sig")

    report = {
        "periodo_validacion": periodo_obj,
        "count_scalar_s": float(s),
        "metrics_raw": metrics_raw,
        "metrics_platt": metrics_cal,
        "metrics_adjusted": metrics_adj,
        "n_train": int(len(df_train)),
        "n_valid": int(len(df_valid)),
        "topM": int(args.topM),
    }
    (out_dir / "reports" / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Modelo guardado: {model_path}")
    print(f"📄 Scoring valid:  {scoring_path}")
    print(f"📄 Reporte:       {out_dir / 'reports' / 'report.json'}")


if __name__ == "__main__":
    main()
