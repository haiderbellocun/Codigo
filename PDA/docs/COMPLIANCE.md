# Cumplimiento y buenas prácticas de scraping

Este proyecto automatiza acciones en una web.

## Antes de usar
- Confirma que tienes autorización (política interna / owner del sistema).
- Revisa Términos de Servicio y políticas de uso de la plataforma.
- Respeta límites de acceso y privacidad.

## Buenas prácticas
- Usa **rate limiting**: pausas razonables entre acciones (`PAUSE_BETWEEN_ROWS`).
- Evita paralelizar en exceso.
- Mantén un perfil de navegador dedicado.
- No recolectes más datos de los necesarios.
- Guarda outputs en carpetas seguras con acceso controlado.

## Riesgos
- Cambios de UI pueden romper XPATHs.
- Sesión expirada / MFA puede requerir intervención manual.
- Descargas automatizadas pueden ser bloqueadas por políticas del navegador.
