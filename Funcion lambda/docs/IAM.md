\
# IAM y Bucket Policies (AWS Transcribe + S3)

## 1) Permisos mínimos para el rol de Lambda

La Lambda necesita:

- `s3:GetObject` sobre el Excel de aprobados (`BASE_VENTAS_BUCKET/BASE_VENTAS_KEY`)
- `transcribe:StartTranscriptionJob`
- Logs (CloudWatch)

Ejemplo (Statement):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadApprovedExcel",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::MI_BUCKET_CONFIG/path/aprobados.xlsx"
    },
    {
      "Sid": "StartTranscribe",
      "Effect": "Allow",
      "Action": ["transcribe:StartTranscriptionJob"],
      "Resource": "*"
    }
  ]
}
```

> Nota: `Resource:"*"` para Transcribe es común porque el ARN del job no existe antes de crearlo.

---

## 2) Bucket policy para que Transcribe lea el audio (bucket de entrada)

En el bucket donde llegan los audios (INPUT BUCKET), agrega una policy que permita al servicio Transcribe leer:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowTranscribeReadInput",
      "Effect": "Allow",
      "Principal": { "Service": "transcribe.amazonaws.com" },
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::MI_INPUT_BUCKET/*"
    }
  ]
}
```

---

## 3) Bucket policy para que Transcribe escriba la salida (bucket de salida)

En el OUT_BUCKET:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowTranscribeWriteOutput",
      "Effect": "Allow",
      "Principal": { "Service": "transcribe.amazonaws.com" },
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::MI_OUT_BUCKET/*"
    }
  ]
}
```

---

## 4) Notas

- Si tus buckets usan KMS, necesitas permisos adicionales (Encrypt/Decrypt).
- Si restringes por prefix, reemplaza `/*` por `/<prefijo>/*`.
