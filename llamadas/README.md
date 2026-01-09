# Proceso de llamadas (Copiar audios → Transcribir → Evaluar)

Pipeline en **Python/Jupyter** para automatizar el QA de llamadas:

1. **Copiar audios** desde una ruta compartida (Windows share) filtrando por fecha y asesor/carpeta.
2. **Transcribir** audios a **TXT** con **faster-whisper** (GPU/CPU).
3. **Evaluar** el texto:
   - Reglas/diccionarios (rápido, determinístico).
   - (Opcional) **LLM local (Ollama)** para casos “borderline” o cuando aporta valor.
4. **Exportar** un **Excel/CSV final** con etiquetas y campos auxiliares.

> ⚠️ Repositorio pensado para uso interno. **No subas credenciales ni PII** (nombres, teléfonos, correos, grabaciones).

---

## Estructura del repo

```text
.
├─ llamadas.ipynb
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ .env.example
├─ LICENSE
├─ CONTRIBUTING.md
├─ docs/
│  ├─ DOCUMENTATION.md
│  └─ SECURITY.md
├─ templates/
│  └─ README.md
└─ scripts/
   ├─ run_notebook.ps1
   └─ run_notebook.sh
```

---

## Requisitos

### Software
- Python 3.10+ recomendado
- **ODBC Driver 17/18 for SQL Server** (requerido por `pyodbc`)
- **ffmpeg** en el PATH (requerido para procesar audios en transcripción)
- (Opcional) **Ollama** corriendo localmente (por defecto: `http://localhost:11434`)

### Accesos
- Acceso a la **ruta compartida** donde están los audios (Windows share).
- Acceso al **SQL Server** (para consultas de plantilla/correos si aplica).

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

### Torch (GPU vs CPU)
`torch` depende de tu hardware. Si necesitas GPU (CUDA), instala la build compatible según tu CUDA.

---

## Configuración (recomendado con variables de entorno)

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example .env
```

> Si no usas `.env`, puedes exportar variables manualmente o editar las constantes dentro del notebook.

---

## Ejecución

### Opción A (recomendada): abrir y ejecutar el notebook
1) Abre `llamadas.ipynb` en VSCode/Jupyter  
2) Ejecuta las celdas en orden (Run All)

### Opción B: ejecutar el notebook desde consola
- **Linux/Mac**
```bash
bash scripts/run_notebook.sh
```

- **Windows PowerShell**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_notebook.ps1
```

---

## Salidas (outputs)

El notebook genera típicamente:
- Carpeta local con audios copiados (por fecha/cargo/asesor)
- Carpeta con **TXT** transcritos
- Archivo final: `*.xlsx` (o `*.csv` si falla Excel)
- Carpeta de cache: `OUTPUT_DIR/_ollama_cache`

---

## Documentación

- Documentación técnica completa: `docs/DOCUMENTATION.md`
- Buenas prácticas de seguridad: `docs/SECURITY.md`
