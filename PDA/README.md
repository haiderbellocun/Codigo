# Scraper Selenium – Descarga/Generación de Reportes (PDA / People Management)

Este repositorio contiene un **scraper con Selenium (Chrome)** para automatizar la **generación y descarga**
de reportes desde una página web (en tu caso, el flujo de **People Management → Reporte PDA**).

✅ Incluye:
- Notebook original: `descarga.ipynb`
- Script ejecutable: `src/scraper.py` (configurable por variables de entorno / CLI)
- Deduplicación multi-equipo con índice compartido (`processed_index.json`) y búsqueda de PDFs existentes
- Scripts para lanzar Chrome con **remote debugging port** (recomendado)


Revisa `docs/COMPLIANCE.md`.

---

## Estructura

```text
.
├─ descarga.ipynb
├─ src/
│  ├─ scraper.py
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
│  ├─ start_chrome_debug.ps1
│  ├─ start_chrome_debug.sh
│  └─ run_scraper.ps1
└─ legacy/
   └─ descarga.ipynb
```

---

## Requisitos

- Python 3.10+ recomendado
- Google Chrome instalado
- Acceso a la página (y permisos de tu usuario)
- En Windows: permisos sobre la carpeta de descargas y carpeta compartida

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

Edita `.env` con tus rutas reales:

- `DOWNLOAD_DIR`: donde Chrome guardará los PDFs
- `SHARED_DIR`: carpeta compartida para consolidación e índice

> `.env` **NO** se sube a Git (está en `.gitignore`).

---

## Ejecución (recomendada): Chrome ya abierto con DevTools

### 1) Abrir Chrome con remote debugging
**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_chrome_debug.ps1
```

**Linux/Mac:**
```bash
bash scripts/start_chrome_debug.sh
```

1. Se abrirá un Chrome con un perfil dedicado.
2. Inicia sesión manualmente en la página.
3. Deja el navegador abierto.

### 2) Ejecutar el scraper
**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_scraper.ps1
```

O directo con Python:

```bash
python src/scraper.py --max-rows 50
```

---

## Variables principales

- `LIST_URL`: URL de la lista principal
- `DOWNLOAD_DIR`: carpeta local donde Chrome descarga
- `SHARED_DIR`: carpeta compartida
- `DEBUG_ADDR`: `127.0.0.1:9222`
- `WAIT`: timeout base en segundos
- `PREFERRED_PAGE_SIZE`: items por página
- `MAX_ROWS`: límite de filas (0 = todas)

---

## Documentación

- Guía técnica y troubleshooting: `docs/DOCUMENTATION.md`
- Seguridad/PII: `docs/SECURITY.md`
- Buenas prácticas de scraping y cumplimiento: `docs/COMPLIANCE.md`
