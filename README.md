# Codigo

# Repositorios de Analítica & Automatización (CUN / COE)

Este repositorio/documento es un **índice** de los proyectos que he construido para automatización, analítica avanzada, NLP/LLM, scraping y pipelines de datos.

> ⚠️ Uso interno: **no subir credenciales, PII ni datos sensibles**. Todos los repos siguen el patrón `.env.example` + `.gitignore` para proteger información.

---

## Mapa general de repos

### 1) Contact Center / Evaluación de calidad
- **Call Evaluation CL Tiene (Descarga → Transcripción → Evaluación)**  
  Repo: `call_eval_cltiene_repo` → (link)  
  **Qué hace:** descarga audios (SFTP), transcribe (faster-whisper GPU/CPU), evalúa con reglas + LLM (Ollama) y exporta Excel final.  
  **Entrada:** lista/metadata (Excel) + audios + config `.env`  
  **Salida:** `outputs/` con reportes/Excel (no versionado)

- **Evaluación de chats**  
  Repo: `evaluacion_chats_repo` → (link)  
  **Qué hace:** evalúa conversaciones (chats) con reglas/LLM y genera reporte final.  
  **Entrada:** dataset de chats + config  
  **Salida:** `outputs/` reportes

---

### 2) AWS / S3 / Lambda
- **AWS Lambda Transcribe (CL Tiene)**  
  Repo: `aws_lambda_transcribe_cltiene_repo` → (link)  
  **Qué hace:** función Lambda para transcripción/flujo en AWS.  
  **Entrada:** eventos S3/trigger (según config)  
  **Salida:** artefactos/transcripciones (según pipeline)

- **PDA → S3 Uploader (AWS)**  
  Repo: `pda_upload_s3_repo` → (link)  
  **Qué hace:** sube archivos a S3 con concurrencia + **resume** usando `outputs/manifest.json`.  
  **Entrada:** carpeta local `LOCAL_DIR` + patrón `FILE_PATTERN`  
  **Salida:** carga en S3 + manifest en `outputs/`

---

### 3) Scraping / Descargas
- **Scraper de descarga (web)**  
  Repo: `scraper_descarga_repo` → (link)  
  **Qué hace:** automatiza descarga desde una página (scraping) y organiza salidas.  
  **Entrada:** credenciales/config en `.env`  
  **Salida:** `outputs/` (archivos descargados/logs)

---

### 4) Escucha Social / Marketing Analytics
- **Escucha social (análisis + extracción + sentimiento/LLM)**  
  Repo: `escucha_social_repo` → (link)  
  **Qué hace:** pipeline de social listening (clasificación, extracción de productos/oferta, enriquecimiento con LLM).  
  **Entrada:** dataset crudo (posts/comentarios)  
  **Salida:** dataset procesado para BI/SQL

- **Predicción de posts / tendencias**  
  Repo: `prediccion_posts_repo` → (link)  
  **Qué hace:** predice desempeño/tendencias de publicaciones y soporta planeación de contenido.  
  **Entrada:** histórico de posts + features  
  **Salida:** predicciones + reportes

---

### 5) Contenido / Multimedia
- **Resúmenes de videos**  
  Repo: `resumen_videos_repo` → (link)  
  **Qué hace:** genera resúmenes de videos (y opcional: extracción de puntos clave).  
  **Entrada:** links/archivos (según pipeline)  
  **Salida:** textos/resúmenes en `outputs/`

- **Audios entrenador (procesamiento)**  
  Repo: `audios_entrenador_repo` → (link)  
  **Qué hace:** pipeline para procesar/transcribir/analizar audios (según notebook).  
  **Entrada:** carpeta de audios  
  **Salida:** `outputs/` (transcripciones/reportes)

---

### 6) Permanencia estudiantil (Modelos + Base de datos)
- **Permanencia estudiantil – Modelos (6)**  
  Repo: `permanencia_modelos_repo` → (link)  
  **Modelos:** CatBoost, LightGBM, XGBoost, RandomForest + GRU + Semana 1 (notebooks)  
  **Entrenamiento:** 4 tabulares por CLI (`src/train.py`, `src/predict.py`)  
  **Deep/Semana:** notebooks (`notebooks/deep`, `notebooks/semana`)

- **Base de datos – GRU + Modelo Semanal**  
  Repo: `base_datos_gru_semana_repo` → (link)  
  **Qué hace:** extracción y construcción de datasets para GRU (secuencial) y datasets semanales (1/3/8/12).  
  **Salida:** `outputs/base_modelo.csv.gz`, `outputs/datos_secuenciales_para_gru.csv.gz`, `outputs/dataset_semana_<w>.csv.gz`

---

### 7) Rematrícula
- **Modelo de Rematrícula (XGBoost + calibración)**  
  Repo: `rematricula_modelo_repo` → (link)  
  **Qué hace:** entrena XGBoost con calibración (Platt OOF) + ajuste de esperados vs reales; genera ranking gestionable.  
  **Entrada:** extracción SQL/CSV (según config)  
  **Salida:** `outputs/` con modelo + predicciones

---

### 8) Utilidades / Carga a SQL Server
- **Carga masiva Excel → SQL Server (staging table)**  
  Repo: `carga_excel_sqlserver_repo` → (link)  
  **Qué hace:** lee Excel, valida/convierte tipos vs `INFORMATION_SCHEMA`, carga a staging y luego inserta al destino.  
  **Entrada:** `.xlsx` + tabla destino  
  **Salida:** registros insertados + logs

---

## Convenciones comunes (en todos los repos)

- **`docs/`**: documentación técnica y seguridad (`SECURITY.md`)
- **`.env.example`**: plantilla de configuración (nunca subir `.env`)
- **`.gitignore`**: ignora `data/`, `outputs/`, `.env`, artefactos y PII
- **`requirements.txt`**: dependencias mínimas
- **`scripts/`**: atajos (`run_all.ps1`, `run_all.sh`, etc.)
- **`outputs/`**: resultados (modelos, reportes, manifests) **NO versionados**
- **`notebooks/`**: notebooks originales/sanitizados (sin secretos)

---

## Instalación estándar (recomendada)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
