# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

load_dotenv()


def read_feature_list(path: str) -> list[str]:
    p = Path(path)
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]


def build_sequences(df: pd.DataFrame, id_col: str, time_col: str, feature_cols: list[str], target_col: str):
    # ordena por tiempo y arma tensor (n_estudiantes, n_steps, n_features)
    ids = df[id_col].astype(str).unique().tolist()
    # determinar steps globales
    steps = sorted(df[time_col].dropna().unique().tolist())
    step_to_idx = {s:i for i,s in enumerate(steps)}
    n_steps = len(steps)
    n_features = len(feature_cols)

    X = np.full((len(ids), n_steps, n_features), np.nan, dtype=np.float32)
    y = np.zeros((len(ids),), dtype=np.int64)

    for i, sid in enumerate(ids):
        temp = df[df[id_col].astype(str) == sid].sort_values(time_col)
        # target final (última semana disponible del estudiante)
        y[i] = int(temp[target_col].iloc[-1])
        for _, row in temp.iterrows():
            s = row[time_col]
            if s not in step_to_idx:
                continue
            t = step_to_idx[s]
            X[i, t, :] = row[feature_cols].astype(float).values

    return X, y, steps


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Entrena un GRU (TensorFlow/Keras) para permanencia (secuencial por semana).")
    parser.add_argument("--data", default=os.environ.get("SEQ_DATA_PATH", "data/df_secuencial.csv"))
    parser.add_argument("--id-col", default=os.environ.get("SEQ_ID_COL", "estudiante_id"))
    parser.add_argument("--time-col", default=os.environ.get("SEQ_TIME_COL", "semana"))
    parser.add_argument("--target", default=os.environ.get("SEQ_TARGET_COL", "deserto"))
    parser.add_argument("--features", default=os.environ.get("FEATURES_FILE", "templates/features_default.txt"))
    parser.add_argument("--test-size", type=float, default=float(os.environ.get("TEST_SIZE", "0.2")))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("RANDOM_STATE", "42")))
    parser.add_argument("--epochs", type=int, default=int(os.environ.get("EPOCHS", "20")))
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("BATCH_SIZE", "32")))
    parser.add_argument("--out-dir", default=os.environ.get("MODEL_DIR", "outputs/models"))
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    feature_cols = read_feature_list(args.features)
    # en secuencial, muchas features pueden ser categóricas; se recomienda convertir antes.
    # aquí intentamos convertir a numérico, dejando NaN si no se puede.
    for c in feature_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    required = [args.id_col, args.time_col, args.target] + [c for c in feature_cols if c in df.columns]
    missing = [c for c in [args.id_col, args.time_col, args.target] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")

    X, y, steps = build_sequences(df, args.id_col, args.time_col, feature_cols, args.target)

    # escala por feature (flatten time)
    n, t, f = X.shape
    scaler = StandardScaler()
    X2 = X.reshape(-1, f)
    X2_scaled = scaler.fit_transform(np.nan_to_num(X2, nan=0.0))
    X_scaled = X2_scaled.reshape(n, t, f)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=args.test_size, random_state=args.seed, stratify=y)

    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import GRU, Dense, Dropout, Masking
    from tensorflow.keras.optimizers import Adam
    from sklearn.metrics import roc_auc_score

    model = Sequential()
    model.add(Masking(mask_value=0.0, input_shape=(X_train.shape[1], X_train.shape[2])))
    model.add(GRU(units=64, return_sequences=False))
    model.add(Dropout(0.3))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(1, activation="sigmoid"))

    model.compile(optimizer=Adam(learning_rate=1e-3), loss="binary_crossentropy", metrics=["accuracy"])
    history = model.fit(X_train, y_train, epochs=args.epochs, batch_size=args.batch_size, validation_split=0.1, verbose=1)

    y_prob = model.predict(X_test).ravel()
    auc = float(roc_auc_score(y_test, y_prob))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "gru_model.keras"
    model.save(model_path)

    # guardar scaler + metadata
    import joblib
    joblib.dump({"scaler": scaler, "feature_cols": feature_cols, "steps": steps, "id_col": args.id_col, "time_col": args.time_col, "target": args.target}, out_dir / "gru_bundle.joblib")

    report_dir = Path(os.environ.get("REPORT_DIR", "outputs/reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {"model": "gru", "roc_auc": auc, "n_train": int(len(y_train)), "n_test": int(len(y_test)), "steps": steps, "features": feature_cols}
    (report_dir / "report_gru.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ GRU guardado: {model_path}")
    print(f"📄 AUC: {auc:.4f}")


if __name__ == "__main__":
    main()
