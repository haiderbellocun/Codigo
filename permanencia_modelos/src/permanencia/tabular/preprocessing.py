from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


@dataclass
class TabularSchema:
    target_col: str = "Deserto"
    id_col: Optional[str] = "DescRF_Identificacion"


def infer_categorical_columns(df: pd.DataFrame, feature_cols: List[str]) -> List[str]:
    cats = []
    for c in feature_cols:
        if c not in df.columns:
            continue
        if df[c].dtype == "object" or str(df[c].dtype).startswith("category"):
            cats.append(c)
    return cats


def make_preprocessor(df: pd.DataFrame, feature_cols: List[str]) -> Tuple[ColumnTransformer, List[str], List[str]]:
    # Categóricas: ordinal (robusto para árboles); numéricas: imputación mediana
    cat_cols = infer_categorical_columns(df, feature_cols)
    num_cols = [c for c in feature_cols if c not in cat_cols]

    cat_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])

    num_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
    ])

    pre = ColumnTransformer(
        transformers=[
            ("num", num_pipe, num_cols),
            ("cat", cat_pipe, cat_cols),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )
    return pre, num_cols, cat_cols
