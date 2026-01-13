# -*- coding: utf-8 -*-
"""
Notas:
- Si el modelo te corta el JSON, sube OLLAMA_OPTIONS["num_predict"] (p.ej. 2200).
- Si el modelo soporta más contexto, sube num_ctx a 8192 para menos “pérdida” en clases largas.
"""

import os
import json
import re
import time
import random
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import inspect
import requests
import boto3
from boto3.s3.transfer import TransferConfig
import ctranslate2
import torch
from faster_whisper import WhisperModel
from dotenv import load_dotenv

load_dotenv()


# ================== CONFIGURACIÓN S3 ==================

S3_BUCKET = os.environ.get("S3_BUCKET", "cun-transcribe-five9")
S3_PREFIX_VIDEOS = os.environ.get("S3_PREFIX_VIDEOS", "Videos_clase_Profesores/video_12_04_25a/")  # termina en "/"

# Opcional: subir también los JSON a S3
UPLOAD_JSON_TO_S3 = os.environ.get("UPLOAD_JSON_TO_S3", "false").lower() in {"1","true","yes","y"}
S3_PREFIX_JSON = os.environ.get("S3_PREFIX_JSON", "Videos_clase_Profesores/video_12_04_25a/resumenes/")  # termina en "/"

# Cliente S3
s3 = boto3.client("s3")

# Descargas S3 más rápidas (ajusta max_concurrency según tu red)
S3_DOWNLOAD_CONFIG = TransferConfig(
    multipart_threshold=64 * 1024 * 1024,  # 64MB
    multipart_chunksize=16 * 1024 * 1024,  # 16MB
    max_concurrency=10,
    use_threads=True,
)

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}


# ================== CONFIGURACIÓN LOCAL ==================

LOCAL_VIDEO_DIR = Path(os.environ.get("LOCAL_VIDEO_DIR", r"C:\\videos_clases_s3"))
LOCAL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

TRANSCRIPTS_DIR = Path(os.environ.get("TRANSCRIPTS_DIR", r"C:\\transcripciones_clases_s3\\video_12_04_25a"))
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

JSON_DIR = Path(os.environ.get("JSON_DIR", r"C:\\resumenes_clases_json_s3\\12_04_25a"))
JSON_DIR.mkdir(parents=True, exist_ok=True)

# Si quieres probar con pocos videos:
LIMIT_VIDEOS: Optional[int] = None  # ej: 2  | None = todos



# ================== WHISPER (TRANSCRIPCIÓN) ==================

# OJO: faster-whisper usa CTranslate2. Torch puede estar en CPU y aun así Whisper ir en GPU.
CT2_CUDA_DEVICES = ctranslate2.get_cuda_device_count()
DEVICE = "cuda" if CT2_CUDA_DEVICES > 0 else "cpu"
DEVICE = os.environ.get("DEVICE", DEVICE)  # "cuda" o "cpu" para forzar

MODEL_NAME = os.environ.get("MODEL_NAME", "medium")
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
COMPUTE_TYPE = os.environ.get("COMPUTE_TYPE", COMPUTE_TYPE)  # float16/int8/...
LANG = os.environ.get("LANG", "es")

WHISPER_BATCH_SIZE = 16 if DEVICE == "cuda" else 1
WHISPER_BATCH_SIZE = int(os.environ.get("WHISPER_BATCH_SIZE", str(WHISPER_BATCH_SIZE)))

print(f"[WHISPER] CT2_CUDA_DEVICES={CT2_CUDA_DEVICES} | DEVICE={DEVICE} | COMPUTE_TYPE={COMPUTE_TYPE} | BATCH={WHISPER_BATCH_SIZE}")



# ================== OBJETIVOS DE ESTUDIO (CONTROL DE LARGO) ==================

RESUMEN_GENERAL_PALABRAS = (150, 220)
RESUMEN_ESTUDIO_PALABRAS = (600, 900)

PUNTOS_CLAVE_CANTIDAD = (10, 16)
TEMAS_PRINCIPALES_CANTIDAD = (6, 10)
GLOSARIO_CANTIDAD = (10, 18)
PREGUNTAS_REPASO_CANTIDAD = (6, 10)


# ================== OLLAMA (RESUMEN) ==================

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")

OLLAMA_OPTIONS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "num_ctx": 4096,     # si tu modelo lo soporta, prueba 8192
    "num_predict": 2000  # sube a 2000-2400 si el JSON se corta
}

# timeouts: (connect_timeout, read_timeout)
OLLAMA_TIMEOUT: Tuple[int, int] = (10, 1800)  # 10s connect, 30min read
OLLAMA_RETRIES = int(os.environ.get("OLLAMA_RETRIES", "3"))

# Tamaño máximo por chunk (si hay demasiados chunks, el resumen se vuelve muy lento)
MAX_CHARS_PER_CHUNK = int(os.environ.get("MAX_CHARS_PER_CHUNK", "20000"))
MAX_CHUNKS_HARD_LIMIT = int(os.environ.get("MAX_CHUNKS_HARD_LIMIT", "8"))  # límite duro


# ================== LOG ==================

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ================== UTILIDADES ==================

def save_text(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def safe_json_loads(s: str) -> Optional[dict]:
    try:
        return json.loads(s)
    except Exception:
        return None

def extract_json_fallback(s: str) -> Optional[dict]:
    """
    Fallback por si Ollama devuelve texto alrededor del JSON.
    """
    s = (s or "").strip()
    if not s:
        return None

    # Caso directo
    j = safe_json_loads(s)
    if isinstance(j, dict):
        return j

    # Buscar primer bloque {...}
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        j = safe_json_loads(s[start:end + 1])
        if isinstance(j, dict):
            return j

    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        j = safe_json_loads(m.group(0))
        if isinstance(j, dict):
            return j

    return None

def _ensure_list(x) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

def _ensure_str(x) -> str:
    return "" if x is None else str(x)

def normalize_summary_json(j: Dict[str, Any], video_name: str) -> Dict[str, Any]:
    """
    Asegura que el JSON final tenga TODAS las llaves esperadas y tipos consistentes.
    """
    if not isinstance(j, dict):
        j = {}

    out = {
        "video": video_name,
        "resumen_general": _ensure_str(j.get("resumen_general", "")),
        "resumen_estudio": _ensure_str(j.get("resumen_estudio", "")),
        "puntos_clave": _ensure_list(j.get("puntos_clave", [])),
        "temas_principales": _ensure_list(j.get("temas_principales", [])),
        "conceptos_importantes": _ensure_list(j.get("conceptos_importantes", [])),
        "glosario": _ensure_list(j.get("glosario", [])),
        "preguntas_repaso": _ensure_list(j.get("preguntas_repaso", [])),
        "tareas_o_recomendaciones": _ensure_list(j.get("tareas_o_recomendaciones", [])),
    }

    # Normaliza glosario y preguntas al formato esperado si vienen como strings
    glos = []
    for it in out["glosario"]:
        if isinstance(it, dict):
            glos.append({"termino": _ensure_str(it.get("termino", "")), "definicion": _ensure_str(it.get("definicion", ""))})
        else:
            s = _ensure_str(it).strip()
            if s:
                glos.append({"termino": s, "definicion": ""})
    out["glosario"] = glos

    preg = []
    for it in out["preguntas_repaso"]:
        if isinstance(it, dict):
            preg.append({"pregunta": _ensure_str(it.get("pregunta", "")), "respuesta_corta": _ensure_str(it.get("respuesta_corta", ""))})
        else:
            s = _ensure_str(it).strip()
            if s:
                preg.append({"pregunta": s, "respuesta_corta": ""})
    out["preguntas_repaso"] = preg

    return out


# ================== S3: LISTAR / DESCARGAR / SUBIR ==================

def list_s3_videos(bucket: str, prefix: str) -> List[str]:
    keys: List[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if Path(key).suffix.lower() in VIDEO_EXTS:
                keys.append(key)
    return keys

def download_s3_video(bucket: str, key: str, local_dir: Path) -> Path:
    local_path = local_dir / Path(key).name
    if local_path.exists():
        log(f"➡️ Video ya descargado: {local_path.name}")
        return local_path

    local_dir.mkdir(parents=True, exist_ok=True)
    log(f"⬇️ Descargando: s3://{bucket}/{key}")
    s3.download_file(bucket, key, str(local_path), Config=S3_DOWNLOAD_CONFIG)
    log(f"✅ Descargado: {local_path}")
    return local_path

def upload_json_to_s3(local_json: Path, bucket: str, prefix: str):
    key = prefix.rstrip("/") + "/" + local_json.name
    log(f"⬆️ Subiendo JSON a S3: s3://{bucket}/{key}")
    s3.upload_file(str(local_json), bucket, key)
    log("✅ JSON subido a S3")


# ================== WHISPER ==================

def load_whisper_model():
    log(f"🔊 Cargando Whisper '{MODEL_NAME}' en {DEVICE} (compute_type={COMPUTE_TYPE}) ...")

    kwargs = dict(
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )

    # algunas versiones soportan device_index
    import inspect
    sig = inspect.signature(WhisperModel)
    if "device_index" in sig.parameters and DEVICE == "cuda":
        kwargs["device_index"] = 0

    model = WhisperModel(MODEL_NAME, **kwargs)

    log("✅ Whisper cargado.")
    return model


def transcribe_video(model: WhisperModel, video_path: Path, out_txt: Path, force: bool = False) -> Path:
    if out_txt.exists() and not force:
        log(f"➡️ TXT ya existe: {out_txt.name}")
        return out_txt

    log(f"🎧 Transcribiendo: {video_path.name} (batch_size={WHISPER_BATCH_SIZE}) ...")
    t0 = time.time()

    # kwargs base (compatibles)
    kwargs = dict(
        language=LANG,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400),
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=False,
    )

    # Estos flags no existen en algunas versiones viejas, así que los agregamos SOLO si están
    sig = inspect.signature(model.transcribe)
    params = sig.parameters

    if "without_timestamps" in params:
        kwargs["without_timestamps"] = True
    if "word_timestamps" in params:
        kwargs["word_timestamps"] = False
    if "batch_size" in params:
        kwargs["batch_size"] = WHISPER_BATCH_SIZE

    segments, info = model.transcribe(str(video_path), **kwargs)

    text = "".join(seg.text for seg in segments).strip()
    save_text(out_txt, text)

    dt = time.time() - t0
    log(f"✅ TXT guardado: {out_txt.name} ({len(text)} chars) | {dt/60:.1f} min")
    return out_txt


# ================== OLLAMA ==================

def call_ollama_json(prompt: str) -> Dict[str, Any]:
    """
    Llama a Ollama forzando salida JSON y con retries.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "60m",
        "options": OLLAMA_OPTIONS,
    }

    last_err = None
    for attempt in range(1, OLLAMA_RETRIES + 1):
        try:
            resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            raw = (data.get("response") or "").strip()

            j = safe_json_loads(raw)
            if isinstance(j, dict):
                return j

            j2 = extract_json_fallback(raw)
            if isinstance(j2, dict):
                return j2

            raise ValueError("Ollama devolvió respuesta sin JSON válido.")

        except Exception as e:
            last_err = e
            wait = min(20, 2 ** attempt) + random.random()
            log(f"⚠️ Ollama error (intento {attempt}/{OLLAMA_RETRIES}): {e} | reintento en {wait:.1f}s")
            time.sleep(wait)

    raise RuntimeError(f"Falló Ollama tras {OLLAMA_RETRIES} intentos. Último error: {last_err}")


# ================== PROMPTS ==================

def build_summary_prompt_full(transcript: str, video_name: str) -> str:
    gmin, gmax = RESUMEN_GENERAL_PALABRAS
    emin, emax = RESUMEN_ESTUDIO_PALABRAS
    pmin, pmax = PUNTOS_CLAVE_CANTIDAD
    tmin, tmax = TEMAS_PRINCIPALES_CANTIDAD
    glmin, glmax = GLOSARIO_CANTIDAD
    qmin, qmax = PREGUNTAS_REPASO_CANTIDAD

    return f"""
Eres un asistente experto en educación que transforma transcripciones de clases en apuntes para estudiar.

Vas a recibir la transcripción casi completa de una CLASE en español.
Debes devolver SOLO un objeto JSON válido con esta estructura (sin texto adicional):

{{
  "video": "{video_name}",
  "resumen_general": "Resumen rápido de {gmin}-{gmax} palabras (1 párrafo).",
  "resumen_estudio": "Apuntes para estudiar de {emin}-{emax} palabras, con subtítulos y viñetas cuando aplique. Incluye: (1) qué se explicó, (2) pasos/procesos, (3) ejemplos si aparecen, (4) conclusiones.",
  "puntos_clave": ["{pmin}-{pmax} bullets, cada bullet 10-18 palabras aprox."],
  "temas_principales": ["{tmin}-{tmax} temas (frases cortas)."],
  "conceptos_importantes": ["lista de conceptos importantes (solo nombres, sin definición larga)."],
  "glosario": [{{"termino":"...","definicion":"definición corta 1-2 líneas"}}],  // entre {glmin}-{glmax} items
  "preguntas_repaso": [{{"pregunta":"...","respuesta_corta":"..."}}],            // entre {qmin}-{qmax} items
  "tareas_o_recomendaciones": ["si el profesor dejó tareas o sugerencias; si no, []"]
}}

Reglas:
- El JSON debe ser válido (comillas dobles, sin comentarios).
- Escribe en español claro.
- NO agregues nada fuera del JSON.
- Respeta los rangos de palabras y cantidades indicados.

Transcripción:
--------------------------
{transcript}
--------------------------
""".strip()

def build_chunk_summary_prompt(chunk_text: str, idx: int, total: int, video_name: str) -> str:
    # Para fragmentos, pedimos un resumen “denso” (ayuda al consolidado)
    return f"""
Estás ayudando a resumir una clase larga de video.

Este es el fragmento {idx}/{total} de la transcripción de la clase "{video_name}".

Devuelve SOLO un objeto JSON válido con esta estructura:

{{
  "fragmento": {idx},
  "resumen_fragmento": "120-180 palabras. Explica qué se enseñó y cómo, con el mayor detalle útil.",
  "puntos_clave_fragmento": ["6-10 bullets con ideas accionables / definiciones / pasos"]
}}

Reglas:
- JSON válido (comillas dobles).
- Sin texto adicional fuera del JSON.

Transcripción del fragmento:
----------------------------
{chunk_text}
----------------------------
""".strip()


# ================== CHUNKING ==================

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + max_chars)
        cut = text.rfind(".", start, end)
        if cut == -1 or cut <= start + int(max_chars * 0.6):
            cut = end
        else:
            cut = cut + 1
        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        start = cut

    return chunks


# ================== RESUMEN GLOBAL ==================

def summarize_transcript_with_ollama(transcript: str, video_name: str) -> Dict[str, Any]:
    transcript = (transcript or "").strip()
    if not transcript:
        return normalize_summary_json({}, video_name)

    # Primer chunking
    chunks = chunk_text(transcript, max_chars=MAX_CHARS_PER_CHUNK)

    # Si quedan demasiados chunks, hacemos chunks más grandes para no demorar horas
    if len(chunks) > MAX_CHUNKS_HARD_LIMIT:
        log(f"⚠️ Muchos fragmentos ({len(chunks)}). Aumentando tamaño de chunk para acelerar...")
        bigger = min(20000, MAX_CHARS_PER_CHUNK * 3)
        chunks = chunk_text(transcript, max_chars=bigger)

    log(f"🧩 {video_name}: {len(chunks)} fragmentos")

    # Si hay un solo fragmento: resumen directo
    if len(chunks) == 1:
        t0 = time.time()
        prompt = build_summary_prompt_full(chunks[0], video_name)
        j = call_ollama_json(prompt)
        j = normalize_summary_json(j, video_name)
        log(f"✅ Resumen (1 paso) listo | {(time.time()-t0)/60:.1f} min")
        return j

    # Resumen por fragmentos
    fragment_summaries: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks, start=1):
        log(f"   ↳ Ollama fragmento {i}/{len(chunks)} ...")
        prompt = build_chunk_summary_prompt(chunk, i, len(chunks), video_name)
        frag = call_ollama_json(prompt)
        if not isinstance(frag, dict):
            frag = {"fragmento": i, "resumen_fragmento": "", "puntos_clave_fragmento": []}
        fragment_summaries.append(frag)

    # Consolidación final
    resumenes_txt = []
    for frag in fragment_summaries:
        num = frag.get("fragmento")
        r = frag.get("resumen_fragmento", "")
        pts = frag.get("puntos_clave_fragmento", [])
        resumenes_txt.append(f"Fragmento {num}:\nResumen: {r}\nPuntos clave: {pts}\n")

    texto_para_resumen_final = "\n\n".join(resumenes_txt)

    gmin, gmax = RESUMEN_GENERAL_PALABRAS
    emin, emax = RESUMEN_ESTUDIO_PALABRAS
    pmin, pmax = PUNTOS_CLAVE_CANTIDAD
    tmin, tmax = TEMAS_PRINCIPALES_CANTIDAD
    glmin, glmax = GLOSARIO_CANTIDAD
    qmin, qmax = PREGUNTAS_REPASO_CANTIDAD

    prompt_final = f"""
Eres un asistente experto en educación que genera apuntes para estudiar a partir de resúmenes parciales.

Se te dará una serie de resúmenes por fragmento de la clase "{video_name}".
Con esa información, genera un único JSON con esta estructura:

{{
  "video": "{video_name}",
  "resumen_general": "Resumen rápido de {gmin}-{gmax} palabras (1 párrafo).",
  "resumen_estudio": "Apuntes para estudiar de {emin}-{emax} palabras, con subtítulos y viñetas cuando aplique. Incluye: (1) qué se explicó, (2) pasos/procesos, (3) ejemplos si aparecen, (4) conclusiones.",
  "puntos_clave": ["{pmin}-{pmax} bullets, cada bullet 10-18 palabras aprox."],
  "temas_principales": ["{tmin}-{tmax} temas (frases cortas)."],
  "conceptos_importantes": ["lista de conceptos importantes (solo nombres)."],
  "glosario": [{{"termino":"...","definicion":"definición corta 1-2 líneas"}}],  // {glmin}-{glmax}
  "preguntas_repaso": [{{"pregunta":"...","respuesta_corta":"..."}}],            // {qmin}-{qmax}
  "tareas_o_recomendaciones": ["tareas o recomendaciones; si no hay, []"]
}}

Reglas:
- Usa SOLO la información de los resúmenes de fragmento.
- El JSON debe ser válido.
- Todo en español.
- Respeta los rangos de palabras y cantidades indicados.
- NO agregues texto fuera del JSON.

Resúmenes de fragmentos:
------------------------
{texto_para_resumen_final}
------------------------
""".strip()

    log("🧠 Consolidando resumen final ...")
    t0 = time.time()
    j_final = call_ollama_json(prompt_final)
    j_final = normalize_summary_json(j_final, video_name)
    log(f"✅ Resumen final listo | {(time.time()-t0)/60:.1f} min")
    return j_final


# ================== PIPELINE PRINCIPAL ==================

def procesar_videos_desde_s3():
    model = load_whisper_model()

    keys = list_s3_videos(S3_BUCKET, S3_PREFIX_VIDEOS)
    if not keys:
        log(f"⚠️ No se encontraron videos en s3://{S3_BUCKET}/{S3_PREFIX_VIDEOS}")
        return

    if LIMIT_VIDEOS is not None:
        keys = keys[:LIMIT_VIDEOS]

    log(f"🎬 Videos encontrados: {len(keys)}")

    for idx, key in enumerate(keys, start=1):
        video_name = Path(key).name
        stem = Path(key).stem

        txt_path = TRANSCRIPTS_DIR / f"{stem}.txt"
        json_out = JSON_DIR / f"{stem}_resumen.json"

        log("=" * 90)
        log(f"[{idx}/{len(keys)}] ▶️ {video_name}")

        # ✅ Si ya existe el JSON final, saltar todo
        if json_out.exists():
            log(f"➡️ Ya existe JSON: {json_out.name} | Salto.")
            continue

        video_path: Optional[Path] = None
        try:
            # ✅ Si ya existe TXT, no descargamos video
            if txt_path.exists():
                log(f"➡️ TXT ya existe: {txt_path.name} | No descargo video.")
            else:
                # Descargar + transcribir
                t0 = time.time()
                video_path = download_s3_video(S3_BUCKET, key, LOCAL_VIDEO_DIR)
                log(f"⏱️ Descarga: {(time.time()-t0)/60:.1f} min")

                transcribe_video(model, video_path, txt_path, force=False)

            transcript = read_text(txt_path)

            # Resumir
            t0 = time.time()
            resumen = summarize_transcript_with_ollama(transcript, video_name)
            log(f"⏱️ Resumen total: {(time.time()-t0)/60:.1f} min")

            # Guardar JSON (atómico)
            tmp = json_out.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(resumen, f, ensure_ascii=False, indent=2)
            tmp.replace(json_out)
            log(f"💾 JSON guardado: {json_out}")

            if UPLOAD_JSON_TO_S3:
                upload_json_to_s3(json_out, S3_BUCKET, S3_PREFIX_JSON)

        except Exception as e:
            log(f"❌ Error procesando {video_name}: {e}")

        finally:
            # 🧹 Borra video SOLO si se descargó en este ciclo
            if video_path and video_path.exists():
                try:
                    video_path.unlink()
                    log(f"🧹 Video local eliminado: {video_path.name}")
                except Exception as e:
                    log(f"⚠️ No se pudo borrar {video_path}: {e}")


def main():
    """CLI para procesar videos desde S3 (descarga → transcribe → resume → exporta JSON)."""
    import argparse

    parser = argparse.ArgumentParser(description="Resúmenes de videos (S3 + faster-whisper + Ollama).")
    parser.add_argument("--bucket", default=os.environ.get("S3_BUCKET", S3_BUCKET), help="Bucket S3 de entrada.")
    parser.add_argument("--prefix", default=os.environ.get("S3_PREFIX_VIDEOS", S3_PREFIX_VIDEOS), help="Prefijo S3 donde están los videos.")
    parser.add_argument("--upload-json", action="store_true", help="Subir JSON a S3 (requiere S3_PREFIX_JSON).")
    parser.add_argument("--local-video-dir", default=os.environ.get("LOCAL_VIDEO_DIR", str(LOCAL_VIDEO_DIR)), help="Carpeta local temporal de videos.")
    parser.add_argument("--transcripts-dir", default=os.environ.get("TRANSCRIPTS_DIR", str(TRANSCRIPTS_DIR)), help="Carpeta local de transcripciones.")
    parser.add_argument("--json-dir", default=os.environ.get("JSON_DIR", str(JSON_DIR)), help="Carpeta local de resúmenes JSON.")
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", MODEL_NAME), help="Modelo faster-whisper (tiny/base/small/medium/large-v3...).")
    parser.add_argument("--lang", default=os.environ.get("LANG", LANG), help="Idioma (ej. es).")
    parser.add_argument("--device", default=os.environ.get("DEVICE", DEVICE), help="Forzar device: cuda/cpu.")
    parser.add_argument("--compute-type", default=os.environ.get("COMPUTE_TYPE", COMPUTE_TYPE), help="compute_type: float16/int8/...")
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("WHISPER_BATCH_SIZE", str(WHISPER_BATCH_SIZE))), help="Batch size para Whisper.")
    parser.add_argument("--max-chars", type=int, default=int(os.environ.get("MAX_CHARS_PER_CHUNK", str(MAX_CHARS_PER_CHUNK))), help="Máx chars por chunk para Ollama.")
    parser.add_argument("--max-chunks", type=int, default=int(os.environ.get("MAX_CHUNKS_HARD_LIMIT", str(MAX_CHUNKS_HARD_LIMIT))), help="Máx chunks por video.")
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", OLLAMA_URL), help="URL Ollama.")
    parser.add_argument("--ollama-model", default=os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL), help="Modelo Ollama.")
    args = parser.parse_args()

    # aplicar overrides globales
    global S3_BUCKET, S3_PREFIX_VIDEOS, UPLOAD_JSON_TO_S3
    global LOCAL_VIDEO_DIR, TRANSCRIPTS_DIR, JSON_DIR
    global MODEL_NAME, LANG, DEVICE, COMPUTE_TYPE, WHISPER_BATCH_SIZE
    global MAX_CHARS_PER_CHUNK, MAX_CHUNKS_HARD_LIMIT, OLLAMA_URL, OLLAMA_MODEL

    S3_BUCKET = args.bucket
    S3_PREFIX_VIDEOS = args.prefix
    if args.upload_json:
        UPLOAD_JSON_TO_S3 = True

    LOCAL_VIDEO_DIR = Path(args.local_video_dir)
    TRANSCRIPTS_DIR = Path(args.transcripts_dir)
    JSON_DIR = Path(args.json_dir)

    MODEL_NAME = args.model
    LANG = args.lang
    DEVICE = args.device
    COMPUTE_TYPE = args.compute_type
    WHISPER_BATCH_SIZE = args.batch_size

    MAX_CHARS_PER_CHUNK = args.max_chars
    MAX_CHUNKS_HARD_LIMIT = args.max_chunks

    OLLAMA_URL = args.ollama_url
    OLLAMA_MODEL = args.ollama_model

    procesar_videos_desde_s3()


if __name__ == "__main__":
    main()
