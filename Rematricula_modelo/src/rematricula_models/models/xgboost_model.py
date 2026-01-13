from __future__ import annotations

import os
import numpy as np
import pandas as pd
from xgboost import XGBClassifier


def build_xgb(y_train: np.ndarray, prefer_gpu: bool = True) -> XGBClassifier:
    y_train = np.asarray(y_train).astype(int)
    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    spw = max(neg / max(pos, 1), 1.0)

    n_jobs = max((os.cpu_count() or 8) - 2, 4)

    params = dict(
        n_estimators=1200,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=4,
        reg_lambda=1.2,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=spw,
        n_jobs=n_jobs,
    )

    if prefer_gpu:
        # si no hay GPU/driver CUDA, xgboost lanzará error; el script hace fallback a CPU.
        params.update(dict(tree_method="gpu_hist", predictor="gpu_predictor", gpu_id=0))
    else:
        params.update(dict(tree_method="hist"))

    return XGBClassifier(**params)
