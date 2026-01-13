# Resúmenes de videos (S3 → Whisper → Ollama)

Automatiza:

- **Listar videos en S3**
- **Descargar** a una carpeta local temporal
- **Transcribir** con `faster-whisper` (GPU si está disponible)
- **Resumir** con **Ollama** en JSON estructurado
- Guardar transcripción y JSON localmente
- (Opcional) **Subir JSON a S3**

Incluye:
- Notebook: `resumen_video.ipynb`
- Script: `src/resumen_videos.py`

> ⚠️ No subas videos/transcripciones/outputs a Git.

---

## Estructura

```text
.
├─ resumen_video.ipynb
├─ src/
│  ├─ resumen_videos.py
│  └─ __init__.py
├─ requirements.txt
├─ requirements-dev.txt
├─ .gitignore
├─ .env.example
├─ docs/
│  ├─ DOCUMENTATION.md
│  ├─ AWS_IAM.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ run.ps1
│  └─ run.sh
├─ templates/
│  ├─ output_schema.json
│  └─ ollama_prompt.md
└─ outputs/
```

---

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuración

```bash
copy .env.example .env
```

---

## Ejecutar

```bash
python src/resumen_videos.py --bucket cun-transcribe-five9 --prefix "Videos_clase_Profesores/video_12_04_25a/"
```

Subir JSON a S3:
```bash
python src/resumen_videos.py --upload-json
```
