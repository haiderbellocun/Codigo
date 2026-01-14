# Evaluación de chats – Limpieza + Keywords + Sentimiento + (opcional) Cédula desde SQL

Este repositorio automatiza el análisis de conversaciones de chat:
- **Limpieza** de transcripción (remueve speakers bot como *CUNDigital/Channel User*, normaliza texto)
- **Extracción de keywords** por categorías (diccionarios/regex)
- **Sentimiento** (TextBlob)
- **Enriquecimiento opcional**: trae la **cédula** del asesor desde SQL Server (`dbo.Planta_Activa`, `box_mail → Identificacion`)
- Exporta un Excel/CSV listo para revisión o carga a SQL

Incluye:
- Notebook original: `chats.ipynb`
- Script ejecutable: `src/eval_chats.py`


Ver `docs/SECURITY.md`.

---

## Estructura

```text
.
├─ chats.ipynb
├─ src/
│  ├─ eval_chats.py
│  └─ __init__.py
├─ requirements.txt
├─ requirements-dev.txt
├─ .gitignore
├─ .env.example
├─ docs/
│  ├─ DOCUMENTATION.md
│  ├─ SECURITY.md
│  └─ COMPLIANCE.md
├─ scripts/
│  ├─ run.ps1
│  ├─ run.sh
│  └─ download_nltk.ps1
├─ templates/
│  └─ input_schema.md
├─ tests/
│  └─ test_smoke.py
└─ outputs/            # (vacía) carpeta de salida local
```

---

## Requisitos

- Python 3.10+
- Para SQL Server (si lo usas): **ODBC Driver 17/18** instalado
- Para sentimiento (TextBlob): descarga de corpora (una sola vez)

---

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
```

### Descargar corpora (TextBlob/NLTK)
```bash
python -m textblob.download_corpora
```

---

## Configuración

```bash
copy .env.example .env
```

Ajusta `INPUT_SRC` y `OUTPUT_PATH`.

Si quieres enriquecer con SQL, completa:
- `SQL_SERVER`, `SQL_DATABASE`
- `SQL_TRUSTED=true` (recomendado) o `SQL_USER/SQL_PASSWORD` si aplica

---

## Ejecución

```bash
python src/eval_chats.py --input "C:\ruta\chats.xlsx" --output "outputs\chats_evaluados.xlsx"
```

Sin SQL:
```bash
python src/eval_chats.py --input "C:\ruta\chats.xlsx" --no-sql
```

---

## Documentación

- Detalle técnico y troubleshooting: `docs/DOCUMENTATION.md`
- Seguridad/PII: `docs/SECURITY.md`
- Cumplimiento: `docs/COMPLIANCE.md`
