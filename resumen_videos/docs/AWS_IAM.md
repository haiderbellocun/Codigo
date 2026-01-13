# AWS IAM / Permisos S3 (mínimo)

Acciones típicas:
- `s3:ListBucket` (listar)
- `s3:GetObject` (descargar videos)
- (opcional) `s3:PutObject` (subir JSON)

Recomendado: usa AWS CLI profile o variables estándar (no hardcodear).
