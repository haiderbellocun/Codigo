- Recorre la grilla de People Management
- Para cada fila:
    * Dedup (índice compartido + PDFs existentes)
    * Si ya existe PDF, verifica que el nombre tenga _<emailLocal> y _<CEDULA>; si faltan, renombra
    * Si no existe, genera "PDA Report", espera la descarga y mueve/renombra
- Paginación + items por página al máximo
"""

import os, time, json, socket, uuid, shutil, re, unicodedata, glob
from typing import Optional, Tuple, List, Dict
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# ===================== CONFIG =====================
LIST_URL = os.environ.get("LIST_URL", "https://hrtech.pdaprofile.com/app/people-managment")

# Carpeta local de descargas (propia de cada PC)
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", r"C:\pda_reports\downloads")

# Carpeta COMPARTIDA entre los equipos (red/OneDrive/Drive). MISMA RUTA EN AMBOS PCS.
SHARED_DIR = os.environ.get("SHARED_DIR", DOWNLOAD_DIR)

MAX_ROWS: Optional[int] = (int(os.environ.get("MAX_ROWS","0")) or None)  # 0/empty => todas
WAIT = int(os.environ.get("WAIT", "25"))
PAUSE_BETWEEN_ROWS = 1.2
CLICK_GAP_SEC = 2.2
FINAL_HOLD_SEC = 10.0
PREFERRED_PAGE_SIZE = int(os.environ.get("PREFERRED_PAGE_SIZE", "200"))
DEBUG_ADDR = os.environ.get("DEBUG_ADDR", "127.0.0.1:9222")

# Índice compartido
INDEX_FILENAME = "processed_index.json"
LOCK_FILENAME  = "index.lock"
# ==================================================

# ---------- XPATHs de tabla / filas ----------
TABLE_ROWS_XPATH = (
    "//table//tbody//tr"
    " | //div[contains(@class,'table')]//div[contains(@role,'row') and contains(@class,'body')]"
)

# Acciones dentro de fila
ROW_THREE_DOTS_XPATH = (
    ".//button[contains(@class,'mat-menu-trigger') or @aria-haspopup='menu' or contains(@class,'menu')]"
    "[.//mat-icon[normalize-space()='more_vert'] or .//*[normalize-space()='more_vert']]"
)
ROW_CARET_XPATH = ".//button[.//mat-icon[normalize-space()='keyboard_arrow_down']]"

# Overlays / Drawer
OVERLAY_PANE_CSS = ".cdk-overlay-pane"
OVERLAY_BACKDROP_CSS = ".cdk-overlay-backdrop"
DRAWER_OPEN_XPATH = "//div[contains(@class,'mat-drawer') and contains(@class,'mat-drawer-end') and contains(@class,'mat-drawer-opened')]"

# Menú contextual → 'Generate/Generar'
MENU_GENERATE_ITEM_REL_XPATH = (
    ".//button[contains(@class,'mat-menu-item')]"
    "[.//span[normalize-space()='Generate'] or contains(normalize-space(.),'Generate')"
    " or .//span[normalize-space()='Generar'] or contains(normalize-space(.),'Generar')]"
)

# Panel derecho → 'PDA Report' / 'Reporte PDA'
PDA_REPORT_BTN_XPATH = (
    "//span[contains(@class,'mat-button-wrapper') and normalize-space()='PDA Report']/ancestor::button[1]"
    " | //span[contains(@class,'mat-button-wrapper') and normalize-space()='Reporte PDA']/ancestor::button[1]"
    f" | {DRAWER_OPEN_XPATH}//button[.//span[normalize-space()='PDA Report'] or .//span[normalize-space()='Reporte PDA']]"
    f" | {DRAWER_OPEN_XPATH}//button[contains(.,'PDA Report') or contains(.,'Reporte PDA')]"
)

# Botón 'Generate/Generar' dentro del drawer
PANEL_GENERATE_BTN_XPATH = (
    "//button[.//span[normalize-space()='Generate'] or contains(normalize-space(.),'Generate')"
    " or .//span[normalize-space()='Generar'] or contains(normalize-space(.),'Generar')]"
)
FINAL_GENERATE_IN_DRAWER_XPATH = (
    f"{DRAWER_OPEN_XPATH}//button[contains(@class,'mat-flat-button')]"
    "[.//span[normalize-space()='Generate'] or .//span[normalize-space()='Generar']]"
)

# Paginador
NEXT_PAGE_BTN_XPATH = (
    "//button[contains(@class,'mat-paginator-navigation-next') and not(@disabled)]"
    " | //mat-paginator//button[contains(@aria-label,'Next') and not(@disabled)]"
    " | //button[(contains(normalize-space(.),'Siguiente') or contains(normalize-space(.),'Next')) and not(@disabled)]"
)

# Page size (Items per page)
PAGE_SIZE_SELECT_XPATH = (
    "//mat-paginator//mat-select[contains(@class,'mat-paginator-page-size-select') or @aria-label='Items per page:']"
    " | //mat-paginator//*[contains(normalize-space(.),'Items per page')]/following::*[self::mat-select or self::div or self::button][1]"
)
PAGE_SIZE_OPTION_XPATH_TPL = "//div[contains(@class,'cdk-overlay-pane')]//mat-option//span[normalize-space()='{}']"

# --- Celda People / Documento (más robusto) ---
ROW_PERSON_TD_XPATH       = ".//td[contains(@class,'mat-column-person') and contains(@class,'cdk-column-person')]"
ROW_NAME_IN_PERSON_XPATH  = ".//span[contains(@class,'font-medium')][1]"
ROW_EMAIL_IN_PERSON_XPATH = ".//a[starts-with(@href,'mailto:')] | .//*[contains(text(),'@')]"
ROW_DOC_TD_XPATH          = ".//td[contains(@class,'mat-column-fieldOne') or contains(@class,'cdk-column-fieldOne')]"

# ---------- utils (compartida/índice) ----------
def ensure_dirs():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(SHARED_DIR, exist_ok=True)

def _normalize_ascii(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def slugify(s: str) -> str:
    s = _normalize_ascii(s)
    keep = []
    for ch in s:
        if ch.isalnum():
            keep.append(ch)
        elif ch in (' ', '-', '_', '.'):
            keep.append(ch)
        else:
            keep.append(' ')
    out = ' '.join(''.join(keep).split())
    return out.replace(' ', '_')

def email_local(email: str) -> str:
    return (email.split("@", 1)[0] if ("@" in (email or "")) else "").strip()

def index_paths():
    return (os.path.join(SHARED_DIR, INDEX_FILENAME), os.path.join(SHARED_DIR, LOCK_FILENAME))

@contextmanager
def index_lock(timeout=15):
    _, lock_path = index_paths()
    token = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex}"
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(token)
            break
        except FileExistsError:
            if time.time() - start > timeout:
                print("⚠️  No pude obtener lock del índice; sigo sin lock.")
                break
            time.sleep(0.3)
    try:
        yield
    finally:
        try:
            if os.path.exists(lock_path): os.remove(lock_path)
        except Exception: pass

def load_index() -> set:
    idx_path, _ = index_paths()
    try:
        with open(idx_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list): return set(data)
        if isinstance(data, dict) and "hashes" in data: return set(data["hashes"])
    except Exception:
        pass
    return set()

def save_index(hashes: set):
    idx_path, _ = index_paths()
    tmp = idx_path + ".tmp"
    data = {"hashes": sorted(list(hashes))}
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, idx_path)

def already_processed_any(keys: List[str]) -> bool:
    with index_lock():
        return any(k in load_index() for k in keys)

def mark_processed_all(keys: List[str]):
    with index_lock():
        s = load_index()
        changed = False
        for k in keys:
            if k and k not in s:
                s.add(k); changed = True
        if changed: save_index(s)

def build_candidate_keys(name: str, email: str, doc: str, gender: str = "") -> List[str]:
    name_norm = _normalize_ascii(name or "").strip().lower()
    ks = []
    if email: ks.append(email.strip().lower())
    if name_norm and doc: ks.append(f"{name_norm}|{doc}")
    if name_norm: ks.append(name_norm)
    if name_norm and doc and gender: ks.append(f"{name_norm}|{doc}|{gender.strip().lower()}")
    dedup = []
    for k in ks:
        if k and k not in dedup: dedup.append(k)
    return dedup

def report_exists_in_shared(name: str, email: str, doc: str) -> bool:
    """Compatibilidad: no se usa en el early-exit principal, pero queda disponible."""
    base = slugify(_normalize_ascii(name or "").strip()) if name else ""
    eloc = slugify(email_local(email)) if email else ""
    pats = []
    if base: pats.append(os.path.join(SHARED_DIR, f"ReportePDA_{base}*"))
    if base and eloc: pats.append(os.path.join(SHARED_DIR, f"ReportePDA_{base}_{eloc}*"))
    if base and doc: pats.append(os.path.join(SHARED_DIR, f"ReportePDA_{base}_{doc}*"))
    if base and eloc and doc: pats.append(os.path.join(SHARED_DIR, f"ReportePDA_{base}_{eloc}_{doc}*"))
    for pat in pats:
        if glob.glob(pat): return True
    return False

# ---------- extracción robusta por fila ----------
def extract_name_email_doc(driver, idx) -> Tuple[str, str, str]:
    """Re-localiza la fila por índice. Extrae nombre, email y cédula (celda o regex)."""
    def get_row():
        return driver.find_element(By.XPATH, f"({TABLE_ROWS_XPATH})[{idx}]")

    # Retry simple
    row = None
    for _ in range(3):
        try:
            row = get_row(); break
        except StaleElementReferenceException:
            time.sleep(0.2)
    if row is None:
        row = get_row()

    name, email, doc = "", "", ""

    # nombre/email
    try:
        p = row.find_element(By.XPATH, ROW_PERSON_TD_XPATH)
        try:
            name = (p.find_element(By.XPATH, ROW_NAME_IN_PERSON_XPATH).get_attribute("innerText") or "").strip()
        except Exception:
            pass
        try:
            e = p.find_element(By.XPATH, ROW_EMAIL_IN_PERSON_XPATH)
            email = (e.get_attribute("data-email")
                     or e.get_attribute("title")
                     or e.text
                     or e.get_attribute("href")
                     or e.get_attribute("innerText")
                     or "").strip()
            if email.startswith("mailto:"): email = email.replace("mailto:", "").strip()
        except Exception:
            pass
    except Exception:
        pass

    if not name:
        try:
            whole = (row.get_attribute("innerText") or "")
            lines = [t for t in whole.split("\n") if t.strip()]
            if lines: name = lines[0].strip()
        except Exception:
            pass

    # fallback email por regex (texto y HTML)
    if not email:
        try:
            whole = (row.get_attribute("innerText") or row.text or "")
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", whole)
            if m:
                email = m.group(0)
            else:
                html = row.get_attribute("outerHTML") or ""
                m2 = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
                if m2: email = m2.group(0)
        except Exception:
            pass

    # cédula en celda específica
    try:
        td = row.find_element(By.XPATH, ROW_DOC_TD_XPATH)
        raw = (td.get_attribute("innerText") or td.text or "").strip()
        only = re.sub(r"\D", "", raw)
        if len(only) >= 6:
            doc = only
    except Exception:
        pass

    # fallback cédula: regex en todo el texto
    if not doc:
        try:
            whole = (row.get_attribute("innerText") or row.text or "")
            m = re.search(r"\b(\d{7,})\b", whole)
            if m: doc = m.group(1)
        except Exception:
            pass

    return name, email, doc

# ---------- nombres sugeridos / movimiento ----------
def suggested_filename(name: str, email: str, doc: str) -> str:
    base = slugify(_normalize_ascii(name or "").strip() or "PDA_Report")[:90]
    eloc = slugify(email_local(email))[:50] if email else ""
    root = f"ReportePDA_{base}"
    if eloc:
        root = f"{root}_{eloc}"
    if doc:
        root = f"{root}_{doc}"
    return f"{root}.pdf"

def move_to_shared_and_rename(local_filename: str, final_name: str) -> str:
    """Mueve desde DOWNLOAD_DIR → SHARED_DIR y asegura nombre único."""
    src = os.path.join(DOWNLOAD_DIR, local_filename)
    base, ext = os.path.splitext(final_name)
    if not ext: ext = ".pdf"
    dst = os.path.join(SHARED_DIR, base + ext)
    k = 2
    while os.path.exists(dst):
        dst = os.path.join(SHARED_DIR, f"{base}_{k}{ext}")
        k += 1
    shutil.move(src, dst)
    return dst

# ---------- Normalización de nombre si el PDF ya existía ----------
def canonical_root(name: str, email: str, doc: str) -> str:
    """Root sin extensión con el mismo criterio de suggested_filename."""
    base = slugify(_normalize_ascii(name or "").strip() or "PDA_Report")[:90]
    eloc = slugify(email_local(email))[:50] if email else ""
    parts = [f"ReportePDA_{base}"]
    if eloc:
        parts.append(eloc)
    if doc:
        parts.append(doc)
    return "_".join(parts)

def _tokens_from_path(path: str) -> List[str]:
    root = os.path.splitext(os.path.basename(path))[0]
    return root.split("_")

def has_token_anywhere(path: str, token: str) -> bool:
    """¿El token aparece como token independiente (separado por '_') en cualquier parte del root?"""
    if not token:
        return False
    toks = _tokens_from_path(path)
    tnorm = slugify(token)
    return any(t == tnorm for t in toks)

def find_existing_reports_by_name(name: str) -> List[str]:
    """Rutas de PDFs existentes que arrancan por ReportePDA_<base> en SHARED_DIR."""
    base = slugify(_normalize_ascii(name or "").strip()) if name else ""
    if not base:
        return []
    pat = os.path.join(SHARED_DIR, f"ReportePDA_{base}*.pdf")
    return sorted(glob.glob(pat), key=lambda p: os.path.getmtime(p), reverse=True)

def scan_candidates_by_signals(name: str, email: str, doc: str) -> List[str]:
    """
    Busca PDFs que coincidan por:
      - base del nombre (ReportePDA_<NombreSlug>*), y/o
      - doc como token, y/o
      - email local como token.
    Devuelve candidatos ordenados por score y última modificación (más reciente primero).
    """
    base = slugify(_normalize_ascii(name or "").strip()) if name else ""
    eloc = slugify(email_local(email))[:50] if email else ""
    patterns = set()

    if base:
        patterns.add(os.path.join(SHARED_DIR, f"ReportePDA_{base}*.pdf"))
    if doc:
        patterns.add(os.path.join(SHARED_DIR, f"ReportePDA_*_{doc}.pdf"))
        patterns.add(os.path.join(SHARED_DIR, f"ReportePDA_*{doc}*.pdf"))
    if eloc:
        patterns.add(os.path.join(SHARED_DIR, f"ReportePDA_*_{eloc}*.pdf"))

    paths = set()
    for pat in patterns:
        paths.update(glob.glob(pat))

    if not paths and base:
        paths = set(glob.glob(os.path.join(SHARED_DIR, f"ReportePDA_{base}*.pdf")))

    def score(p: str) -> int:
        s = 0
        if eloc and has_token_anywhere(p, eloc): s += 2
        if doc and has_token_anywhere(p, doc):   s += 3
        if base and os.path.basename(p).startswith(f"ReportePDA_{base}"): s += 1
        return s

    return sorted(paths, key=lambda p: (score(p), os.path.getmtime(p)), reverse=True)

def ensure_canonical_name_if_exists(name: str, email: str, doc: str) -> Tuple[Optional[str], bool]:
    """
    Localiza un PDF existente por nombre base, doc y/o email local.
    Si falta añadir _<emailLocal> y/o _<doc>, renombra al formato canónico.
    Devuelve (ruta_final, changed).
    """
    eloc = slugify(email_local(email))[:50] if email else ""
    candidates = scan_candidates_by_signals(name, email, doc)
    if not candidates:
        return None, False

    best = candidates[0]
    had_eloc = has_token_anywhere(best, eloc) if eloc else False
    had_doc  = has_token_anywhere(best, doc)  if doc  else False
    need_eloc = bool(eloc and not had_eloc)
    need_doc  = bool(doc  and not had_doc)

    if not (need_eloc or need_doc):
        return best, False

    missing = []
    if need_eloc: missing.append("correo")
    if need_doc:  missing.append("cédula")
    print(f"      ↪ Faltaba(n): {', '.join(missing)} → renombrando a canónico…")

    new_root = canonical_root(name, email, doc)
    dst = os.path.join(SHARED_DIR, f"{new_root}.pdf")
    base, ext = os.path.splitext(dst)
    k = 2
    while os.path.exists(dst):
        dst = f"{base}_{k}.pdf"
        k += 1
    try:
        os.replace(best, dst)   # atómico misma unidad
    except Exception:
        shutil.move(best, dst)  # fallback
    return dst, True

# ---------- Selenium helpers ----------
def build_driver_remote(debug_addr: str = DEBUG_ADDR) -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.debugger_address = debug_addr
    driver = webdriver.Chrome(options=chrome_options)
    try: driver.set_window_rect(width=1400, height=900)
    except Exception: pass
    ensure_dirs()
    try:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": DOWNLOAD_DIR})
    except Exception:
        print("⚠️  No se pudo fijar carpeta de descargas por CDP; Chrome usará la predeterminada.")
    return driver

def wait_present(driver, by, locator, timeout=WAIT):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.05)
    driver.execute_script("arguments[0].click();", el)

def click_then_pause(driver, el, gap=CLICK_GAP_SEC):
    js_click(driver, el)
    time.sleep(gap)

def list_rows(driver) -> List:
    return driver.find_elements(By.XPATH, TABLE_ROWS_XPATH) or []

def close_drawer_and_overlays(driver):
    # cierra drawer
    try:
        for d in driver.find_elements(By.XPATH, DRAWER_OPEN_XPATH):
            close_btns = d.find_elements(
                By.XPATH,
                ".//button[.//mat-icon[normalize-space()='close'] or .//mat-icon[normalize-space()='arrow_back']"
                " or contains(@aria-label,'Close') or contains(@aria-label,'Cerrar')]"
            )
            if close_btns:
                click_then_pause(driver, close_btns[0], gap=0.3)
    except Exception:
        pass
    # cierra overlays
    try:
        for _ in range(3):
            backs = [b for b in driver.find_elements(By.CSS_SELECTOR, OVERLAY_BACKDROP_CSS) if b.is_displayed()]
            if not backs: break
            js_click(driver, backs[-1]); time.sleep(0.2)
    except Exception:
        try: driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        except Exception: pass

def first_row_key(driver) -> str:
    try:
        el = driver.find_element(By.XPATH, f"({TABLE_ROWS_XPATH})[1]")
        return (el.text or "").strip()
    except Exception:
        return ""

def go_next_page(driver, timeout=12) -> bool:
    close_drawer_and_overlays(driver)
    old_key = first_row_key(driver)
    try:
        next_btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, NEXT_PAGE_BTN_XPATH)))
    except TimeoutException:
        return False
    js_click(driver, next_btn)
    try:
        WebDriverWait(driver, timeout).until(lambda d: first_row_key(d) != old_key and len(list_rows(d)) > 0)
        time.sleep(0.5)
        return True
    except TimeoutException:
        return False

def set_items_per_page(driver, preferred=PREFERRED_PAGE_SIZE):
    try:
        size_trigger = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, PAGE_SIZE_SELECT_XPATH)))
        js_click(driver, size_trigger); time.sleep(0.2)
    except TimeoutException:
        return
    try:
        opt = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, PAGE_SIZE_OPTION_XPATH_TPL.format(preferred)))
        )
        js_click(driver, opt); time.sleep(0.5); return
    except TimeoutException:
        pass
    try:
        pane = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane")))
        options = pane.find_elements(By.XPATH, ".//mat-option//span")
        nums = []
        for s in options:
            try:
                val = int((s.text or "").strip()); nums.append((val, s))
            except Exception:
                continue
        if nums:
            _, el = sorted(nums, key=lambda t: t[0])[-1]
            js_click(driver, el); time.sleep(0.5)
    except TimeoutException:
        pass
    finally:
        close_drawer_and_overlays(driver)

def wait_for_download_finish(initial_files: set, timeout_sec: int = 180) -> Tuple[bool, str]:
    deadline = time.time() + timeout_sec
    seen = set(initial_files)
    while time.time() < deadline:
        now = set(os.listdir(DOWNLOAD_DIR))
        if any(f.endswith(".crdownload") for f in now):
            time.sleep(0.9); continue
        new_files = [f for f in now - seen if not f.endswith(".crdownload")]
        if new_files:
            newest = sorted(new_files, key=lambda x: os.path.getctime(os.path.join(DOWNLOAD_DIR, x)))[-1]
            return True, newest
        time.sleep(0.7)
    return False, ""

# ---------- flujo por fila ----------
def open_actions_menu(driver, row_el) -> bool:
    a = ActionChains(driver)
    try: a.move_to_element(row_el).perform(); time.sleep(0.15)
    except Exception: pass
    # tres puntos
    try:
        btn = row_el.find_element(By.XPATH, ROW_THREE_DOTS_XPATH)
        click_then_pause(driver, btn)
        for _ in range(8):
            panes = [p for p in driver.find_elements(By.CSS_SELECTOR, OVERLAY_PANE_CSS) if p.is_displayed()]
            if panes: return True
            time.sleep(0.25)
    except Exception:
        pass
    # caret (mobile)
    try:
        btn = row_el.find_element(By.XPATH, ROW_CARET_XPATH)
        click_then_pause(driver, btn)
        for _ in range(8):
            panes = [p for p in driver.find_elements(By.CSS_SELECTOR, OVERLAY_PANE_CSS) if p.is_displayed()]
            if panes: return True
            time.sleep(0.25)
    except Exception:
        pass
    return False

def click_menu_generate(driver) -> bool:
    try:
        panes = [p for p in driver.find_elements(By.CSS_SELECTOR, OVERLAY_PANE_CSS) if p.is_displayed()]
        for pane in reversed(panes):
            try:
                item = pane.find_element(By.XPATH, MENU_GENERATE_ITEM_REL_XPATH)
                click_then_pause(driver, item)
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def select_pda_report(driver) -> bool:
    try:
        pda = WebDriverWait(driver, 12).until(EC.element_to_be_clickable((By.XPATH, PDA_REPORT_BTN_XPATH)))
        click_then_pause(driver, pda)
        return True
    except TimeoutException:
        try:
            any_pda = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH, f"{DRAWER_OPEN_XPATH}//button[contains(.,'PDA')]"))
            )
            click_then_pause(driver, any_pda)
            return True
        except TimeoutException:
            print("   ℹ️  No encontré 'PDA Report/Reporte PDA' en el panel.")
            return False

def click_final_generate(driver) -> bool:
    try:
        final_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, FINAL_GENERATE_IN_DRAWER_XPATH)))
        click_then_pause(driver, final_btn)
        return True
    except TimeoutException:
        try:
            any_gen = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, PANEL_GENERATE_BTN_XPATH)))
            click_then_pause(driver, any_gen)
            return True
        except TimeoutException:
            print("   ❌ No pude clickear el 'Generate/Generar' final del drawer.")
            return False

def get_row_by_index(driver, idx: int):
    xp = f"({TABLE_ROWS_XPATH})[{idx}]"
    return driver.find_element(By.XPATH, xp)

def process_row_by_index(driver, idx, processed_cache: set) -> bool:
    close_drawer_and_overlays(driver)

    # Asegurar visibilidad y extraer señales robustas
    try:
        row_el = get_row_by_index(driver, idx)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", row_el)
        time.sleep(0.2)
    except Exception:
        print(f"   #{idx} ❌ No pude localizar la fila #{idx}.")
        return False

    # Extrae nombre, email y doc (cédula)
    name_dbg, email_dbg, doc_dbg = extract_name_email_doc(driver, idx)
    name_for_keys = name_dbg
    gender = ""  # si en tu UI aparece, extráelo similar a antes

    cand_keys = build_candidate_keys(name_for_keys, email_dbg, doc_dbg, gender)

    # --- DEDUP: verificación y normalización ANTES de saltar por índice ---
    already = already_processed_any(cand_keys) or any(k in processed_cache for k in cand_keys)
    if already:
        path, changed = ensure_canonical_name_if_exists(name_dbg, email_dbg, doc_dbg)
        if path:
            if changed:
                print(f"   #{idx} 📄 Ya existía. Aseguré nombre con correo/cédula: {path}")
            else:
                print(f"   #{idx} ✅ Verificado: ya tenía correo/cédula: {os.path.basename(path)}")
            for k in cand_keys: processed_cache.add(k)
            mark_processed_all(cand_keys)
            return True
        else:
            print(f"   #{idx} ⚠️ Marcado en índice pero sin PDF. Reprocesando…")
            # (sigue flujo normal)

    # --- Si NO estaba en índice, pero SÍ existe PDF: normaliza y salta ---
    path2, changed2 = ensure_canonical_name_if_exists(name_dbg, email_dbg, doc_dbg)
    if path2:
        if changed2:
            print(f"   #{idx} 📄 Ya existía. Aseguré nombre con correo/cédula: {path2}")
        else:
            print(f"   #{idx} ✅ Verificado: ya tenía correo/cédula: {os.path.basename(path2)}")
        for k in cand_keys: processed_cache.add(k)
        mark_processed_all(cand_keys)
        return True

    # --- Flujo UI: abrir menú -> Generate -> PDA Report -> Generate final ---
    preview = f"{(name_dbg or '').strip()} | {email_dbg or '-'} | ced={doc_dbg or '-'}"
    print(preview)

    if not open_actions_menu(driver, row_el):
        print(f"   #{idx} ❌ No pude abrir el menú de acciones.")
        return False

    if not click_menu_generate(driver):
        print(f"   #{idx} ❌ No apareció 'Generate/Generar' dentro del menú.")
        return False

    if not select_pda_report(driver):
        print(f"   #{idx} ❌ No pude seleccionar 'PDA Report/Reporte PDA'.")
        return False

    before = set(os.listdir(DOWNLOAD_DIR))

    if not click_final_generate(driver):
        print(f"   #{idx} ❌ No pude pulsar el 'Generate/Generar' final.")
        return False

    time.sleep(FINAL_HOLD_SEC)
    print(f"   #{idx} ✅ Generate pulsado. Esperando descarga…")

    okd, fname = wait_for_download_finish(before, timeout_sec=180)
    if okd:
        try:
            final_name = suggested_filename(name_dbg, email_dbg, doc_dbg)  # añade email/doc si están
            final_path = move_to_shared_and_rename(fname, final_name)
            print(f"   #{idx} 📄 Movido a compartida: {final_path}")
        except Exception as e:
            print(f"   #{idx} ⚠️ Descargado '{fname}', pero no pude mover/renombrar: {e}")

        for k in cand_keys: processed_cache.add(k)
        mark_processed_all(cand_keys)
        close_drawer_and_overlays(driver)
        return True
    else:
        print(f"   #{idx} ⚠️ No detecté archivo nuevo en {DOWNLOAD_DIR}.")
        close_drawer_and_overlays(driver)
        return False

# ---------- navegación con paginación ----------
def go_to_list(driver):
    if not driver.current_url.startswith(LIST_URL):
        driver.get(LIST_URL)
    wait_present(driver, By.XPATH, TABLE_ROWS_XPATH, timeout=WAIT)

def iterate_pages(driver):
    set_items_per_page(driver, preferred=PREFERRED_PAGE_SIZE)

    page = 1
    processed_total = 0
    processed_cache = set()

    while True:
        rows_now = list_rows(driver)
        total = len(rows_now)
        if total == 0:
            print("⚠️  No se detectaron filas. Revisa TABLE_ROWS_XPATH.")
            break

        print(f"\n== Página {page} | Filas visibles: {total} ==")

        for idx in range(1, total + 1):
            if MAX_ROWS is not None and processed_total >= MAX_ROWS:
                print(f"\n⏹ Límite MAX_ROWS alcanzado: {MAX_ROWS}")
                return

            print(f"[{idx}]", end=" ", flush=True)
            try:
                _ = process_row_by_index(driver, idx, processed_cache)
            except StaleElementReferenceException:
                try:
                    time.sleep(0.5)
                    _ = process_row_by_index(driver, idx, processed_cache)
                except Exception as e:
                    print(f"   ❌ Error inesperado en fila #{idx}: {e}")
            except Exception as e:
                print(f"   ❌ Error inesperado en fila #{idx}: {e}")

            processed_total += 1
            time.sleep(PAUSE_BETWEEN_ROWS)

        if go_next_page(driver):
            page += 1
            continue
        else:
            print("No hay más páginas (o botón 'Next' no disponible).")
            break

    print("\n✅ Proceso terminado.")

# ---------- main ----------
def main():
    ensure_dirs()
    driver = build_driver_remote(DEBUG_ADDR)
    try:
        go_to_list(driver)
        iterate_pages(driver)
        print(f"\n📂 Descargas locales: {DOWNLOAD_DIR}")
        print(f"🤝 Carpeta compartida: {SHARED_DIR}")
    finally:
        try: driver.quit()
        except Exception: pass

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scraper Selenium para generar/descargar Reporte PDA y moverlo a carpeta compartida."
    )
    parser.add_argument("--list-url", default=os.environ.get("LIST_URL", LIST_URL), help="URL de la lista (People Management).")
    parser.add_argument("--download-dir", default=os.environ.get("DOWNLOAD_DIR", DOWNLOAD_DIR), help="Carpeta local donde Chrome descarga PDFs.")
    parser.add_argument("--shared-dir", default=os.environ.get("SHARED_DIR", SHARED_DIR), help="Carpeta compartida para consolidar PDFs e índice.")
    parser.add_argument("--debug-addr", default=os.environ.get("DEBUG_ADDR", DEBUG_ADDR), help="Dirección DevTools (ej. 127.0.0.1:9222).")
    parser.add_argument("--max-rows", type=int, default=int(os.environ.get("MAX_ROWS","0") or "0"),
                        help="Límite de filas a procesar (0 = todas).")
    parser.add_argument("--wait", type=int, default=int(os.environ.get("WAIT","25")), help="Timeout base (segundos).")
    parser.add_argument("--page-size", type=int, default=int(os.environ.get("PREFERRED_PAGE_SIZE","200")), help="Items por página preferido.")
    args = parser.parse_args()

    # aplicar overrides a variables globales
    LIST_URL = args.list_url
    DOWNLOAD_DIR = args.download_dir
    SHARED_DIR = args.shared_dir
    DEBUG_ADDR = args.debug_addr
    WAIT = args.wait
    PREFERRED_PAGE_SIZE = args.page_size
    MAX_ROWS = (args.max_rows or None)

    main()

