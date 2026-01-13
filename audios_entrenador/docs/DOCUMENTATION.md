# Documentación técnica – Audios Entrenador

## Scripts

### `src/download_audios.py`
- Fuente: CSV/Excel (call_id, recording_url) o SQL (tabla `dbo.vapi_entrenador`)
- Salida: `inputs/audios/<call_id>.<ext>`

### `src/transcribe_audios.py` (opcional)
- Entrada: audios en `inputs/audios`
- Salida: transcripciones en `inputs/txt/<call_id>.txt`
- GPU si está disponible; CPU si no.

### `src/evaluar_txt.py`
- Entrada: `.txt` en `INPUT_TXT_DIR`
- Cruce meta: por `call_id`
- Salida: Excel/CSV en `OUTPUT_DIR`

## Troubleshooting
- ODBC: instala “ODBC Driver 17/18 for SQL Server”.
- TextBlob: `python -m textblob.download_corpora`
- Whisper GPU: valida que `torch.cuda.is_available()` sea `True`.
