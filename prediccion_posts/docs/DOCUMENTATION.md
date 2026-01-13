# Documentación técnica – Predicción de posts (tendencias)

## 1) Objetivo

A partir de un histórico de publicaciones, construir señales de tendencia (por semana y por origen)
y luego pedir a un LLM local (Ollama) que proponga **temas y plan de contenido** por intervalos.

## 2) Flujo

1. Validación de columnas mínimas (`Origen`, `Post_Date`, `justificacion_post`).
2. Normalización de `Origen`.
3. Normalización de fechas (`Post_Date`).
4. Extracción de keywords por post.
5. Agregación por `Semana_Año` + `Origen`:
   - top keywords / temas recientes
   - (opcional) baseline de interacciones (P50/P75) si hay columnas numéricas
6. Llamado a Ollama:
   - /api/chat (principal)
   - fallback /api/generate si /api/chat falla
   - respuesta JSON estricta (cuando `intentar_schema=True`)
7. Resultado:
   - JSON con estructura por intervalos y por red.

## 3) Intervalos

Por defecto incluye intervalos para diciembre 2025 (en el script).
Puedes pasar un JSON personalizado:

```json
[
  {"inicio":"2026-02-01","fin":"2026-02-07"},
  {"inicio":"2026-02-08","fin":"2026-02-14"}
]
```

## 4) Troubleshooting

- Ollama no responde:
  - valida que `OLLAMA_BASE` esté activo (ej. `http://localhost:11434`)
  - baja el tamaño del prompt o usa un modelo más pequeño
  - sube `TIMEOUT`
- Respuesta no JSON:
  - usa `--no-schema` (más tolerante)
  - baja `temperature` en el código si quieres más consistencia
- Error con SQL:
  - verifica ODBC Driver y credenciales
