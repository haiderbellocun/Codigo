from __future__ import annotations

from typing import Callable, Dict

from .xgboost_model import build_xgb

MODEL_REGISTRY: Dict[str, Callable] = {
    "xgboost": build_xgb,
    "xgb": build_xgb,
}
