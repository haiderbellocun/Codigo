# Documentación técnica – Scraper de Descarga (Selenium)

## 1) Flujo general

1. Conectarse a un Chrome ya abierto por **DevTools** (`--remote-debugging-port=9222`).
2. Abrir/validar la URL de la lista (`LIST_URL`).
3. Ajustar paginación (Items per page).
4. Iterar filas:
   - abrir menú de acciones (tres puntos / caret)
   - seleccionar **Generate / Generar**
   - en el panel lateral: entrar a **PDA Report / Reporte PDA**
   - presionar **Generate / Generar**
   - esperar que el PDF termine de descargarse
   - mover el PDF a `SHARED_DIR` y renombrar
5. Deduplicación:
   - índice compartido `processed_index.json`
   - si el reporte ya existe, se omite

---

## 2) Cómo lanzar Chrome (DevTools)

### Windows
Ejemplo (ya incluido en `scripts/start_chrome_debug.ps1`):

- Puerto: `9222`
- Perfil: `C:\selenium\chrome-profile`

Recomendación:
- Cierra otros Chromes antes de abrir este.
- Usa un perfil dedicado para mantener sesión.

### Linux/Mac
Ver `scripts/start_chrome_debug.sh`.

---

## 3) Descargas: puntos críticos

Para que Selenium pueda detectar la descarga:
- `DOWNLOAD_DIR` debe existir y ser escribible.
- El navegador debe permitir descarga automática en esa ruta.
- El scraper espera a que desaparezcan extensiones típicas de “en progreso” (`.crdownload`).

Si no detecta PDFs:
- valida que realmente se descargan en `DOWNLOAD_DIR`
- revisa la configuración de “Descargas” de Chrome
- revisa `wait_for_download_finish()` en `src/scraper.py`

---

## 4) Deduplicación multi-equipo

El índice en `SHARED_DIR` permite:
- evitar reprocesar la misma persona/registro
- coordinar dos equipos en paralelo

Archivos usados:
- `processed_index.json` (estado)
- `index.lock` (lock best-effort)

Si trabajas con red/OneDrive:
- evita conflictos de sincronización
- usa rutas iguales en ambos equipos

---

## 5) Troubleshooting

### No conecta a DevTools
- valida `DEBUG_ADDR=127.0.0.1:9222`
- confirma que Chrome se abrió con `--remote-debugging-port=9222`
- revisa firewall / procesos

### Elementos no encontrados (XPATH)
La UI puede cambiar. Si falla:
- ajusta XPATHs en el script
- sube `WAIT`
- valida que estés en la pantalla correcta y logueado

### Descarga lenta
- sube `WAIT`
- baja `PREFERRED_PAGE_SIZE`
- reduce `MAX_ROWS` en sesiones largas
