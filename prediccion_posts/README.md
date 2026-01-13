# Predicción de posts (tendencias) – Escucha Social

Pipeline para **predecir temas/tendencias de publicaciones** por intervalos (ej. semanas de un mes)
a partir de un histórico de posts, usando **Ollama local** para generar:

- temas por red (Instagram, Facebook, LinkedIn, TikTok, YouTube)
- hashtags sugeridos
- palabras clave SEO (5)
- recomendaciones gráficas (4 bloques)
- (opcional) rango de interacciones estimadas

Incluye:
- Notebook original: `tendencia.ipynb`
- Script ejecutable: `src/predict_posts.py`



---

## Estructura

```text
.
├─ tendencia.ipynb
├─ src/
│  ├─ predict_posts.py
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
│  ├─ input_schema.md
│  └─ intervals_example.json
└─ legacy/
   └─ tendencia.ipynb
```

---

## Requisitos

- Python 3.10+
- Ollama corriendo localmente (default: `http://localhost:11434`)
  - Modelo recomendado: `qwen2.5:7b-instruct`
- (Opcional) SQL Server: ODBC Driver 17/18 si cargas con `--sql`

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

Copia el ejemplo:

```bash
copy .env.example .env
```

Ajusta `INPUT_PATH` y (si aplica) las variables de SQL.

---

## Ejecutar

### 1) Desde archivo (Excel/CSV)

```bash
python src/predict_posts.py --input "C:\ruta\historico.xlsx" --export-json "predicciones_posts.json"
```

### 2) Con intervalos personalizados

```bash
python src/predict_posts.py --input "C:\ruta\historico.xlsx" --intervals templates\intervals_example.json
```

### 3) Desde SQL Server (opcional)

```bash
python src/predict_posts.py --sql --export-json predicciones_posts.json
```

---

## Entradas esperadas

Mínimo (columnas):
- `Origen`
- `Post_Date` (fecha)
- `justificacion_post` (texto del post o texto base del post)

Opcional:
- columnas numéricas de interacción (likes, comments, shares, etc.)  
  El script intenta detectarlas y construir un baseline.

Ver detalle: `templates/input_schema.md`.

---

## Documentación

- Técnica: `docs/DOCUMENTATION.md`
- Seguridad/PII: `docs/SECURITY.md`
- Cumplimiento/ToS: `docs/COMPLIANCE.md`
