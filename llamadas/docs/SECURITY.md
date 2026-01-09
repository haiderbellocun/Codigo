# Seguridad y privacidad (obligatorio para este repositorio)

Este proyecto procesa **audios** y **transcripciones** (información sensible). Sigue estas reglas:

## 1) Nunca subas a Git
- Audios (`.wav`, `.mp3`, `.wma`, etc.)
- Transcripciones (`.txt`)
- Archivos exportados (`.xlsx`, `.csv`, `.json`)
- Logs con PII
- Credenciales (SQL / rutas internas / usuarios / contraseñas)
- `.env` (solo `.env.example`)

## 2) Usa variables de entorno
- Configura credenciales con `.env` o variables del sistema.
- Mantén `.env` en `.gitignore`.

## 3) Rotación de credenciales
Si en algún momento subiste credenciales por error:
- **rota** contraseñas/keys inmediatamente
- considera limpiar historial git (ej. `git filter-repo`) si fue a un remoto

## 4) Minimiza PII
- Enmascara identificación/teléfono en outputs si no son necesarios.
- Restringe accesos a carpetas de audios y resultados.

## 5) Permisos
- Acceso mínimo necesario al share y a SQL.
- Evita credenciales compartidas sin control.

## 6) Cache LLM
- La carpeta `_ollama_cache` puede contener texto sensible (inputs/respuestas).
- Debe estar en `.gitignore` y almacenarse en ubicación segura.
