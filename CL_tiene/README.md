# Proceso de llamadas CL Tiene (Descarga → Transcripción → Evaluación)

Pipeline en Python/Jupyter para:

1) **Descargar audios** desde un servidor vía **SFTP (Paramiko)** usando una lista en Excel (`nombre_audio`).
2) **Transcribir audios a TXT** con **faster-whisper** (GPU) en paralelo.
3) **Evaluar calidad de llamadas**:
   - Baseline por **diccionarios** (reglas).
   - Evaluación con **LLM local (Ollama)** + unión con **metadata Excel** para exportar un **Excel final**.

> Este repositorio está pensado para uso interno. **No subas credenciales** ni datos sensibles (PII) al control de versiones.

---

## Estructura sugerida del repo

```text
.
├─ Proceso llamadas CL Tiene.ipynb
├─ requirements.txt
├─ README.md
└─ docs/
   └─ DOCUMENTATION.md
