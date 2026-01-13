# -*- coding: utf-8 -*-
"""Predicción de posts (tendencias) con Ollama – Escucha Social CUN

Este script toma un histórico de posts (DataFrame) con columnas mínimas:
- Origen
- Post_Date
- justificacion_post  (texto del post / explicación o contenido)

Opcionalmente, también puede usar columnas de interacción (likes, comments, shares, etc.).
El pipeline construye tendencias recientes por semana y usa **Ollama local** para generar:
- temas por intervalo (por defecto intervalos de diciembre 2025)
- hashtags sugeridos
- palabras clave SEO
- recomendaciones gráficas
- (opcional) intervalo estimado de interacciones

⚠️ No incluyas datos sensibles en repos públicos. Ver docs/SECURITY.md.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

import pandas as pd
from collections import Counter
import re
import json
import requests
from urllib.parse import urlparse

# =========================
# CONFIG OLLAMA
# =========================
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE}/api/chat"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE}/api/generate"

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
TIMEOUT = int(os.environ.get("TIMEOUT", "600"))
# =========================
# INTERVALOS DICIEMBRE 2025
# =========================
INTERVALOS_DICIEMBRE_2025 = [
    {"inicio": "2025-12-01", "fin": "2025-12-06"},
    {"inicio": "2025-12-07", "fin": "2025-12-13"},
    {"inicio": "2025-12-14", "fin": "2025-12-20"},
    {"inicio": "2025-12-21", "fin": "2025-12-27"},
    {"inicio": "2025-12-28", "fin": "2025-12-31"},
]

REDES = ["instagram", "facebook", "linkedin", "tiktok", "youtube"]
FORMATOS_VALIDOS = ["reel", "carrusel", "post", "story", "video", "short", "live"]
AUDIENCIAS_VALIDAS = ["aspirantes", "estudiantes activos", "egresados", "padres", "empresas"]


# =========================
# CARGA DE DATOS (archivo o SQL)
# =========================

def load_input_df(path: str, sheet: str | None = None) -> "pd.DataFrame":
    import pandas as pd
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe INPUT_PATH: {p}")
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p, sheet_name=(sheet or 0))
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Formato no soportado: {p.suffix}. Usa .xlsx o .csv.")

def load_from_sql_server(query: str) -> "pd.DataFrame":
    \"\"\"Carga desde SQL Server usando pyodbc. Requiere ODBC Driver instalado.\"\"\"
    import pandas as pd
    try:
        import pyodbc
    except Exception as e:
        raise RuntimeError("Falta pyodbc. Instala requirements.txt y ODBC Driver 17/18.") from e

    server = os.environ.get("SQL_SERVER", "")
    database = os.environ.get("SQL_DATABASE", "")
    trusted = os.environ.get("SQL_TRUSTED", "true").lower() in {"1","true","yes","y"}
    user = os.environ.get("SQL_USER", "")
    password = os.environ.get("SQL_PASSWORD", "")
    driver = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    if not server or not database:
        raise ValueError("Faltan SQL_SERVER / SQL_DATABASE en variables de entorno.")

    if trusted:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    else:
        if not user or not password:
            raise ValueError("Faltan SQL_USER / SQL_PASSWORD (o activa SQL_TRUSTED=true).")
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={user};PWD={password};"

    with pyodbc.connect(conn_str) as conn:
        return pd.read_sql(query, conn)

def load_intervals(path: str | None) -> List[Dict[str,str]]:
    \"\"\"Carga intervalos desde JSON (lista de {inicio, fin}). Si no hay, usa INTERVALOS_DICIEMBRE_2025.\"\"\"
    if not path:
        return INTERVALOS_DICIEMBRE_2025
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe INTERVALS_JSON: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("INTERVALS_JSON debe ser una lista de objetos {inicio, fin}.")
    for it in data:
        if not isinstance(it, dict) or "inicio" not in it or "fin" not in it:
            raise ValueError("Cada intervalo debe tener 'inicio' y 'fin'.")
    return data

# =========================
# HELPERS JSON
# =========================
def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

def _extract_json(text: str) -> dict:
    text = _strip_code_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a == -1 or b == -1 or b <= a:
            raise
        return json.loads(text[a:b+1])

def _print_http_error(r: requests.Response, tag: str):
    try:
        print(f"[{tag}] HTTP {r.status_code} -> {r.text[:500]}")
    except Exception:
        print(f"[{tag}] HTTP {r.status_code}")

# =========================
# NORMALIZACIÓN DATOS
# =========================
def limpiar_origen(origen):
    s = str(origen).strip()
    if s.lower().startswith(("http://", "https://")):
        try:
            dom = urlparse(s).netloc.lower().replace("www.", "")
            return dom if dom else "url"
        except Exception:
            return "url"
    return s

def normalizar_post_date(col: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(col):
        return pd.to_datetime(col, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(col, errors="coerce")

def obtener_palabras_clave(texto):
    stop = {
        "para","pero","como","con","del","desde","donde","durante","entre","porque","cuando","que","por","una","uno",
        "sobre","sin","son","sus","tiene","tienen","hay","fue","han","más","muy","todo","todos","todas","ellos","ellas",
        "nos","nuestra","nuestro","tu","tus","yo","el","la","los","las","de","y","o","a","al","se","es","no","si","sí"
    }
    if pd.isna(texto):
        return []
    t = re.sub(r"[^\w\s]", "", str(texto).lower())
    return [p for p in t.split() if p not in stop and len(p) > 3]

def detectar_columnas_interaccion(df: pd.DataFrame) -> list:
    patrones = [
        "interac", "interaccion", "engagement", "reaccion", "reacciones",
        "like", "likes", "me_gusta",
        "comment", "coment", "comentario", "comentarios",
        "share", "shares", "compart", "compartido", "compartidos",
        "save", "saves", "guard", "guardado", "guardados",
        "view", "views", "visual", "visualizacion", "visualizaciones",
        "click", "clicks", "clic", "clics"
    ]
    cols = []
    for c in df.columns:
        cl = str(c).lower()
        if any(p in cl for p in patrones) and pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols

def construir_df_tendencias_cun(df4: pd.DataFrame, verbose: bool = True) -> (pd.DataFrame, dict):
    """
    Construye tendencias por Semana_Año y Origen.
    Si detecta columnas numéricas de interacción, calcula baseline P50/P75 por semana.
    """
    req = ["Origen", "justificacion_post", "Post_Date"]
    faltan = [c for c in req if c not in df4.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en df4: {faltan}")

    df = df4[req + [c for c in df4.columns if c not in req]].copy()
    if verbose:
        print("rows inicial:", len(df))

    df["Origen"] = df["Origen"].apply(limpiar_origen)
    df = df.dropna(subset=["Origen"]).copy()

    df["Post_Date"] = normalizar_post_date(df["Post_Date"])
    df = df.dropna(subset=["Post_Date"]).copy()

    if verbose:
        print("rows fecha válida:", len(df))

    df["Semana_Año"] = df["Post_Date"].dt.strftime("%Y-%W")
    df["Palabras_Post"] = df["justificacion_post"].apply(obtener_palabras_clave)

    # interacciones (opcional)
    inter_cols = detectar_columnas_interaccion(df)
    baseline_info = {"inter_cols": inter_cols, "p50_global": None, "p75_global": None}

    if inter_cols:
        df["_interacciones"] = df[inter_cols].fillna(0).sum(axis=1)
    else:
        if verbose:
            print("⚠️ No se detectaron columnas de interacción -> el LLM estimará sin baseline numérico.")

    datos = []
    for (semana, origen), g in df.groupby(["Semana_Año", "Origen"]):
        conteo = Counter([p for sub in g["Palabras_Post"] for p in sub])
        top = [p for p, _ in conteo.most_common(20)]

        row = {
            "Semana_Año": semana,
            "Origen": str(origen),
            "Fecha_Ejemplo": g["Post_Date"].min().strftime("%Y-%m-%d"),
            "N_Posts": int(len(g)),
            "Temas_Tendencia_Recientes": ", ".join(top),
        }
        if inter_cols:
            row["Interacciones_P50"] = float(g["_interacciones"].quantile(0.50))
            row["Interacciones_P75"] = float(g["_interacciones"].quantile(0.75))
        else:
            row["Interacciones_P50"] = None
            row["Interacciones_P75"] = None

        datos.append(row)

    out = pd.DataFrame(datos).sort_values("Semana_Año")
    if verbose:
        print("tendencias agrupadas:", len(out))

    if inter_cols and not out["Interacciones_P50"].dropna().empty:
        baseline_info["p50_global"] = float(out["Interacciones_P50"].dropna().median())
        baseline_info["p75_global"] = float(out["Interacciones_P75"].dropna().median())

    return out, baseline_info

def top_keywords_global(df_tendencias: pd.DataFrame, top_n: int = 30) -> list:
    all_words = []
    for s in df_tendencias["Temas_Tendencia_Recientes"].astype(str).tolist():
        all_words.extend([p.strip() for p in s.split(",") if p.strip()])
    c = Counter(all_words)
    return [w for w, _ in c.most_common(top_n)]

# =========================
# OLLAMA CALL (chat con fallback a generate)
# =========================
def ollama_chat_or_generate(prompt: str, fmt="json", temperature=0.35, num_predict=1600, num_ctx=8192, verbose=True, retries=1) -> dict:
    """
    Intenta /api/chat primero; si falla, intenta /api/generate.
    """
    # 1) CHAT
    payload_chat = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "Responde únicamente en JSON válido. Sin texto adicional."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": fmt,
        "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": num_ctx},
    }

    last_err = None
    for _ in range(retries + 1):
        try:
            r = requests.post(OLLAMA_CHAT_URL, json=payload_chat, timeout=TIMEOUT)
            if verbose:
                print("[ollama/chat] status:", r.status_code)
            if r.status_code != 200:
                _print_http_error(r, "ollama/chat")
                r.raise_for_status()
            return _extract_json(r.json()["message"]["content"])
        except Exception as e:
            last_err = e

    # 2) GENERATE fallback
    if verbose:
        print("[fallback] probando /api/generate por error en /api/chat:", repr(last_err))

    payload_gen = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": fmt,
        "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": num_ctx},
    }

    r = requests.post(OLLAMA_GENERATE_URL, json=payload_gen, timeout=TIMEOUT)
    if verbose:
        print("[ollama/generate] status:", r.status_code)
    if r.status_code != 200:
        _print_http_error(r, "ollama/generate")
        r.raise_for_status()

    return _extract_json(r.json().get("response", ""))

# =========================
# SCHEMA (opcional) - si tu Ollama lo soporta
# =========================
def build_schema_intervalo_cun(inicio: str, fin: str) -> dict:
    obj_item = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "tema_principal","audiencia","justificacion","formato","cta",
            "palabras_clave_seo","recomendaciones_graficas","interacciones_estimadas"
        ],
        "properties": {
            "tema_principal": {"type": "string", "minLength": 12, "pattern": r"^(?!.*[,]).+$"},
            "audiencia": {"type": "string", "enum": AUDIENCIAS_VALIDAS},
            "justificacion": {"type": "string", "minLength": 70},
            "formato": {"type": "string", "enum": FORMATOS_VALIDOS},
            "cta": {"type": "string", "minLength": 8},
            "palabras_clave_seo": {
                "type": "array", "minItems": 5, "maxItems": 5,
                "items": {"type": "string", "minLength": 3}
            },
            "recomendaciones_graficas": {
                "type": "string",
                "minLength": 160,
                "pattern": r"^.+ \| .+ \| .+ \| .+$"
            },
            "interacciones_estimadas": {
                "type": "object",
                "additionalProperties": False,
                "required": ["unidad","min","probable","max","supuesto"],
                "properties": {
                    "unidad": {"type": "string", "enum": ["interacciones_totales"]},
                    "min": {"type": "integer", "minimum": 0},
                    "probable": {"type": "integer", "minimum": 0},
                    "max": {"type": "integer", "minimum": 0},
                    "supuesto": {"type": "string", "minLength": 20}
                }
            }
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["universidad", "rango", "por_red"],
        "properties": {
            "universidad": {"type": "string", "const": "CUN"},
            "rango": {
                "type": "object",
                "additionalProperties": False,
                "required": ["inicio", "fin"],
                "properties": {"inicio": {"type": "string", "const": inicio}, "fin": {"type": "string", "const": fin}},
            },
            "por_red": {
                "type": "object",
                "additionalProperties": False,
                "required": REDES,
                "properties": {red: {"type": "array", "minItems": 2, "maxItems": 2, "items": obj_item} for red in REDES},
            },
        },
    }

# =========================
# PROMPT
# =========================
def prompt_intervalo_cun(hist: pd.DataFrame, inicio: str, fin: str, top_kws: list, baseline: dict) -> str:
    hist_json = json.dumps(hist.to_dict("records"), ensure_ascii=False)
    kws_json = json.dumps(top_kws, ensure_ascii=False)

    baseline_txt = ""
    if baseline.get("inter_cols"):
        baseline_txt = (
            f"Baseline numérico (histórico): p50≈{baseline.get('p50_global')} | p75≈{baseline.get('p75_global')} "
            f"(métrica = suma de {baseline.get('inter_cols')}).\n"
            "Usa este baseline para estimar interacciones (min/probable/max) por recomendación.\n"
        )
    else:
        baseline_txt = (
            "No hay columnas numéricas de interacción en el histórico. Estima interacciones (min/probable/max) "
            "con supuestos conservadores y explícalos en 'supuesto'.\n"
        )

    return (
        "Eres estratega de contenido para EDUCACIÓN SUPERIOR.\n"
        "Universidad objetivo: CUN.\n"
        f"Intervalo: {inicio} a {fin}.\n\n"

        "Necesito EXACTAMENTE 2 recomendaciones por red social: instagram, facebook, linkedin, tiktok, youtube.\n"
        "Las 2 recomendaciones de cada red deben ser para AUDIENCIAS DIFERENTES.\n\n"

        "REGLAS OBLIGATORIAS:\n"
        "- TODO en español.\n"
        "- Prohibido usar 'Yes' o hashtags como respuesta de 'recomendaciones_graficas'.\n"
        "- 'tema_principal' debe ser una sola idea (sin comas, sin lista de keywords).\n"
        "- 'justificacion' debe ser frase completa (>=70 caracteres) e incluir 2-3 keywords del histórico.\n"
        "- 'recomendaciones_graficas' debe tener 4 bloques separados por ' | ' así:\n"
        "  Hook visual (2s) | Composición+ratio | Texto en pantalla+CTA | Motion/edición+subtítulos\n"
        "- Incluye 'interacciones_estimadas' con:\n"
        '  {"unidad":"interacciones_totales","min":123,"probable":456,"max":789,"supuesto":"..."}\n'
        "- Ratios sugeridos por red:\n"
        "  Instagram: 4:5 (carrusel) o 9:16 (reel)\n"
        "  Facebook: 1:1 o 4:5\n"
        "  LinkedIn: 1:1 o 4:5 (tono más profesional)\n"
        "  TikTok: 9:16\n"
        "  YouTube: 16:9 (video) o 9:16 (short)\n\n"

        f"{baseline_txt}\n"
        "Keywords frecuentes del histórico:\n"
        f"{kws_json}\n\n"
        "Histórico (CUN):\n"
        f"{hist_json}\n"
    )

# =========================
# REPARAR SALIDAS (si viene "Yes", hashtags o strings flojos)
# =========================
def reparar_salida(resultado: dict, verbose: bool = False) -> dict:
    def needs_fix(it: dict) -> bool:
        rg = str(it.get("recomendaciones_graficas", "")).strip()
        tp = str(it.get("tema_principal", "")).strip()
        js = str(it.get("justificacion", "")).strip()
        if "," in tp:
            return True
        if len(js) < 70:
            return True
        if rg.lower().startswith("yes") or rg.startswith("#"):
            return True
        if " | " not in rg:
            return True
        if len(rg) < 160:
            return True
        ie = it.get("interacciones_estimadas", {})
        if not isinstance(ie, dict) or any(k not in ie for k in ["min","probable","max","supuesto","unidad"]):
            return True
        return False

    for bloque in resultado.get("predicciones", []):
        por_red = bloque.get("por_red", {})
        for red, items in por_red.items():
            for it in items:
                if not needs_fix(it):
                    continue

                fix_prompt = (
                    "Corrige SOLO estos campos y devuelve SOLO JSON válido (sin texto):\n"
                    "1) tema_principal: una sola idea SIN comas.\n"
                    "2) justificacion: frase completa (>=70 caracteres) con 2-3 keywords.\n"
                    "3) recomendaciones_graficas: 4 bloques con ' | ' y ratio.\n"
                    '4) interacciones_estimadas: {"unidad":"interacciones_totales","min":int,"probable":int,"max":int,"supuesto":"..."}\n\n'
                    f"Red: {red}\n"
                    f"Audiencia: {it.get('audiencia')}\n"
                    f"Formato: {it.get('formato')}\n"
                    f"Palabras SEO: {it.get('palabras_clave_seo')}\n\n"
                    "Devuelve SOLO:\n"
                    '{"tema_principal":"...", "justificacion":"...", "recomendaciones_graficas":"Hook | Composición+ratio | Texto+CTA | Motion+subtítulos", '
                    '"interacciones_estimadas":{"unidad":"interacciones_totales","min":0,"probable":0,"max":0,"supuesto":"..."}}'
                )

                resp = ollama_chat_or_generate(
                    fix_prompt,
                    fmt="json",
                    temperature=0.35,
                    num_predict=700,
                    num_ctx=4096,
                    verbose=verbose
                )

                it["tema_principal"] = resp.get("tema_principal", it.get("tema_principal"))
                it["justificacion"] = resp.get("justificacion", it.get("justificacion"))
                it["recomendaciones_graficas"] = resp.get("recomendaciones_graficas", it.get("recomendaciones_graficas"))
                it["interacciones_estimadas"] = resp.get("interacciones_estimadas", it.get("interacciones_estimadas"))

    return resultado

# =========================
# FUNCIÓN FINAL (CUN)
# =========================
def predecir_dic_intervalos_cun(
    df4: pd.DataFrame,
    intervalos=INTERVALOS_DICIEMBRE_2025,
    max_filas_llm=160,
    verbose=True,
    intentar_schema=True
) -> dict:

    df_t, baseline = construir_df_tendencias_cun(df4, verbose=verbose)

    df_llm = df_t.tail(max_filas_llm).copy()
    kws = top_keywords_global(df_llm, top_n=30)

    if verbose:
        print("filas enviadas al LLM (histórico):", len(df_llm))
        print(df_llm.head(3).to_string(index=False))

    predicciones = []
    for i, itv in enumerate(intervalos, start=1):
        inicio, fin = itv["inicio"], itv["fin"]
        if verbose:
            print(f"\n=== Intervalo {i}/{len(intervalos)}: {inicio} a {fin} ===")

        p = prompt_intervalo_cun(df_llm, inicio, fin, kws, baseline)

        # Si tu Ollama soporta JSON Schema, úsalo; si no, cae a json normal
        if intentar_schema:
            schema = build_schema_intervalo_cun(inicio, fin)
            try:
                resp = ollama_chat_or_generate(p, fmt=schema, temperature=0.35, num_predict=1700, num_ctx=8192, verbose=verbose)
            except Exception as e:
                if verbose:
                    print("[schema] no soportado o falló -> fallback format=json | error:", repr(e))
                resp = ollama_chat_or_generate(p, fmt="json", temperature=0.45, num_predict=1900, num_ctx=8192, verbose=verbose)
        else:
            resp = ollama_chat_or_generate(p, fmt="json", temperature=0.45, num_predict=1900, num_ctx=8192, verbose=verbose)

        predicciones.append(resp)

    resultado = {"predicciones": predicciones}
    # Reparación ligera opcional:
    resultado = reparar_salida(resultado, verbose=False)
    return resultado


# =========================
# RUN + CLI
# =========================

def run(df4, intervalos=None, export_json: str | None = None, verbose: bool = True, intentar_schema: bool = True) -> dict:
    \"\"\"Ejecuta predicción y (opcional) guarda JSON.\"\"\"
    if intervalos is None:
        intervalos = INTERVALOS_DICIEMBRE_2025
    resultado = predecir_dic_intervalos_cun(
        df4,
        intervalos=intervalos,
        verbose=verbose,
        intentar_schema=intentar_schema
    )
    if export_json:
        Path(export_json).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        if verbose:
            print(f"✅ JSON guardado en: {export_json}")
    return resultado


def main():
    load_dotenv()

    import argparse

    parser = argparse.ArgumentParser(description="Predicción de posts (tendencias) con Ollama – Escucha Social")
    parser.add_argument("--input", default=os.environ.get("INPUT_PATH",""), help="Ruta a .xlsx/.csv con histórico.")
    parser.add_argument("--sheet", default=os.environ.get("INPUT_SHEET",""), help="Hoja de Excel (opcional).")
    parser.add_argument("--sql", action="store_true", help="Cargar histórico desde SQL Server (usa SQL_QUERY o default).")
    parser.add_argument("--sql-query", default=os.environ.get("SQL_QUERY",""), help="Query para SQL Server.")
    parser.add_argument("--intervals", default=os.environ.get("INTERVALS_JSON",""), help="Ruta JSON con intervalos {inicio, fin}.")
    parser.add_argument("--export-json", default=os.environ.get("EXPORT_JSON","predicciones_posts.json"), help="Ruta del JSON de salida.")
    parser.add_argument("--no-schema", action="store_true", help="Desactiva validación estricta de schema (más permisivo).")
    parser.add_argument("--quiet", action="store_true", help="Menos logs.")

    args = parser.parse_args()
    verbose = not args.quiet

    if args.sql:
        query = args.sql_query or \"\"\"SELECT * FROM COE.escucha_social_nuevo
WHERE Origen = 'corporacion-unificada-nacional-de-educacion-superior-cun'\"\"\"
        df4 = load_from_sql_server(query)
    else:
        if not args.input:
            raise SystemExit("❌ Falta --input o activa --sql (o define INPUT_PATH en .env).")
        df4 = load_input_df(args.input, (args.sheet or None))

    intervalos = load_intervals(args.intervals or None)

    run(
        df4,
        intervalos=intervalos,
        export_json=args.export_json,
        verbose=verbose,
        intentar_schema=(not args.no_schema),
    )


if __name__ == "__main__":
    main()
