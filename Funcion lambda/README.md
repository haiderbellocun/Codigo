\
# AWS Lambda – Disparador de AWS Transcribe por S3

Esta función **AWS Lambda (Python)** se dispara cuando llega un archivo de audio a un bucket S3.
Luego:

1. Extrae un **correo** desde el `key` del objeto S3 (regex).
2. Valida si ese correo está en una **lista de aprobados** guardada en un **Excel en S3**.
3. Si está aprobado, inicia un **AWS Transcribe job**.
4. AWS Transcribe escribe su salida en:  
   `s3://OUT_BUCKET/OUT_PREFIX/YYYY-MM-DD/Grabaciones/`



---

## Estructura

```text
.
├─ src/
│  ├─ app.py                  # lambda_handler
│  └─ __init__.py
├─ template.yaml              # AWS SAM (opcional)
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ .env.example
├─ events/
│  └─ s3_put.json             # evento de prueba
├─ docs/
│  ├─ DOCUMENTATION.md
│  ├─ IAM.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ package_zip.sh
│  └─ deploy_sam.sh
├─ tests/
│  └─ test_utils.py
└─ legacy/
   └─ lambda.py               # tu versión original (referencia)
```

---

## Variables de entorno

Obligatorias:
- `OUT_BUCKET`: bucket destino de salida de Transcribe
- `BASE_VENTAS_BUCKET`, `BASE_VENTAS_KEY`: ubicación del Excel con correos aprobados

Recomendadas:
- `OUT_PREFIX` (default: `txt/prue`)
- `LANGUAGE` (`auto` o un `LanguageCode` de Transcribe)
- `SPEAKERS` (>=2 habilita speaker labels)

Opcionales:
- `APPROVED_SHEET`, `EMAIL_COLUMNS`, `ALLOWED_EXTS`, `EMAIL_REGEX`

Ejemplo: ver `.env.example`.

---

## Instalación (para desarrollo local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -U pytest
```

---

## Empaquetar en ZIP (Lambda “zip deployment”)

```bash
bash scripts/package_zip.sh
```

Te genera: `dist/lambda.zip`

---

## Despliegue con AWS SAM (recomendado)

1) Instala SAM CLI y configura AWS credentials.  
2) Despliega:

```bash
bash scripts/deploy_sam.sh
```

> SAM crea recursos en tu cuenta (si usas el `template.yaml`).  
> Para buckets existentes, revisa la nota en `docs/DOCUMENTATION.md`.

---

## Prueba local rápida

Puedes validar funciones auxiliares con:

```bash
pytest -q
```

Para probar el handler, usa el evento de ejemplo:

- `events/s3_put.json`

En SAM:
```bash
sam local invoke TranscribeStarterFunction -e events/s3_put.json
```

---

## Documentación

- Técnica y flujo: `docs/DOCUMENTATION.md`
- IAM y bucket policies: `docs/IAM.md`
- Seguridad y PII: `docs/SECURITY.md`
