from __future__ import annotations

import os
from dataclasses import dataclass
from sqlalchemy import create_engine


@dataclass
class MSSQLConfig:
    server: str
    database: str
    user: str
    password: str
    schema: str = "COE"
    driver: str = "ODBC Driver 17 for SQL Server"


def load_mssql_config_from_env() -> MSSQLConfig:
    return MSSQLConfig(
        server=os.environ.get("SQL_SERVER", ""),
        database=os.environ.get("SQL_DB", ""),
        user=os.environ.get("SQL_USER", ""),
        password=os.environ.get("SQL_PASSWORD", ""),
        schema=os.environ.get("SQL_SCHEMA", "COE"),
        driver=os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server"),
    )


def make_engine(cfg: MSSQLConfig):
    if not all([cfg.server, cfg.database, cfg.user, cfg.password]):
        raise ValueError("Faltan variables de entorno SQL_SERVER / SQL_DB / SQL_USER / SQL_PASSWORD")

    from urllib.parse import quote_plus
    driver_q = quote_plus(cfg.driver)
    user_q = quote_plus(cfg.user)
    pass_q = quote_plus(cfg.password)

    url = f"mssql+pyodbc://{user_q}:{pass_q}@{cfg.server}/{cfg.database}?driver={driver_q}"
    return create_engine(url, pool_pre_ping=True)
