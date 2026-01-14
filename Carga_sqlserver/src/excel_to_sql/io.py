from __future__ import annotations

from pathlib import Path
import pandas as pd


def load_excel(path: str, sheet: str = "Sheet1") -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe el archivo: {p}")
    return pd.read_excel(p, sheet_name=sheet)
