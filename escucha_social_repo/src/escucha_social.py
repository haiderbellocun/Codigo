# -*- coding: utf-8 -*-
# === ESCUCHA SOCIAL EXPERTA (Ollama) → df_final + df_sql listo para SQL ===

import os
import requests
import json
import re
import pandas as pd
from string import Template
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

# ---------------------- CONFIGURACIÓN ----------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("MODEL", "qwen2.5:7b-instruct")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "3"))
PRINT_EVERY = int(os.environ.get("PRINT_EVERY", "50"))
TIMEOUT = int(os.environ.get("TIMEOUT", "180"))
RETRIES = int(os.environ.get("RETRIES", "2"))

LIMIT = (int(os.environ.get("LIMIT","0")) or None)  # 0 => todo
# ======= ENTRADA (archivo o dataframe en memoria) =======
def load_input_df(path: str, sheet: str | None = None) -> pd.DataFrame:
    """Carga el dataset de entrada desde xlsx/csv."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe INPUT_PATH: {p}")
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p, sheet_name=(sheet or 0))
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Formato no soportado: {p.suffix}. Usa .xlsx o .csv.")

INPUT_PATH  = os.environ.get("INPUT_PATH", "")
INPUT_SHEET = os.environ.get("INPUT_SHEET", "")  # opcional (nombre de hoja)

if INPUT_PATH:
    INPUT_DF = load_input_df(INPUT_PATH, INPUT_SHEET or None)
else:
    # Modo notebook: asume que `df` ya existe en memoria
    try:
        INPUT_DF = df  # type: ignore[name-defined]
    except Exception as e:
        raise RuntimeError(
            "No veo INPUT_PATH configurado y tampoco existe `df` en memoria. "
            "Define INPUT_PATH (xlsx/csv) o carga df en el notebook."
        ) from e


# Columnas de tu dataset (origen)
COL_POST_IN     = "Post"
COL_COMENT_IN   = "textoComentario"       # si tu DF ya trae "Comentario", se usa ese
COL_FECHA_IN    = "Fecha del comentario"  # debe coincidir con tu DF

EXPORT_XLSX = os.environ.get("EXPORT_XLSX", "analisis_escucha_social.xlsx")
def check_ollama():
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    r.raise_for_status()
    print(f"✅ Ollama activo en {OLLAMA_URL}")


# ---- LISTAS Y REGLAS (Negocio) ----
ALLOWED_SENT = {
    "gratitud_alegria","confianza_seguridad","sorpresa",
    "tristeza","miedo_preocupacion","desagrado","enojo_frustracion",
    "consulta_sugerencia"
}

FEAR_EMOJI = {"😟","😰","😨","😱","😥","😓","😔"}
fear_regex = re.compile(r"\b(miedo|temo|temer|preocupad\w*|ansied\w*|p[aá]nico|asustad\w*)\b", re.IGNORECASE)
neg_strong = re.compile(r"\b(p[eé]simo|estafa|robo|asco|in[uú]tiles|ladrones|engañ)\b", re.IGNORECASE)


def map_tipo_from_sent(sent):
    if sent in {"gratitud_alegria","confianza_seguridad","sorpresa"}:
        return "felicitacion_positivo"
    if sent in {"tristeza","miedo_preocupacion","desagrado","enojo_frustracion"}:
        return "queja_reclamo_negativo"
    if sent == "consulta_sugerencia":
        return "pregunta_neutral"
    return "otro"


def fix_miedo(texto: str, sent: str) -> str:
    if sent != "miedo_preocupacion":
        return sent
    t = (texto or "").lower()
    has_signal = any(e in t for e in FEAR_EMOJI) or bool(fear_regex.search(t))
    if not has_signal:
        if neg_strong.search(t):
            return "enojo_frustracion"
        return "consulta_sugerencia"
    return sent


def extract_json(s: str):
    """Extractor robusto de JSON desde la respuesta del LLM."""
    if not s:
        return None

    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = s[start:end+1]
        try:
            return json.loads(chunk)
        except Exception:
            pass

    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    return None


def infer_tema_fallback(texto: str) -> str:
    t = (texto or "").lower()
    if "inscrip" in t or "matr" in t:
        return "admisiones_matricula"
    if "pag" in t or "cost" in t:
        return "pagos_finanzas"
    if "clase" in t or "curso" in t:
        return "educacion_academico"
    return "comunidad"


# ===== PROMPTS =====
PROMPT_COMENT = Template("""
Eres analista de Customer Experience. Clasifica este COMENTARIO:
1. SENTIMIENTO: gratitud_alegria | confianza_seguridad | sorpresa | tristeza | miedo_preocupacion | desagrado | enojo_frustracion | consulta_sugerencia
2. TIPO: felicitacion_positivo | queja_reclamo_negativo | pregunta_neutral
3. TEMA: educacion_academico | servicio_atencion | pagos_finanzas | admisiones_matricula | eventos | infraestructura | comunidad | empleo_practicas | comunicaciones_marketing | otro
4. CLASE: elogio | queja | pregunta | sugerencia | experiencia | spam_bot | offtopic | otro
Responde SOLO JSON: {"sentimiento":"...", "tipo_comentario":"...", "tema":"...", "clase_comentario":"...", "justificacion":"..."}
Texto: \"\"\"$texto\"\"\" 
""")

PROMPT_POST = Template("""
Eres experto en Marketing. Analiza el POST y extrae la oferta comercial:
1. TEMA_POST: (educacion_academico, servicio_atencion, pagos_finanzas, admisiones_matricula, eventos, infraestructura, comunidad, empleo_practicas, comunicaciones_marketing, otro)
2. CLASE_POST: (informativo, promocional, convocatoria, evento, logro_testimonial, entretenimiento, servicio_atencion, comunidad, otro)
3. PRODUCTO_DETECTADO:
   - Nombre EXACTO del producto/beneficio/programa ofrecido.
   - Si no hay oferta clara, pon "ninguno".
   - Máximo 5 palabras.
Responde SOLO JSON: {"tema_post":"...", "clase_post":"...", "producto_detectado":"...", "justificacion_post":"..."}
Texto: \"\"\"$texto\"\"\" 
""")


def classify_comment(texto, retries=RETRIES):
    if not str(texto).strip():
        return {
            "sentimiento": "consulta_sugerencia",
            "tipo_comentario": "pregunta_neutral",
            "tema": "comunidad",
            "clase_comentario": "otro",
            "justificacion": "vacio"
        }

    payload = {
        "model": MODEL,
        "prompt": PROMPT_COMENT.substitute(texto=texto),
        "stream": False,
        "options": {"temperature": 0}
    }

    for _ in range(retries + 1):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            j = extract_json(r.json().get("response", "")) or {}

            sent = fix_miedo(texto, (j.get("sentimiento") or "").lower())
            if sent not in ALLOWED_SENT:
                sent = "consulta_sugerencia"

            tema = (j.get("tema") or "").lower()
            if tema == "otro":
                tema = infer_tema_fallback(texto)
            if tema == "otro":
                tema = "comunidad"

            tipo = j.get("tipo_comentario") or map_tipo_from_sent(sent)

            return {
                "sentimiento": sent,
                "tipo_comentario": tipo,
                "tema": tema,
                "clase_comentario": j.get("clase_comentario", "otro"),
                "justificacion": j.get("justificacion", "")
            }
        except Exception:
            pass

    return {
        "sentimiento": "consulta_sugerencia",
        "tipo_comentario": "pregunta_neutral",
        "tema": "comunidad",
        "clase_comentario": "otro",
        "justificacion": "error_ollama"
    }


def classify_post(texto, retries=RETRIES):
    if not str(texto).strip():
        return {
            "tema_post": "comunidad",
            "clase_post": "otro",
            "producto_detectado": "ninguno",
            "justificacion_post": "vacio"
        }

    payload = {
        "model": MODEL,
        "prompt": PROMPT_POST.substitute(texto=texto),
        "stream": False,
        "options": {"temperature": 0.1}
    }

    for _ in range(retries + 1):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            j = extract_json(r.json().get("response", "")) or {}

            tema = (j.get("tema_post") or "").lower()
            if tema == "otro":
                tema = infer_tema_fallback(texto)
            if tema == "otro":
                tema = "comunidad"

            prod = str(j.get("producto_detectado", "ninguno")).strip().strip('."').lower()
            if prod in {"ninguno","n/a","no aplica","no","informacion"}:
                prod = "ninguno"

            return {
                "tema_post": tema,
                "clase_post": j.get("clase_post", "otro"),
                "producto_detectado": prod,
                "justificacion_post": j.get("justificacion_post", "")
            }
        except Exception:
            pass

    return {
        "tema_post": "comunidad",
        "clase_post": "otro",
        "producto_detectado": "error",
        "justificacion_post": "error_ollama"
    }


def classify_series_parallel(df_source, colname, fn, rename_map, label):
    if colname not in df_source.columns:
        print(f"⚠️ No existe columna '{colname}' para {label}.")
        return pd.DataFrame()

    data = df_source[colname].fillna("").astype(str).tolist()
    total = len(data)
    results = [None] * total

    print(f"🚀 Iniciando {label} ({total} docs)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fn, txt): i for i, txt in enumerate(data)}
        completed = 0
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
            completed += 1
            if completed % PRINT_EVERY == 0:
                print(f"   [{label}] {completed}/{total}...", end="\r")

    print(f"✅ {label} terminado.              ")
    return pd.DataFrame(results).rename(columns=rename_map)


# ---- keywords -> palabras_clave_comentario ----
_STOP = {
    "que","de","la","el","en","y","a","los","las","un","una","por","para","con","no","si",
    "es","al","lo","se","mi","tu","su","me","te","le","les","ya","muy","más","mas","pero",
    "como","cuando","donde","del","hay","son","uno","este","esta","eso","esa","una"
}

def extraer_keywords(texto, topk=5):
    t = (texto or "").lower()
    toks = re.findall(r"[a-záéíóúñ]{3,}", t)
    toks = [w for w in toks if w not in _STOP]
    if not toks:
        return None
    top = [w for w, _ in Counter(toks).most_common(topk)]
    return ", ".join(top)


def normalizar_input(df_in: pd.DataFrame) -> pd.DataFrame:
    df0 = df_in.copy()
    df0 = df0.loc[:, ~df0.columns.duplicated(keep="last")]

    # Normaliza Comentario
    if "Comentario" not in df0.columns and COL_COMENT_IN in df0.columns:
        df0 = df0.rename(columns={COL_COMENT_IN: "Comentario"})

    # Normaliza Post
    if "Post" not in df0.columns and COL_POST_IN in df0.columns:
        df0 = df0.rename(columns={COL_POST_IN: "Post"})

    return df0


def enrich_data(df_in: pd.DataFrame) -> pd.DataFrame:
    df0 = df_in.copy()
    df0 = df0.loc[:, ~df0.columns.duplicated(keep="last")]

    # Fechas => anio, mes, semana, dia_semana
    if COL_FECHA_IN in df0.columns:
        dt = pd.to_datetime(df0[COL_FECHA_IN], errors="coerce")
        df0["anio"] = dt.dt.year.astype("Int64")
        df0["mes"] = dt.dt.month.astype("Int64")
        df0["semana"] = dt.dt.isocalendar().week.astype("Int64")
        df0["dia_semana"] = dt.dt.weekday.astype("Int64")  # 0=Lun ... 6=Dom
    else:
        for c in ["anio","mes","semana","dia_semana"]:
            if c not in df0.columns:
                df0[c] = pd.NA

    # Polaridad y tipo emoción
    pol_map = {
        "gratitud_alegria": 1, "confianza_seguridad": 1, "sorpresa": 0.5,
        "consulta_sugerencia": 0, "pregunta_neutral": 0,
        "tristeza": -0.5, "miedo_preocupacion": -1, "desagrado": -1, "enojo_frustracion": -1
    }

    if "sentimiento_comentario" in df0.columns:
        s = df0["sentimiento_comentario"].astype(str).str.lower()
        df0["polaridad_comentario"] = s.map(pol_map).fillna(0)

        pos = {"gratitud_alegria","confianza_seguridad","sorpresa"}
        neg = {"tristeza","miedo_preocupacion","desagrado","enojo_frustracion"}
        df0["emocion_tipo_comentario"] = s.map(
            lambda x: "positiva" if x in pos else ("negativa" if x in neg else "neutral")
        )
    else:
        df0["polaridad_comentario"] = 0
        df0["emocion_tipo_comentario"] = pd.NA

    # Keywords
    if "Comentario" in df0.columns:
        df0["palabras_clave_comentario"] = df0["Comentario"].astype(str).apply(extraer_keywords)
    else:
        df0["palabras_clave_comentario"] = pd.NA

    return df0


def get_product_stats(df0: pd.DataFrame) -> pd.DataFrame:
    if "producto_oferta" not in df0.columns:
        return pd.DataFrame()
    ignore = {"ninguno", "error", "n/a", "comunidad", "informacion", "foto", "post", "nan", "none"}
    series = df0["producto_oferta"].astype(str).str.lower().str.strip()
    counts = series[~series.isin(ignore)].value_counts().reset_index()
    counts.columns = ["Producto_Detectado", "Menciones_en_Posts"]
    return counts.head(60)


def preparar_df_sql(df_final: pd.DataFrame) -> pd.DataFrame:
    """
    df_sql con el schema EXACTO de tu tabla (según la captura).
    NOTA: la tabla NO incluye 'producto_oferta'. Si la necesitas en SQL, agrega la columna en la tabla.
    """
    df0 = df_final.copy()
    df0 = df0.loc[:, ~df0.columns.duplicated(keep="last")]

    required_cols = [
        "Post",
        "Comentario",
        "Fecha del comentario",
        "Origen",
        "Usu_Comentario",
        "URL_post",
        "Red_social",
        "Post_Date",
        "Traza",
        "ID_comentario",
        "sentimiento_comentario",
        "tipo_comentario_comentario",
        "tema_comentario",
        "clase_comentario",
        "justificacion_comentario",
        "tema_post",
        "clase_post",
        "justificacion_post",
        "anio",
        "mes",
        "semana",
        "dia_semana",
        "polaridad_comentario",
        "emocion_tipo_comentario",
        "palabras_clave_comentario",
    ]

    for c in required_cols:
        if c not in df0.columns:
            df0[c] = pd.NA

    return df0[required_cols]


# ------------------ EJECUCIÓN ------------------
check_ollama()



def run(INPUT_DF: pd.DataFrame, export_xlsx: str = None):
    """Ejecuta el pipeline y retorna (df_final, df_sql)."""
    global EXPORT_XLSX
    if export_xlsx:
        EXPORT_XLSX = export_xlsx
    df_work = normalizar_input(INPUT_DF)
    if LIMIT:
        df_work = df_work.head(LIMIT)

    print(f"📂 Dataset cargado: {df_work.shape}")

    # 1) Comentarios
    res_com = classify_series_parallel(
        df_work, "Comentario", classify_comment,
        rename_map={
            "sentimiento": "sentimiento_comentario",
            "tipo_comentario": "tipo_comentario_comentario",  # <-- como tu SQL
            "tema": "tema_comentario",
            "clase_comentario": "clase_comentario",
            "justificacion": "justificacion_comentario",
        },
        label="Comentarios"
    )

    # 2) Posts + producto
    res_post = classify_series_parallel(
        df_work, "Post", classify_post,
        rename_map={
            "tema_post": "tema_post",
            "clase_post": "clase_post",
            "producto_detectado": "producto_oferta",           # <-- se queda en df_final (no en df_sql)
            "justificacion_post": "justificacion_post",
        },
        label="Posts"
    )

    # 3) Evita duplicados antes del concat
    cols_nuevas = set(res_com.columns).union(set(res_post.columns))
    df_work_clean = df_work.drop(columns=[c for c in cols_nuevas if c in df_work.columns], errors="ignore")

    # 4) df_final
    df_final = pd.concat([df_work_clean.reset_index(drop=True), res_com, res_post], axis=1)

    # 5) Enriquecimiento => columnas del schema (anio, mes, semana, dia_semana, polaridad, emoción, keywords)
    df_final = enrich_data(df_final)

    # 6) Ranking productos (opcional)
    stats_prod = get_product_stats(df_final)

    # 7) df_sql listo para insertar (schema igual al de tu tabla)
    df_sql = preparar_df_sql(df_final)

    # --- sanity check ---
    print("✅ df_final cols:", len(df_final.columns))
    print("✅ df_sql cols:", df_sql.columns.tolist())
    print(df_sql.head(2))

    # 8) Export Excel (multihoja)
    print(f"💾 Generando Excel: {EXPORT_XLSX}")
    try:
        with pd.ExcelWriter(EXPORT_XLSX, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False, sheet_name="Data_Clasificada")
            df_sql.to_excel(writer, index=False, sheet_name="SQL_READY")
            if not stats_prod.empty:
                stats_prod.to_excel(writer, index=False, sheet_name="Ranking_Productos")
            if "tema_comentario" in df_final.columns:
                df_final["tema_comentario"].value_counts().reset_index().to_excel(
                    writer, index=False, sheet_name="Temas"
                )
        print("\n✨ ¡Proceso completado! Revisa 'SQL_READY' para cargar a SQL.")
    except PermissionError:
        print("❌ ERROR: El archivo Excel está abierto. Ciérralo e intenta de nuevo.")

    if __name__ == "__main__":
        import argparse
        from dotenv import load_dotenv

        load_dotenv()

        parser = argparse.ArgumentParser(description="Escucha Social (Ollama): clasifica comentarios y posts, genera df_sql y exporta Excel.")
        parser.add_argument("--input", default=os.environ.get("INPUT_PATH",""), help="Ruta a .xlsx o .csv. Alternativamente define INPUT_PATH en .env.")
        parser.add_argument("--sheet", default=os.environ.get("INPUT_SHEET",""), help="Hoja del Excel (opcional).")
        parser.add_argument("--export", default=os.environ.get("EXPORT_XLSX","analisis_escucha_social.xlsx"), help="Nombre/ruta del Excel de salida.")
        args = parser.parse_args()

        if args.input:
            os.environ["INPUT_PATH"] = args.input
        if args.sheet:
            os.environ["INPUT_SHEET"] = args.sheet
        if args.export:
            os.environ["EXPORT_XLSX"] = args.export

        # Re-ejecuta la carga según args (para modo CLI)
        if os.environ.get("INPUT_PATH"):
            INPUT_DF = load_input_df(os.environ["INPUT_PATH"], os.environ.get("INPUT_SHEET") or None)  # type: ignore[assignment]

        # Ejecuta el pipeline (el código de abajo corre en import-time en notebook; aquí lo dejamos igual)
        # Si quieres hacerlo más "limpio", mueve el bloque final a una función run().
        pass
    return df_final, df_sql

if __name__ == "__main__":
    from dotenv import load_dotenv
    import argparse

    load_dotenv()

    parser = argparse.ArgumentParser(description="Escucha Social (Ollama): clasifica comentarios y posts, exporta Excel y retorna df_sql.")
    parser.add_argument("--input", default=os.environ.get("INPUT_PATH",""), help="Ruta a .xlsx o .csv (o define INPUT_PATH en .env).")
    parser.add_argument("--sheet", default=os.environ.get("INPUT_SHEET",""), help="Hoja del Excel (opcional).")
    parser.add_argument("--export", default=os.environ.get("EXPORT_XLSX","analisis_escucha_social.xlsx"), help="Ruta/nombre del Excel de salida.")
    args = parser.parse_args()

    input_path = args.input or os.environ.get("INPUT_PATH","")
    if not input_path:
        raise SystemExit("❌ Falta --input o INPUT_PATH en .env")

    df_in = load_input_df(input_path, (args.sheet or os.environ.get("INPUT_SHEET") or None))
    run(df_in, export_xlsx=args.export)
