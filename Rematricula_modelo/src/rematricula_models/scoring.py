from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


def threshold_for_topM(p: np.ndarray, topM: int) -> float:
    p = np.asarray(p, dtype=float)
    if topM <= 0 or topM >= len(p):
        return float(np.min(p))
    return float(np.partition(p, -topM)[-topM])


@dataclass
class ScoringConfig:
    topM: int = 250  # capacidad de gestión
    proba_col: str = "y_proba"
    flag_col: str = "gestionar"


def apply_topM_flag(df: pd.DataFrame, cfg: ScoringConfig) -> pd.DataFrame:
    out = df.copy()
    thr = threshold_for_topM(out[cfg.proba_col].values, cfg.topM)
    out[cfg.flag_col] = (out[cfg.proba_col].values >= thr).astype(int)
    out["thr_topM"] = thr
    return out
