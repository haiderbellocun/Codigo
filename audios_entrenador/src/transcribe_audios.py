# !pip install faster-whisper torch --upgrade
import os
import time
import math
import threading
from queue import Queue
from pathlib import Path
from faster_whisper import WhisperModel
import torch

from dotenv import load_dotenv

load_dotenv()
# ───── RUTAS (AJUSTA) ───────────────────────────────────────────────────────────
INPUT_ROOT = Path(os.environ.get("AUDIO_DIR", r"inputs\audios"))
OUTPUT_DIR = Path(os.environ.get("TRANSCRIPTS_DIR", r"inputs\txt"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma"}

# ───── DETECCIÓN GPU / CONFIG ──────────────────────────────────────────────────
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
# Nota: si no hay CUDA, el script correrá en CPU (más lento).
torch.set_float32_matmul_precision("medium")

MODEL_NAME   = os.environ.get("WHISPER_MODEL", "medium")
COMPUTE_TYPE = "float16"           # FP16 en GPU = rápido
BEAM_SIZE    = 1                   # 1 = más veloz
LANG         = "es"

# Estimar cuántas instancias caben en 12 GB (aprox medium FP16 ~4-5 GB)
if DEVICE == "cuda":
    free, total = torch.cuda.mem_get_info()
    free_gb  = free / (1024**3)
    total_gb = total / (1024**3)

    # Máximo 3 modelos; si VRAM libre <7.5 GB, usa 2; si >=11 GB, prueba 3
    MAX_MODELS = int(os.environ.get("MAX_MODELS", "0")) or (3 if free_gb >= 11 else (2 if free_gb >= 7.5 else 1))
    print(f"GPU VRAM libre: {free_gb:.1f} GB / {total_gb:.1f} GB → instancias: {MAX_MODELS}")
else:
    MAX_MODELS = int(os.environ.get("MAX_MODELS", "1"))

# ───── UTILIDADES ───────────────────────────────────────────────────────────────
def gather_audio_files(root: Path):
    for dp, _, files in os.walk(root):
        for f in files:
            if Path(f).suffix.lower() in AUDIO_EXTS:
                yield Path(dp) / f

def transcribe_with_model(model: WhisperModel, audio_path: Path, out_dir: Path) -> str:
    out_path = out_dir / (audio_path.stem + ".txt")
    if out_path.exists():
        return f"➡️ {audio_path.name} (ya existe)"
    segments, _ = model.transcribe(
        str(audio_path),
        language=LANG,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400),
        beam_size=BEAM_SIZE,
        best_of=1,
        temperature=0.0,
        without_timestamps=True,
        word_timestamps=False,
        condition_on_previous_text=False,
    )
    text = "".join(s.text for s in segments).strip()
    out_path.write_text(text, encoding="utf-8")
    return f"✔️ {audio_path.name} ({len(text)} chars)"

# ───── POOL DE WORKERS (CADA UNO CON SU MODELO) ────────────────────────────────
def worker_loop(worker_id: int, q: Queue, results: list, lock: threading.Lock):
    # Cada worker carga SU propia instancia del modelo (mantiene GPU ocupada)
    model = WhisperModel(
        MODEL_NAME,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        device_index=0,      # cambia si usas otra GPU
        num_workers=1        # hilos internos del modelo (no subir en GPU)
    )
    while True:
        audio_path = q.get()
        if audio_path is None:
            q.task_done()
            break
        try:
            msg = transcribe_with_model(model, audio_path, OUTPUT_DIR)
        except Exception as e:
            msg = f"❌ {audio_path.name} → {e}"
        with lock:
            results.append(msg)
            print(msg)
        q.task_done()

def main():
    files = list(gather_audio_files(INPUT_ROOT))
    total = len(files)
    if total == 0:
        print("⚠️ No se encontraron audios.")
        return

    # Ordenar por tamaño descendente para balancear carga (los largos primero)
    files.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)

    print(f"🗂️  Audios: {total}  ·  Workers(modelos): {MAX_MODELS}\n")

    q = Queue(maxsize=MAX_MODELS * 4)  # prefetched items
    results, lock = [], threading.Lock()
    threads = []

    # Lanzar N workers (cada uno con su modelo)
    for i in range(MAX_MODELS):
        t = threading.Thread(target=worker_loop, args=(i, q, results, lock), daemon=True)
        t.start()
        threads.append(t)

    # Ingesta en la cola con barra de progreso simple
    start = time.time()
    for idx, f in enumerate(files, 1):
        q.put(f)
        if idx % 50 == 0:
            elapsed = time.time() - start
            done = len(results)
            if done:
                rate = done / elapsed               # archivos/seg
                eta  = (total - done) / rate
                print(f"⏳ {done}/{total} · {rate*60:.1f} a/min · ETA {eta/60:.1f} min")

    # Señales de fin
    for _ in range(MAX_MODELS):
        q.put(None)

    q.join()  # esperar a que terminen
    dur = time.time() - start
    print(f"\n🏁 Listo: {len(results)}/{total} en {dur/60:.1f} min "
          f"({(total/(dur/60)):0.1f} audios/min aprox)")

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Transcribe audios (entrenador) con faster-whisper → .txt")
    parser.add_argument("--audio-dir", default=os.environ.get("AUDIO_DIR", str(INPUT_ROOT)), help="Carpeta con audios.")
    parser.add_argument("--out-dir", default=os.environ.get("TRANSCRIPTS_DIR", str(OUTPUT_DIR)), help="Carpeta de salida .txt")
    parser.add_argument("--model", default=os.environ.get("WHISPER_MODEL", MODEL_NAME), help="Modelo Whisper (tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default=os.environ.get("DEVICE", DEVICE), help="cuda/cpu (auto por defecto)")
    parser.add_argument("--compute-type", default=os.environ.get("COMPUTE_TYPE", COMPUTE_TYPE), help="float16/int8/...")
    parser.add_argument("--max-models", type=int, default=int(os.environ.get("MAX_MODELS", str(MAX_MODELS))), help="Instancias del modelo (GPU) o workers (CPU).")
    args = parser.parse_args()

    global INPUT_ROOT, OUTPUT_DIR, MODEL_NAME, DEVICE, COMPUTE_TYPE, MAX_MODELS
    INPUT_ROOT = Path(args.audio_dir)
    OUTPUT_DIR = Path(args.out_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_NAME = args.model
    DEVICE = args.device
    COMPUTE_TYPE = args.compute_type
    MAX_MODELS = args.max_models

    main()

if __name__ == "__main__":
    cli()
