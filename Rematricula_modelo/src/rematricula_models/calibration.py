from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression


def logit_clip(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


@dataclass
class PlattCalibrator:
    model: LogisticRegression

    def predict(self, p_raw: np.ndarray) -> np.ndarray:
        X = logit_clip(np.asarray(p_raw)).reshape(-1, 1)
        return self.model.predict_proba(X)[:, 1]


def fit_platt_from_oof(proba_oof: np.ndarray, y_true: np.ndarray) -> PlattCalibrator:
    X = logit_clip(np.asarray(proba_oof)).reshape(-1, 1)
    lr = LogisticRegression(solver="lbfgs")
    lr.fit(X, y_true.astype(int))
    return PlattCalibrator(model=lr)


def count_adjustment_scalar(y_true: np.ndarray, p_cal: np.ndarray, clip: Tuple[float, float] = (0.6, 1.4)) -> float:
    # s = reales / esperados
    y_sum = float(np.asarray(y_true).sum())
    p_sum = float(np.asarray(p_cal).sum())
    if p_sum <= 0:
        return 1.0
    s = y_sum / p_sum
    return float(np.clip(s, clip[0], clip[1]))


def apply_count_adjustment(p: np.ndarray, s: float) -> np.ndarray:
    return np.clip(np.asarray(p) * float(s), 0, 1)
