# Documentación técnica

- `scanner.py`: encuentra archivos con `rglob(pattern)`
- `uploader.py`: sube en paralelo con `TransferConfig` y guarda `manifest.json`
- `--skip-if-exists`: hace `head_object` para saltar si ya existe en S3
