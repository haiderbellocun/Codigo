# Esquema de entrada (mínimo)

El script espera al menos:

- `textoComentario` (comentario)  **o** `Comentario`
- `Post` (texto del post)
- `Fecha del comentario` (fecha o relativo)

## Ejemplo (CSV)
```csv
textoComentario,Post,Fecha del comentario
"Me encantó la atención","Inscríbete hoy en...", "2026-01-10"
"Qué mala experiencia","Becas disponibles...", "2026-01-11"
```

## Si tus columnas tienen otros nombres
Edita en `src/escucha_social.py`:

- `COL_COMENT_IN`
- `COL_POST_IN`
- `COL_FECHA_IN`
