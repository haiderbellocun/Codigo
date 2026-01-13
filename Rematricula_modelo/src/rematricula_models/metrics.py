from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss


def base_metrics(y_true, y_prob) -> Dict[str, float]:
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "avg_precision": float(average_precision_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "positives": int(y_true.sum()),
        "n": int(len(y_true)),
        "base_rate": float(y_true.mean()) if len(y_true) else float("nan"),
        "expected": float(y_prob.sum()),
    }


def kpi_block(df: pd.DataFrame, proba_col: str = "y_proba") -> pd.Series:
    p = df[proba_col].clip(0, 1)
    N = int(len(p))
    C = float(p.sum())
    var = float((p * (1 - p)).sum())
    se = var ** 0.5
    return pd.Series({
        "N": N,
        "Esperados": C,
        "IC95_inf": C - 1.96 * se,
        "IC95_sup": C + 1.96 * se,
        "Tasa_Esp": C / N if N else np.nan,
        "Tasa_IC95_inf": (C - 1.96 * se) / N if N else np.nan,
        "Tasa_IC95_sup": (C + 1.96 * se) / N if N else np.nan,
    })


def tabla_control(df: pd.DataFrame, seg: str, y_col: str = "y", proba_col: str = "y_proba") -> pd.DataFrame:
    tmp = df.copy()
    tmp["Esperados"] = tmp[proba_col].clip(0,1)
    g = tmp.groupby(seg, dropna=False).agg(
        N=(y_col, "size"),
        Esperados=("Esperados", "sum"),
        Reales=(y_col, "sum"),
    ).reset_index()
    g["Error"] = g["Esperados"] - g["Reales"]
    g["AbsErr"] = g["Error"].abs()
    return g.sort_values("AbsErr", ascending=False)
