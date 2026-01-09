# Documentación técnica – Proceso de llamadas (CL Tiene)

Este documento describe el notebook **`llamadas.ipynb`** y su pipeline.

---

## 1. Objetivo

Automatizar un flujo de **QA de llamadas**:

1. **Copiar audios** desde una ruta compartida (Windows share) a una carpeta local por fecha.
2. **Transcribir** audio → texto (TXT) usando **faster-whisper** (GPU/CPU).
3. **Evaluación** del texto:
   - Reglas/diccionarios (detección de frases).
   - (Opcional) LLM local (**Ollama**) para mejorar casos ambiguos (“borderline”).
4. **Exportación** a Excel/CSV para análisis y/o carga posterior.

---

## 2. Flujo (alto nivel)

```text
Ruta compartida audios ──► Copia local por fecha/carpeta ──► Transcripción TXT ──►
Reglas (diccionarios) ──► (Opcional) Ollama ──► Excel/CSV final + cache LLM
```

---

## 3. Componentes del notebook

### 3.1 Copia de audios (share → local)

**Entrada**
- Ruta origen (share): `RUTA_ORIGEN` (ej. `\\SRV...\recordings`)
- Fecha objetivo: `FECHA_OBJETIVO` (formato carpeta `M_D_YYYY`)
- Extensiones admitidas: `EXTENSIONES_AUDIO`

**Salida**
- Carpeta destino calculada: `RUTA_DESTINO_BASE / f"audios {FECHA_FOLDER}"`
- El copiado evita sobre-escritura si el archivo ya existe y tiene mismo tamaño.

**Puntos críticos**
- Requiere permisos de lectura sobre la ruta compartida.
- Si el share tiene estructura profunda por asesor/carpeta, el código recorre y copia.

---

### 3.2 Plantilla/metadata desde SQL Server (opcional en tu flujo)

El notebook contiene consultas a SQL Server para:
- Recuperar plantilla/tabla (ej. para población o estructura operativa)
- Mapear identificación/cedula ↔ correo (por ejemplo desde `dbo.Planta_Activa`)

**Requisitos**
- ODBC Driver instalado
- Acceso de red al servidor SQL
- Credenciales seguras (no hardcodear)

**Buenas prácticas**
- Usar `Trusted_Connection=yes` cuando aplique.
- Si usas usuario/contraseña:
  - guardar la contraseña en `.env` o pedirla una sola vez y guardarla localmente de forma segura (ver `docs/SECURITY.md`).

---

### 3.3 Transcripción (faster-whisper)

**Entrada**
- `INPUT_ROOT`: carpeta con audios
- `OUTPUT_DIR`: carpeta salida
- Idioma (típicamente español)
- Configuración GPU/CPU:
  - `device="cuda"` o `device="cpu"`
  - `compute_type="float16"` (GPU) o `int8` (CPU)

**Salida**
- Un archivo `.txt` por audio (mismo nombre base).
- Idempotencia: si el `.txt` existe, se puede omitir (depende de tu lógica).

**Requisitos**
- `ffmpeg` en PATH.
- Para GPU: Torch + CUDA correctamente instalados.

---

### 3.4 Evaluación por reglas/diccionarios

El notebook define listas de frases (ej. cierre real, seguimiento, anti-cierre, etc.) y produce una etiqueta final.

**Objetivo**
- Tener un baseline rápido, reproducible y auditable.

**Resultado**
- Campos típicos:
  - score/puntajes
  - flags por tipo (cierre/seguimiento)
  - `etiqueta_final` (p. ej. efectiva / no efectiva / revisar)

---

### 3.5 Evaluación con Ollama (opcional)

**Activación**
- `USE_OLLAMA = True`
- `OLLAMA_BASE = "http://localhost:11434"`
- `OLLAMA_MODEL = "qwen2.5:7b-instruct"`

**Control de costo/latencia**
- `MAX_OLLAMA_WORKERS`: concurrencia
- `OLLAMA_ONLY_BORDERLINE`: solo llama al LLM si el caso es borderline
- `BORDERLINE_MIN`, `BORDERLINE_MAX`: rango para decidir “ambigüedad”
- Cache:
  - `CACHE_DIR = OUTPUT_DIR / "_ollama_cache"`

**Buenas prácticas**
- Prompts que exijan JSON estricto (para parseo robusto).
- Retries controlados (`OLLAMA_MAX_RETRIES`).
- Timeout defensivo (`OLLAMA_TIMEOUT`).

---

## 4. Outputs

El pipeline exporta:
- `*.xlsx` (si `openpyxl` está disponible y el archivo no está abierto)
- fallback a `*.csv` si falla la escritura del Excel
- carpeta cache: `_ollama_cache/`

---

## 5. Troubleshooting

### Error: `pyodbc` no conecta
- Verifica ODBC Driver 17/18 instalado.
- Revisa firewall/VPN/red.
- Si usas `Trusted_Connection`, debe existir contexto de dominio/Windows adecuado.

### Error: no encuentra `ffmpeg`
- Instala ffmpeg y agrega al PATH.
- Reinicia la terminal/VSCode para que tome el PATH.

### Ollama no responde
- Verifica `http://localhost:11434` y que el modelo esté descargado (`ollama pull ...`).
- Baja `MAX_OLLAMA_WORKERS` si se satura.

---

## 6. Seguridad (muy importante)

Revisa `docs/SECURITY.md` para:
- manejo de credenciales
- manejo de PII
- qué NO subir a git
