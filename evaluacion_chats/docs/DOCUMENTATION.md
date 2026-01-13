# Documentación técnica – Evaluación de chats

## 1) Flujo

1. **Carga**: Excel/CSV (`load_input`)
2. **Limpieza**:
   - parsea turnos por speaker
   - elimina speakers tipo bot (*CUNDigital*, *Channel User*, etc.)
   - normaliza texto (acentos, signos, espacios)
3. **Extracción de keywords**:
   - diccionarios por categoría → compila regex → cuenta ocurrencias
   - deriva señales para `puntaje` y `efectiva`
4. **Sentimiento**:
   - `TextBlob(p).sentiment.polarity` → etiqueta `positivo/neutro/negativo`
5. **Cédula (opcional)**:
   - consulta `dbo.Planta_Activa` en SQL Server
   - hace join por correo (`box_mail`)

## 2) Inputs mínimos

La columna exacta puede variar; el script trabaja sobre una columna de transcripción (texto).
Si tu archivo usa otro nombre, ajusta el código donde se llama `limpiar_df4()`.

Ver: `templates/input_schema.md`.

## 3) Outputs

- Excel/CSV con:
  - transcripción limpia
  - conteos por categorías
  - sentimiento
  - puntaje/efectiva
  - cédula (si aplica)

## 4) Troubleshooting

### TextBlob/NLTK error (resource not found)
Ejecuta:
```bash
python -m textblob.download_corpora
```

### Error de conexión SQL
- verifica ODBC Driver instalado
- si usas `SQL_TRUSTED=true`, debes estar en dominio / tener permisos
- si usas usuario/clave, completa `SQL_USER` y `SQL_PASSWORD` en `.env`
