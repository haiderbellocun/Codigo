# Documentación técnica – Escucha Social (Ollama)

## 1) Qué hace

1. Normaliza el dataset de entrada (posts + comentarios).
2. Ejecuta clasificación con Ollama en paralelo:
   - Comentarios: sentimiento, tipo, tema, clase + justificación.
   - Posts: tema_post, clase_post, producto/oferta detectada + justificación.
3. Enriquecimiento:
   - Reglas heurísticas para corregir casos (ej. miedo vs queja).
   - Deriva `tipo` final y señales auxiliares.
4. Genera:
   - `df_final`: dataset enriquecido.
   - `df_sql`: esquema alineado con la tabla SQL (sin columnas extra no soportadas).
5. Exporta un Excel multi-hoja.

## 2) Entradas

Archivo Excel/CSV con columnas mínimas:
- Comentario: `textoComentario` (o `Comentario`)
- Post: `Post`
- Fecha: `Fecha del comentario`

> Si tu dataset tiene nombres distintos, ajusta las variables `COL_COMENT_IN`, `COL_POST_IN`, `COL_FECHA_IN` en `src/escucha_social.py`.

## 3) Ollama

Variables:
- `OLLAMA_URL` (default: http://localhost:11434)
- `MODEL` (default: qwen2.5:7b-instruct)
- `MAX_WORKERS` (paralelismo)

Recomendaciones:
- `temperature=0` para clasificaciones consistentes.
- Limitar concurrencia si hay timeouts (baja `MAX_WORKERS`).

## 4) Outputs

- `EXPORT_XLSX`:
  - `Data_Clasificada`
  - `SQL_READY`
  - `Ranking_Productos` (si aplica)
  - `Temas` (si aplica)

## 5) Troubleshooting

- Ollama no responde:
  - valida `/api/tags`
  - revisa el modelo instalado
- Excel bloqueado:
  - cierra el archivo antes de exportar
- Columnas no encontradas:
  - revisa nombres exactos y tildes
  - ajusta `COL_*` en el script
