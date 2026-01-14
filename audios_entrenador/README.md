# Audios Entrenador – Descarga → Transcripción → Evaluación (.txt + Meta SQL)

Este repositorio reúne el flujo para trabajar con los **audios del entrenador**:

1) Traer **metadatos** desde SQL Server (`dbo.vapi_entrenador`)  
2) (Opcional) **Descargar audios** desde `recording_url`  
3) (Opcional) **Transcribir audios** a `.txt` con **faster-whisper**  
4) **Evaluar** los `.txt` con diccionarios de keywords + métricas y cruce de meta  
5) Exportar **Excel/CSV** en `outputs/`

Incluye el notebook original: `audi_entrenador.ipynb`.



---

## Instalación

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python -m textblob.download_corpora
```

### Transcripción (opcional)
```bash
pip install -r requirements-whisper.txt
```

---

## Configuración
Copia `.env.example` a `.env` y ajusta rutas/SQL.

---

## Uso

### 1) Descargar audios (opcional)
```bash
python src/download_audios.py --out-dir inputs\audios
```

### 2) Transcribir audios → .txt (opcional)
```bash
python src/transcribe_audios.py --audio-dir inputs\audios --out-dir inputs\txt
```

### 3) Evaluar .txt y exportar
```bash
python src/evaluar_txt.py --input-txt-dir inputs\txt --output-dir outputs
```

Sin SQL:
```bash
python src/evaluar_txt.py --no-sql
```

---

## Documentación
- `docs/DOCUMENTATION.md` – flujo y troubleshooting  
- `docs/SQL.md` – campos/tablas y conexión  
- `docs/SECURITY.md` – PII / secretos / buenas prácticas  
