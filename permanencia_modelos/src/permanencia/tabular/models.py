from __future__ import annotations

from typing import Any, Dict

from sklearn.ensemble import RandomForestClassifier

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover
    CatBoostClassifier = None  # type: ignore

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None  # type: ignore

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None  # type: ignore


def build_model(name: str, params: Dict[str, Any] | None = None):
    params = params or {}
    name = name.lower()

    if name in {"random_forest", "rf"}:
        return RandomForestClassifier(
            n_estimators=int(params.get("n_estimators", 500)),
            max_depth=params.get("max_depth", None),
            random_state=int(params.get("random_state", 42)),
            n_jobs=-1,
        )

    if name in {"catboost", "cb"}:
        if CatBoostClassifier is None:
            raise ImportError("catboost no está instalado. Instala requirements.txt")
        return CatBoostClassifier(
            iterations=int(params.get("iterations", 800)),
            depth=int(params.get("depth", 8)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            loss_function="Logloss",
            eval_metric="AUC",
            verbose=False,
            random_seed=int(params.get("random_state", 42)),
        )

    if name in {"lightgbm", "lgbm"}:
        if LGBMClassifier is None:
            raise ImportError("lightgbm no está instalado. Instala requirements.txt")
        return LGBMClassifier(
            n_estimators=int(params.get("n_estimators", 2000)),
            learning_rate=float(params.get("learning_rate", 0.03)),
            num_leaves=int(params.get("num_leaves", 63)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            random_state=int(params.get("random_state", 42)),
            n_jobs=-1,
        )

    if name in {"xgboost", "xgb"}:
        if XGBClassifier is None:
            raise ImportError("xgboost no está instalado. Instala requirements.txt")
        return XGBClassifier(
            n_estimators=int(params.get("n_estimators", 1500)),
            learning_rate=float(params.get("learning_rate", 0.03)),
            max_depth=int(params.get("max_depth", 6)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            reg_lambda=float(params.get("reg_lambda", 1.0)),
            random_state=int(params.get("random_state", 42)),
            n_jobs=-1,
            eval_metric="logloss",
        )

    raise ValueError(f"Modelo no soportado: {name}")
