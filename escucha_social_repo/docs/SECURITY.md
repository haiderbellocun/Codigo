# Seguridad y privacidad

Este proyecto procesa texto de redes sociales (potencialmente PII).

## NO subir a Git
- Datasets reales (xlsx/csv)
- Exports (xlsx/csv/json)
- Logs con PII
- `.env`

## Recomendado
- Enmascarar identificadores (teléfonos/correos/IDs) si aparecen en texto.
- Controlar acceso a carpetas de entrada/salida.
- Mantener prompts y outputs en almacenamiento seguro.
