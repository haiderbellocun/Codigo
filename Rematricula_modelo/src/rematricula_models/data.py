from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


@dataclass
class DataConfig:
    # Columnas clave (según notebook)
    col_id: str = "num_identificacion"
    col_periodo: str = "COD_PERIODO"
    col_periodo_paga: str = "Periodo_Paga"
    col_estado_actual: str = "ESTADOACTUAL"
    col_target: str = "y_rematricula"
    col_periodo_orden: str = "periodo_orden"
    seg_programa: str = "Programa"
    seg_sede: str = "sede"

    # Periodos: ajusta si aparecen nuevos
    periodo_orden: Tuple[str, ...] = (
        "23V04","2023B","23V05","23V06",
        "24V01","2024A","24V02","24V03","24P02","24V04","2024B","24V05","24V06",
        "25V02","2025B","25V05","2025D"
    )


def norm_periodo(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.strip()


def make_period_map(cfg: DataConfig) -> Dict[str, int]:
    return {p.upper(): i for i, p in enumerate(cfg.periodo_orden, start=1)}


def compute_label_row(row: pd.Series, cfg: DataConfig, orden_map: Dict[str, int]) -> int:
    """Etiqueta 1 si:
    - ESTADOACTUAL == 'YA PAGO'
    - Periodo_Paga existe y es posterior a COD_PERIODO (según orden_map)
    """
    est = str(row.get(cfg.col_estado_actual, "")).upper()
    cp = row.get(cfg.col_periodo, None)
    pp = row.get(cfg.col_periodo_paga, None)
    if est == "YA PAGO":
        i_cp = orden_map.get(str(cp), None)
        i_pp = orden_map.get(str(pp), None)
        if i_cp is not None and i_pp is not None:
            return int(i_pp > i_cp)
    return 0


def build_engine_from_env() -> object:
    """Crea engine SQL Server usando variables de entorno.

    Soporta:
    - Autenticación integrada (Windows): TRUSTED_CONNECTION=yes
    - Usuario/clave: SQL_USER/SQL_PASSWORD
    """
    server = os.environ.get("SQL_SERVER", "")
    db = os.environ.get("SQL_DB", "")
    port = os.environ.get("SQL_PORT", "1433")
    driver = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    trusted = os.environ.get("SQL_TRUSTED_CONNECTION", "yes").lower() in {"1", "true", "yes", "y"}
    user = os.environ.get("SQL_USER", "")
    pwd = os.environ.get("SQL_PASSWORD", "")

    if not server or not db:
        raise ValueError("Faltan SQL_SERVER o SQL_DB en el entorno (.env).")

    if trusted:
        # mssql+pyodbc://@host:port/db?driver=...&trusted_connection=yes
        engine_url = (
            f"mssql+pyodbc://@{server}:{port}/{db}"
            f"?driver={driver.replace(' ', '+')}"
            f"&trusted_connection=yes&TrustServerCertificate=yes"
        )
        return create_engine(engine_url, fast_executemany=True)

    # user/password
    odbc = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
    )
    params = quote_plus(odbc)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)


def load_dataset(
    cfg: DataConfig,
    source: str,
    sql_path: Optional[str] = None,
) -> pd.DataFrame:
    """Carga dataset desde CSV o desde SQL (archivo .sql).
    - source='csv': usa DATA_PATH
    - source='sql': usa sql_path y credenciales del .env
    """
    if source == "csv":
        data_path = Path(os.environ.get("DATA_PATH", "data/df_rematricula.csv"))
        if not data_path.exists():
            raise FileNotFoundError(f"No existe {data_path}. Coloca tu CSV o ajusta DATA_PATH.")
        return pd.read_csv(data_path)

    if source == "sql":
        if not sql_path:
            sql_path = "sql/extract.sql"
        q = Path(sql_path).read_text(encoding="utf-8")
        if "SELECT" not in q.upper():
            raise ValueError("El archivo SQL parece vacío. Completa sql/extract.sql.")
        engine = build_engine_from_env()
        with engine.connect() as conn:
            return pd.read_sql(text(q), conn)

    raise ValueError("source debe ser 'csv' o 'sql'")


def add_label_and_period_order(df: pd.DataFrame, cfg: DataConfig) -> pd.DataFrame:
    orden_map = make_period_map(cfg)

    df = df.copy()
    df[cfg.col_periodo] = norm_periodo(df[cfg.col_periodo])
    if cfg.col_periodo_paga in df.columns:
        df[cfg.col_periodo_paga] = norm_periodo(df[cfg.col_periodo_paga])

    df[cfg.col_periodo_orden] = df[cfg.col_periodo].map(orden_map).astype("Int64")
    df = df[df[cfg.col_periodo_orden].notna()].copy()
    df[cfg.col_periodo_orden] = df[cfg.col_periodo_orden].astype(int)

    # si no existe target, lo crea
    if cfg.col_target not in df.columns:
        df[cfg.col_target] = df.apply(lambda r: compute_label_row(r, cfg, orden_map), axis=1).astype(int)

    return df


def time_split_last_period(df: pd.DataFrame, cfg: DataConfig) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Toma el último periodo (máximo periodo_orden) como validación."""
    v_max = int(df[cfg.col_periodo_orden].max())
    periodo_obj = df.loc[df[cfg.col_periodo_orden] == v_max, cfg.col_periodo].mode().iat[0]
    df_train = df[df[cfg.col_periodo_orden] < v_max].copy()
    df_valid = df[df[cfg.col_periodo_orden] == v_max].copy()
    return df_train, df_valid, str(periodo_obj)
