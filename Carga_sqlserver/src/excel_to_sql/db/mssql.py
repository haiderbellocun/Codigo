from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event


@dataclass
class MSSQLConfig:
    server: str
    database: str
    driver: str = "ODBC Driver 17 for SQL Server"
    trusted_connection: bool = True
    user: str | None = None
    password: str | None = None


def load_config_from_env() -> MSSQLConfig:
    trusted = os.environ.get("SQL_TRUSTED", "yes").strip().lower() in {"1","true","yes","y"}
    return MSSQLConfig(
        server=os.environ.get("SQL_SERVER", ""),
        database=os.environ.get("SQL_DB", ""),
        driver=os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server"),
        trusted_connection=trusted,
        user=os.environ.get("SQL_USER") or None,
        password=os.environ.get("SQL_PASSWORD") or None,
    )


def make_engine(cfg: MSSQLConfig):
    if not cfg.server or not cfg.database:
        raise ValueError("Faltan SQL_SERVER y/o SQL_DB en el .env")

    if cfg.trusted_connection:
        params = quote_plus(
            f"DRIVER={{{cfg.driver}}};"
            f"SERVER={cfg.server};"
            f"DATABASE={cfg.database};"
            f"Trusted_Connection=yes;"
        )
    else:
        if not cfg.user or not cfg.password:
            raise ValueError("Si SQL_TRUSTED=no, debes setear SQL_USER y SQL_PASSWORD")
        params = quote_plus(
            f"DRIVER={{{cfg.driver}}};"
            f"SERVER={cfg.server};"
            f"DATABASE={cfg.database};"
            f"UID={cfg.user};"
            f"PWD={cfg.password};"
            f"TrustServerCertificate=yes;"
        )

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", pool_pre_ping=True)

    # Acelera inserts (pyodbc)
    @event.listens_for(engine, "before_cursor_execute")
    def _set_fast_executemany(conn, cursor, statement, parameters, context, executemany):
        if executemany:
            try:
                cursor.fast_executemany = True
            except Exception:
                pass

    return engine
