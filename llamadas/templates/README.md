# Plantillas / formatos esperados

Este repositorio **NO** versiona archivos reales con PII (audios, transcripciones, excels).
Aquí documentamos formatos esperados para que el pipeline sea reproducible.

## Audio
- Extensiones admitidas: `.wav`, `.mp3`, `.wma` (ajustable)
- Fuente: ruta compartida (Windows share) organizada por fecha/carpeta/asesor.

## SQL (si aplica)
El notebook consulta tablas internas (ej. para mapear correo/cedula o cargar plantilla).
Asegúrate de:
- tener ODBC Driver instalado
- credenciales por variables de entorno

## Output recomendado
- Excel final con `etiqueta_final` y columnas auxiliares.
- Si tu operación requiere integración con BD, mantén un esquema estable de columnas.
