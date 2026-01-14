\
# Documentación técnica – Lambda “Transcribe Starter”

## 1) Qué hace

- Se ejecuta con eventos `ObjectCreated` de S3.
- Toma `bucket` y `key` del audio.
- Extrae un correo desde el `key`.
- Consulta un Excel de aprobados en S3 (cacheado en warm starts).
- Si el correo está aprobado:
  - Inicia un job de AWS Transcribe.
  - Escribe resultados en `s3://OUT_BUCKET/OUT_PREFIX/YYYY-MM-DD/Grabaciones/`

## 2) Formato del S3 Key esperado

El key debe contener un correo en cualquier parte, por ejemplo:

- `Grabaciones/agent=juan/juan.perez@cun.edu.co/llamada_123.wav`
- `ventas/2026-01-01/ana@empresa.com/audio.mp3`

Regex por defecto: `[\w.+-]+@[\w-]+\.[\w.-]+`  
Puedes cambiarlo con `EMAIL_REGEX`.

## 3) Excel de aprobados (en S3)

- Debe contener una columna `correo` o `email` (configurable con `EMAIL_COLUMNS`).
- La hoja:
  - por defecto toma la primera
  - o la indicada en `APPROVED_SHEET`

La función descarga el Excel con `s3:GetObject` y lo lee con `openpyxl`.

## 4) AWS Transcribe

La función llama a `StartTranscriptionJob` con:

- `MediaFileUri`: `s3://input-bucket/key`
- `OutputBucketName`: `OUT_BUCKET`
- `OutputKey`: `OUT_PREFIX/YYYY-MM-DD/Grabaciones/`
- `IdentifyLanguage=True` si `LANGUAGE=auto`; si no, usa `LanguageCode`.

### Speaker labels
Si `SPEAKERS >= 2`, añade `Settings.ShowSpeakerLabels=True` y `MaxSpeakerLabels=SPEAKERS`.

## 5) Importante: permisos S3 para el servicio Transcribe

Lambda **no** copia el audio ni escribe la salida.
Transcribe lee y escribe en S3 con su identidad de servicio.

Debes:
- Permitir que `transcribe.amazonaws.com` lea el bucket de entrada
- Permitir que escriba en el bucket de salida

Ver `docs/IAM.md` para ejemplo de bucket policy.

## 6) Manejo de errores

- Si falta correo en el key → se omite.
- Si correo no está aprobado → se omite.
- Si el job ya existe → registra `already_exists`.
- Otras excepciones → se reportan en `skipped`.

La respuesta HTTP devuelve un JSON con `processed` y `skipped`.

## 7) Performance / costos

- El Excel se cachea por container (warm starts).
- Se refresca si cambia el ETag (head_object).
- Recomendación:
  - Mantén el Excel pequeño (solo columna correo/email).
  - Usa filtros S3 (prefix/suffix) para evitar disparos innecesarios.

## 8) Buckets existentes

Si tu bucket de entrada ya existe:
- crea/ajusta la notificación de eventos S3 hacia esta Lambda (Console o IaC)
- si usas SAM, puedes desplegar la Lambda sin crear bucket y luego configurar el trigger manualmente
