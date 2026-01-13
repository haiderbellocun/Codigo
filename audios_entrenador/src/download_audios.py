# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


def build_sql_connstr() -> str:
    driver   = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    trusted  = os.environ.get("SQL_TRUSTED", "true").lower() in {"1","true","yes","y"}
    server   = os.environ.get("SQL_SERVER", "")
    db       = os.environ.get("SQL_DB", "")
    user     = os.environ.get("SQL_USER", "")
    password = os.environ.get("SQL_PASSWORD", "")

    if not server or not db:
        raise ValueError("Faltan SQL_SERVER / SQL_DB en .env.")

    if trusted:
        return f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};Trusted_Connection=yes;"

    if not user or not password:
        raise ValueError("Faltan SQL_USER / SQL_PASSWORD o activa SQL_TRUSTED=true.")

    return f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};UID={user};PWD={password};Trusted_Connection=no;"


def fetch_meta_from_sql(meta_desde: Optional[str] = None, meta_hasta_exc: Optional[str] = None) -> pd.DataFrame:
    import pyodbc

    conn = pyodbc.connect(build_sql_connstr())

    where_parts = []
    if meta_desde:
        where_parts.append(f"started_at >= CONVERT(datetime2(7), '{meta_desde}T00:00:00', 126)")
    if meta_hasta_exc:
        where_parts.append(f"started_at <  CONVERT(datetime2(7), '{meta_hasta_exc}T00:00:00', 126)")
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    query = f"""
    SELECT
        call_id,
        number      AS numero_vapi,
        started_at  AS fecha,
        recording_url
    FROM dbo.vapi_entrenador
    {where_sql};
    """

    df = pd.read_sql(query, conn)
    conn.close()
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def guess_ext(url: str) -> str:
    m = re.search(r"\.([a-zA-Z0-9]{2,5})(?:\?|$)", url)
    return ("." + m.group(1).lower()) if m else ".mp3"


def download_file(url: str, out_path: Path, timeout: int = 60) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Descarga audios del entrenador desde recording_url (CSV/Excel o SQL).")
    parser.add_argument("--csv", default=os.environ.get("META_CSV", ""), help="CSV/Excel con columnas call_id y recording_url.")
    parser.add_argument("--out-dir", default=os.environ.get("AUDIO_DIR", r"inputs\\audios"), help="Carpeta destino de audios.")
    parser.add_argument("--from", dest="meta_desde", default=os.environ.get("META_DESDE", ""), help="Fecha inicio (YYYY-MM-DD) si lees desde SQL.")
    parser.add_argument("--to", dest="meta_hasta", default=os.environ.get("META_HASTA_EXC", ""), help="Fecha fin excluyente (YYYY-MM-DD) si lees desde SQL.")
    parser.add_argument("--limit", type=int, default=int(os.environ.get("DOWNLOAD_LIMIT", "0")), help="Limitar descargas (0 = sin límite).")
    parser.add_argument("--overwrite", action="store_true", help="Re-descargar aunque exista el archivo.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Cargar meta
    if args.csv:
        p = Path(args.csv)
        df = pd.read_excel(p) if p.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(p)
        df.columns = [c.strip().lower() for c in df.columns]
    else:
        df = fetch_meta_from_sql(meta_desde=args.meta_desde or None, meta_hasta_exc=args.meta_hasta or None)

    if "call_id" not in df.columns or "recording_url" not in df.columns:
        raise ValueError("El input debe tener columnas call_id y recording_url.")

    total = len(df)
    done = skipped = failed = 0

    for _, row in df.iterrows():
        if args.limit and done >= args.limit:
            break

        call_id = str(row["call_id"]).strip()
        url = str(row["recording_url"]).strip()

        if not call_id or not url or url.lower() == "nan":
            skipped += 1
            continue

        out_path = out_dir / f"{call_id}{guess_ext(url)}"
        if out_path.exists() and not args.overwrite:
            skipped += 1
            continue

        try:
            download_file(url, out_path)
            done += 1
            if done % 25 == 0:
                print(f"⬇️ Descargados: {done}/{total} (saltados: {skipped}, fallidos: {failed})")
        except Exception as e:
            failed += 1
            print(f"❌ Falló {call_id}: {e}")

    print(f"✅ Listo. Descargados: {done} | Saltados: {skipped} | Fallidos: {failed} | Total meta: {total}")


if __name__ == "__main__":
    main()
