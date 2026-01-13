# Documentación técnica – Resúmenes de videos

## Flujo
1) Lista keys en S3 por prefijo y extensiones.
2) Descarga el video al disco.
3) Transcribe con Whisper (GPU/CPU).
4) Trocea en fragmentos (chunks) y resume cada fragmento.
5) Consolida un JSON final y lo guarda.
6) Elimina el video local.

## Configuración clave
- `MODEL_NAME`: tamaño whisper (medium/large-v3)
- `DEVICE`: auto, o forzar cuda/cpu
- `WHISPER_BATCH_SIZE`: sube si hay VRAM
- `MAX_CHARS_PER_CHUNK`: controla tamaño del prompt a Ollama
- `MAX_CHUNKS_HARD_LIMIT`: evita demasiados fragmentos

## Troubleshooting
- Ollama caído: revisa `OLLAMA_URL`.
- CUDA no detectada: valida drivers + torch CUDA + ctranslate2.
- Permisos S3: ver `AWS_IAM.md`.
