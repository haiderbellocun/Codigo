from __future__ import annotations

from typing import List, Tuple

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


def infer_feature_sets(df: pd.DataFrame, target: str, drops: List[str]) -> Tuple[List[str], List[str], List[str]]:
    drop_cols = set([target] + drops)
    feat = [c for c in df.columns if c not in drop_cols]
    num = [c for c in feat if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in feat if c not in num]
    return feat, num, cat


def make_preprocessor(num_cols: List[str], cat_cols: List[str]) -> ColumnTransformer:
    # compatibilidad sklearn: sparse_output (>=1.2) / sparse (older)
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:  # pragma: no cover
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=True)

    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", num_cols),
            ("cat", ohe, cat_cols),
        ]
    )
