# Escucha Social  – Clasificación de Comentarios y Posts → df_sql listo para SQL

Este repo contiene un pipeline de **escucha social** que toma un dataset (Excel/CSV) con publicaciones y/o comentarios,
usa **Ollama local** para clasificar, y exporta un Excel con:

- `Data_Clasificada`: dataset completo con columnas nuevas
- `SQL_READY`: `df_sql` con el **schema** listo para insertar en tu tabla
- `Ranking_Productos`: ranking de productos/ofertas detectadas (si aplica)
- `Temas`: distribución de temas (si aplica)

Incluye:
- Notebook original: `escucha_social.ipynb`
- Script ejecutable: `src/escucha_social.py`



---

## Estructura

```text
.
├─ escucha_social.ipynb
├─ src/
│  ├─ escucha_social.py
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
│  └─ run.sh
├─ templates/
│  └─ input_schema.md
└─ legacy/
   └─ arregla_otros.ipynb
```

---

## Requisitos

- Python 3.10+
- Ollama corriendo en tu PC (por defecto `http://localhost:11434`)
  - Modelo sugerido: `qwen2.5:7b-instruct`

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

---

## Configuración

Copia y ajusta:

```bash
copy .env.example .env
```

Variables importantes:
- `INPUT_PATH`: ruta al Excel/CSV
- `INPUT_SHEET`: hoja (0 o nombre)
- `OLLAMA_URL`, `MODEL`
- `EXPORT_XLSX`: salida

---

## Ejecutar (script)

```bash
python src/escucha_social.py --input "C:\ruta\entrada.xlsx" --export "salida.xlsx"
```

O con scripts:
- Windows: `scripts\run.ps1`
- Linux/Mac: `bash scripts/run.sh`

---

## Columnas esperadas (mínimas)

El pipeline usa por defecto:
- `textoComentario` (comentario) **o** `Comentario` si ya existe
- `Post` (texto del post)
- `Fecha del comentario` (fecha/relativo)

Ver detalle en `templates/input_schema.md`.

---

## Documentación

- Técnica: `docs/DOCUMENTATION.md`
- Seguridad: `docs/SECURITY.md`
- Cumplimiento (ToS/privacidad): `docs/COMPLIANCE.md`
