# Esquema de entrada (guía)

El pipeline requiere un dataset con una columna de **transcripción** del chat.

Ejemplos comunes:
- `Transcripción`
- `Transcripcion`
- `Transcripción_limpia`
- o similar

Dentro de la transcripción se esperan líneas tipo:
```
#Asesor : Hola, ¿cómo estás?
#Cliente : Quiero información del programa...
```

Si tu formato difiere:
- ajusta el regex `SPEAKER_LINE_RX`
- o pre-procesa para estandarizar

Opcional (para cédula):
- una columna de correo del asesor (o un campo equivalente) que el script use para mapear contra `dbo.Planta_Activa.box_mail`.
