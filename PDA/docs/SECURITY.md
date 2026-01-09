# Seguridad y privacidad

Este scraper procesa **reportes PDF** y metadatos (potencialmente PII).

## NO subir a Git
- PDFs descargados
- logs con datos personales
- `.env` con rutas/variables internas

## Recomendaciones
- Minimiza lo que imprimes en consola (evita nombres/correos completos).
- Restringe permisos a `DOWNLOAD_DIR` y `SHARED_DIR`.
- Si usas OneDrive/Drive, valida quién tiene acceso.

## Incidentes
Si accidentalmente subiste PII o rutas internas:
- elimina el commit
- rota credenciales si hubo exposición
- limpia el historial si se publicó en remoto
