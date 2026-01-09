\
# Seguridad y privacidad

Este proyecto trabaja con **audios** y **transcripciones** (datos sensibles).

## NO subir a Git
- Audios (wav/mp3/etc)
- Transcripciones (txt)
- Outputs (json/xlsx/csv)
- `.env` (solo `.env.example`)
- Keys / passwords / tokens

## PII
- No versionar keys que contengan correos reales si el repo es público.
- Evita imprimir PII en logs (o minimízalo).

## Rotación
Si alguna credencial se subió por error:
1) rota contraseñas/keys
2) limpia historial del repo si llegó a remoto
