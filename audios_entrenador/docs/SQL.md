# SQL – Metadatos de audios entrenador

Tabla esperada: `dbo.vapi_entrenador`

Campos usados:
- `call_id`
- `number` (→ `numero_vapi`)
- `started_at` (→ `fecha`)
- `recording_url`

Filtros opcionales:
- `META_DESDE` (incluye)
- `META_HASTA_EXC` (excluye)

Conexión:
- `SQL_TRUSTED=true` (recomendado) o `SQL_USER/SQL_PASSWORD`
- `SQL_DRIVER` típico: ODBC Driver 17/18
