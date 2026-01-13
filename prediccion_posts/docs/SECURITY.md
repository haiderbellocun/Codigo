# Seguridad y privacidad

Este proyecto procesa texto y métricas de redes sociales (potencialmente PII).

## NO subir a Git
- Datasets reales (xlsx/csv) con información interna
- Outputs (json) con datos sensibles
- `.env` con credenciales/rutas
- Logs con identificadores personales

## Recomendaciones
- Enmascarar correos/teléfonos si aparecen en texto.
- Mantener outputs en carpetas seguras con acceso controlado.
- Si por error subiste credenciales, rótalas inmediatamente.
