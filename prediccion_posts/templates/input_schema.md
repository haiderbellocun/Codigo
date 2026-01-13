# Esquema de entrada (mínimo)

Columnas mínimas:

- `Origen` (string): identificador del perfil/marca (ej. nombre de empresa)
- `Post_Date` (fecha): puede ser datetime, string o serial de Excel
- `justificacion_post` (string): texto base del post (o campo equivalente)

Opcional:
- columnas numéricas de interacciones, por ejemplo:
  - `likes`, `comments`, `shares`, `reactions`
  - `interacciones`, `engagement`

El script intenta detectarlas automáticamente.
