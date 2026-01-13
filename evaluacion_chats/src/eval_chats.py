# -*- coding: utf-8 -*-
"""
Limpia chats eliminando CUNDigital/Channel User, analiza keywords y sentimiento,
y enriquece con cédula del asesor vía SQL (dbo.Planta_Activa: box_mail -> Identificacion).

- Entrada: archivo .xlsx/.csv (INPUT_SRC) o df4 en memoria (si INPUT_SRC=None)
- Salida: DataFrame con columnas tipo "ventas" y guardado opcional en OUTPUT_PATH
"""

import os


import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import re
import unicodedata
import html
from datetime import datetime, time
from pathlib import Path
from textblob import TextBlob
from textblob.classifiers import NaiveBayesClassifier
import pyodbc  # ← necesario para cargar cédulas

# ===================== CONFIGURA AQUÍ =====================
INPUT_SRC = os.environ.get("INPUT_SRC", "") or None  # ruta .xlsx/.csv; si None intenta df4 en notebook
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "outputs/chats_evaluados.xlsx")
TIPO_POR_DEFECTO = os.environ.get("TIPO_POR_DEFECTO", "chats")

# --- Parámetros SQL para cédulas (Planta_Activa) ---
SQL_TRUSTED  = os.environ.get('SQL_TRUSTED','true').lower() in {'1','true','yes','y'}
SQL_DRIVER   = os.environ.get('SQL_DRIVER','ODBC Driver 17 for SQL Server')
USE_SQL_CEDULAS = os.environ.get("USE_SQL_CEDULAS", "true").lower() in {"1","true","yes","y"}
SQL_SERVER = os.environ.get("SQL_SERVER", "")
SQL_DATABASE = os.environ.get("SQL_DATABASE", "")
SQL_USER = os.environ.get("SQL_USER", "")
SQL_PASSWORD = os.environ.get("SQL_PASSWORD", "")  # NO hardcodear

# ===================== Helpers I/O =====================
def load_input(src_or_df):
    """Acepta DataFrame o ruta (.xlsx/.csv). Si src_or_df=None, intenta usar df4 en memoria."""
    if isinstance(src_or_df, pd.DataFrame):
        return src_or_df.copy()
    if src_or_df is None:
        try:
            return df4.copy()  # noqa: F821
        except NameError:
            raise ValueError("No se pasó INPUT_SRC ni existe df4 en memoria.")
    p = Path(src_or_df)
    if not p.exists():
        raise FileNotFoundError(f"No existe el archivo: {p}")
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(p)
    if ext == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Extensión no soportada: {ext}. Usa .xlsx/.xls/.csv o pasa un DataFrame.")

def save_output(df: pd.DataFrame, out_path):
    """
    Acepta carpeta o archivo:
    - Si out_path es carpeta o no tiene extensión -> crea nombre por defecto resultado_YYYYmmdd_%H%M.xlsx
    - Si no puede escribir XLSX, guarda CSV al mismo lado.
    """
    if not out_path:
        print("ℹ️ OUTPUT_PATH=None → no se guarda archivo.")
        return
    p = Path(out_path)
    if (p.exists() and p.is_dir()) or (p.suffix == ""):
        if p.suffix == "" and not p.exists() and p.parent.exists() and not p.parent.suffix:
            p = p / f"resultado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        elif p.exists() and p.is_dir():
            p = p / f"resultado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        else:
            p = p.with_suffix(".xlsx")
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_excel(p, index=False)
        print(f"✅ Guardado Excel en: {p}")
    except Exception as e:
        alt = p.with_suffix(".csv")
        df.to_csv(alt, index=False, encoding="utf-8-sig")
        print(f"⚠️ No se pudo escribir XLSX ({e}). Guardado CSV en: {alt}")

# ===================== Limpieza (sin #Contact) =====================
SPEAKER_LINE_RX = re.compile(r"^\s*#?\s*([^\n:]+?)\s*:\s*(.*)$")
BOT_NAMES = {
    "cun digital", "cundigital", "cun bot", "chatbot", "chat bot",
    "asistente virtual", "sistema", "system", "ivr", "virtual assistant",
    "channel user"
}

def _html_unescape(txt: str) -> str:
    return html.unescape(txt) if isinstance(txt, str) else txt

def _quitar_acentos(s: str) -> str:
    if not isinstance(s, str): return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm_name(name: str) -> str:
    n = _quitar_acentos(name).strip().lower()
    n = re.sub(r"\s+", " ", n)
    return n

def _is_bot_speaker(speaker: str) -> bool:
    return _norm_name(speaker) in BOT_NAMES

def _split_turns(text: str):
    """Devuelve [(speaker, content)] a partir de líneas '#Nombre : texto'."""
    if not isinstance(text, str) or not text.strip():
        return []
    t = _html_unescape(text)
    turns, current_speaker, current_lines = [], None, []
    for line in t.splitlines():
        m = SPEAKER_LINE_RX.match(line)
        if m:
            if current_speaker is not None:
                turns.append((current_speaker, "\n".join(current_lines).rstrip()))
            current_speaker = m.group(1).strip()
            first_line = m.group(2).rstrip()
            current_lines = [first_line] if first_line != "" else []
        else:
            if current_speaker is not None:
                current_lines.append(line.rstrip())
    if current_speaker is not None:
        turns.append((current_speaker, "\n".join(current_lines).rstrip()))
    return turns

def limpiar_sin_cundigital(text: str) -> str:
    """Elimina turnos de speakers BOT (CUNDigital/Channel User/etc.) en toda la celda."""
    if not isinstance(text, str) or not text.strip():
        return ""
    turns = _split_turns(text)
    if not turns:
        return ""
    kept = []
    for speaker, content in turns:
        if _is_bot_speaker(speaker):
            continue
        content = (content or "").strip()
        kept.append(f"#{speaker} : {content}" if content else f"#{speaker} :")
    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned

def pick_text_column_for_clean(df: pd.DataFrame) -> str:
    prefer = ["Transcripción", "Transcripcion"]
    fallback = ["Transcripción_limpia", "Transcripcion_limpia", "Transcripción_limpia_v2", "Transcripcion_limpia_v2"]
    for c in prefer:
        if c in df.columns: return c
    for c in fallback:
        if c in df.columns: return c
    for c in df.columns:
        if "transcripcion" in _quitar_acentos(str(c)).strip().lower():
            return c
    raise KeyError("No encuentro la columna de transcripción (ej. 'Transcripción').")

def limpiar_df4(df4: pd.DataFrame, dest_col: str = "Transcripción_limpia_v2") -> pd.DataFrame:
    base_col = pick_text_column_for_clean(df4)
    df = df4.copy()
    df[dest_col] = df[base_col].fillna("").astype(str).map(limpiar_sin_cundigital)
    return df

# ===================== Diccionarios / Requisitos =====================
diccionarios_keywords = {
    "saludo": {
        "alo","hola","buenos dias","buenas tardes","buenas noches","digame","si","quien habla","con quien hablo",
        "quien llama","de parte de quien","le puedo ayudar en algo","en que le puedo servir","que desea","que necesita",
        "habla con","soy","aqui","departamento de","le atiende","si le escucho","le oigo","adelante","te escucho","todo bien",
        "que tal","como le va","como te va","que cuentas","que hay de nuevo","que pasa","que me cuentas","a quien busca",
        "a quien desea hablar","con quien gustaria hablar","con quien le gustaria hablar","con quien te gustaria hablar","a quien busca por favor",
        "podria decirme con quien desea hablar","hablo con","si soy yo","en que puedo ayudarle","si habla con el","si habla con ella","si que necesita",
        "un segundo por favor","espere un momentito","ya le pongo","me puede repetir su nombre por favor","podria deletrear su nombre","cual es su apellido",
        "de que empresa llama","cual es su extension","no le escucho bien podria hablar mas alto","se oye entrecortado","puede repetir",
        "entendio","esta claro","perfecto","muy bien","de acuerdo","entendido","gracias","muchas gracias","a usted","con gusto","que tenga un buen dia",
        "que tenga buena tarde","que tenga buena noche","igualmente","hasta luego","adios","nos vemos","que le vaya bien","saludos","un placer atenderle",
        "gracias por su tiempo","nombre","area","admisiones","interes","acompañarte"
    },
    "indagacion": {
        "alguna vez has considerado la posibilidad de estudiar algo mas","hay algun tema que siempre te haya llamado la atencion y que quizas te gustaria estudiar",
        "te has preguntado como seria estudiar","te gustaria estudiar en la cun","que opinas sobre la educacion continua o el aprendizaje a lo largo de la vida",
        "crees que en algun momento te gustaria ampliar tus conocimientos a traves de estudios","te ves volviendo a estudiar en el futuro",
        "que factores te harian considerar seriamente la opcion de estudiar","hay algo que te gustaria aprender o profundizar si tuvieras la oportunidad",
        "que tipo de habilidades o conocimientos te gustaria adquirir","te interesa el desarrollo personal y profesional a traves de la educacion",
        "has visto algun programa o curso que te haya parecido interesante","que piensas sobre la idea de invertir tiempo y recursos en tu formacion",
        "crees que estudiar podria abrirte nuevas puertas en el futuro","que te detendria de estudiar en este momento",
        "que necesitarias para tomar la decision de estudiar","te gustaria explorar opciones de estudio en algun momento","que tanto valoras la educacion en tu vida",
        "hay algun cambio en tu vida que podria motivarte a estudiar","que beneficios crees que podrias obtener al estudiar","estudiaste algo en el pasado",
        "como fue tu experiencia estudiando","que piensas sobre la gente que estudia actualmente","crees que la educacion es importante en general",
        "estas ocupado con otras cosas en este momento","estas ocupada con otras cosas en este momento","tienes planes a corto plazo que no incluyen estudiar",
        "estas enfocado en tu trabajo o en otras prioridades","estas enfocada en tu trabajo o en otras prioridades","sientes que necesitas estudiar algo en este momento",
        "hay algo mas que te interese hacer en lugar de estudiar","como te sientes con respecto a tu desarrollo profesional actual","crees que necesitas mas formacion para alcanzar tus metas",
        "que te parece la idea de volver a las aulas","te imaginas estudiando de nuevo alguna vez","que opinas sobre el sistema educativo actual",
        "crees que estudiar es para todos","que alternativas a la educacion formal consideras validas","te sientes realizada profesionalmente sin necesidad de mas estudios",
        "te sientes realizado profesionalmente sin necesidad de mas estudios","hay algun obstaculo importante que te impida estudiar","que necesitaria cambiar en tu vida para considerar estudiar",
        "te ves jubilando sin volver a estudiar","te sientes satisfecho con tu nivel actual de conocimientos o te gustaria seguir aprendiendo",
        "instagram con un","paga con una","indicacion","indicacion indicacion","indicacion","indicacion indicamense","indicaciones de mas","validar","confirmar","corroborar","comprobar","verificar","asegurar","certificar",
        "cuina con la","diana con el","digan con ustedes","financiaciones precisamente","mis indicaciones de","de vacaciones de","financiar con un","inducciones cuatro","inducciones y sabemos",
        "de vacaciones","de vacaciones en","brindarte con la","indicando con que","financiado no te","de vacaciones y","inducciones entonces","nacional tengo","nacional como","indicio de a","nacional en","a ligacion del",
        "nacional como","nacional pues","nacional tengo","nacional como","nacional con","ingresa in direzione","nacional manifiestas","una accion bancaria","nacional como","nacional de","nacional estos","nacional me",
        "tiendi con informacion","ciudad con daniel","viajar con aguas","nacional el","nacional nosotros","ingles con beca","nacional la","nacional y queria","naciones de","nacional estamos","nacional tengo","nacional el",
        "que necesitas","cual problema","como usas","que buscas","cuanto inviertes","por que cambiaste","que esperas","cuando decides","quien decide","que opinas","ya conocias","con que frecuencia","que presupuesto",
        "donde aplicas","que resultados","como manejas","que prioridad","has considerado","te interesa","que impacto","carrera","descubrimos","crecer","carreras","homologar"
    }, 
    "programas": {
        "ingenieria","derecho","administracion","programa","carrera","empresas","tecnica","profesional","administrativos","gestion","administrativa",
        "snies","diseño","grafico","graficos","publicaciones","sistemas","informatica","software","industrial","productivos","modas","vestuario","patronaje",
        "audiovisuales","comunicacion","social","deportiva","seguridad","salud","publicidad","mercadeo","agroindustrial","contaduria",
        "contable","financiera","comerciales","comunicativa","mercados","deportivo","territorial","territoriales"
    },
    "argumentacion": {
        "beca","descuento","financiacion","convenio","modalidad virtual","modalidad presencial","modalidad plus","plataforma","flexibilidad","titulo",
        "perfil egresado","competencias","salidas laborales","costo","valor semestre","inscripcion","metodos de pago","requisitos admision","fechas inscripcion",
        "pasos admision","icfes","homologacion","homologar","documentos homologacion","proceso homologacion","estudio homologacion","contenido programatico",
        "materias homologadas","viabilidad homologacion","solicitud de homologacion","ruta academica post-homologacion","plan homologacion","comparar modalidades",
        "comparar perfiles","comparar financiacion","analizar elegibilidad","analizar materias","analizar diferencias","reingreso","requisito reingreso",
        "proceso reingreso","formulario reingreso","verificar pendientes","elegibilidad reingreso","actualizar informacion","actualizar plan","diferencias actuales",
        "costos actuales","beneficios","requisitos","proceso","titulo previo","modalidad","presencial","virtual","distancia","convenio"
    },
    "objecion": {
        "muy caro","no tengo tiempo","lo pensare","duda","que te preocupa exactamente","entiendo tu punto","podrias contarme mas",
        "que informacion te falta","que dudas tienes","que te impide decidir","comprendo tu inquietud sobre","validamos tu preocupacion","es normal tener preguntas",
        "que necesitas para sentirte seguro/a","inversion vs gasto","retorno de inversion (roi)","valor a largo plazo","opciones de financiacion detalladas","plan de pagos",
        "becas/descuentos aplicables","comparar valor","accesibilidad","presupuesto educativo","financiacion cun","flexibilidad de horarios","modalidad virtual/distancia","estudia a tu ritmo",
        "compatible con trabajo/familia","eficiencia (ciclos prop)","optimizar tiempo","gestion del tiempo","carga academica adaptable","metas profesionales","impacto en carrera","desarrollo personal",
        "oportunidad de mercado","costo de oportunidad (no actuar)","que cambiaria con el titulo","competitividad laboral","proyeccion futura","calidad cun (saber pro)","testimonios","alianzas","trayectoria",
        "soporte del asesor","proceso paso a paso","simplificamos el tramite","plataformas intuitivas (sinu/camiticket)","acompañamiento continuo","reconocimiento men","experiencia estudiantil",
        "que otras opciones consideras","como se compara la cun","programa alternativo cun","explorar otra modalidad","iniciar mas adelante (con seguimiento)","resolver dudas puntuales","estudio gratuito",
        "ahorro significativo vs empezar de cero","costo por credito homologado","financiacion flexible","inversion inteligente","valor del tiempo ahorrado","ahorro de tiempo significativo","avanzar semestres",
        "proceso agil","validacion rapida","menos tiempo de estudio total","proceso estandarizado","requisitos claros","respuesta garantizada","te guio en cada documento","simplificacion documental","soporte cun",
        "reconocimiento de tu esfuerzo previo","construir sobre lo existente","acelerar tu meta profesional","evitar redundancia","valor del titulo completo","optimizar tu formacion","experiencia con otras ies/sena",
        "transparencia","proceso definido","casos de exito homologacion","garantia de respuesta","claridad normativa","revisar estudio de homologacion","considerar otra carrera cun","aclarar dudas especificas del proceso",
        "consultar con coordinacion academica","evaluar plan de estudios detallado","inversion para finalizar","opciones de pago disponibles","presupuesto ajustado","valor de completar titulo","facilidades de pago reintegro",
        "costo vs beneficio final","plan de estudios adaptado","carga academica flexible","organizacion del tiempo","retomar sin perder mas tiempo","actualizacion al plan vigente","soporte academico","completar ciclo",
        "logro personal/profesional","beneficios de finalizar","actualizacion necesaria","mercado laboral actual","superar obstaculos previos","renovar compromiso","soporte para la solicitud","aclaramos requisitos",
        "experiencia previa (como mejoro)","confidencialidad","compromiso institucional","facilidad tramite online","respuesta formal","evaluar transferencia interna","discutir plan de estudios","plan de accion personalizado",
        "aclarar dudas sobre materias/creditos","ciudad","campo"
    },
    "cierre": {
        "te inscribo","te llamo mañana","listo para matricularte","bienvenido","ciclos propedeuticos","3 titulos en 3 años","formacion para el futuro",
        "modalidad flexible","virtual","distancia","presencial entretenida","herramientas digitales","calidad academica","saber pro","portal de empleo",
        "servicios asistenciales","experiencia cun","bachillersitario","inscripcion facil","requisitos sencillos","plataforma sinu","camiticket",
        "admision directa","calendario academico","proceso guiado","te acompañamos","opciones de financiacion","credito educativo","icetex","sufi",
        "banco pichincha","facilidades de pago","inversion educativa","descuentos por convenio","alianzas financieras","becas","gran decision","excelente eleccion",
        "tu mejor version","unete al parche","futuro profesional","inicia ahora","oportunidad unica","empieza tu viaje","bienvenido a la cun","comunidad cunista",
        "confirmar inscripcion","enviar documentos","realizar pago","matricula","induccion","reunir papeles","formalizar admision","legalizar matricula",
        "validar conocimientos","reconocer tu titulo","ahorro tiempo y dinero","avanzar rapido","no empezar de cero","precios justos","hasta 50% homologable",
        "continuidad academica","mejorar perfil profesional","convenio sena","aprovechar estudios previos","estudio gratuito","respuesta rapida (5 dias)",
        "documentacion clara","tramite agil","homologacion en linea","te ayudo con los documentos","paso a paso","proceso simplificado","sin costo",
        "financiacion disponible","pago flexible","aplica financiacion","opciones de credito","facilidades de pago","buen camino","aprovecha tus estudios previos",
        "acelera tu carrera","felicitaciones por continuar","animate a validar","decision inteligente","continua tu formacion","preparar documentos",
        "enviar contenido tematico","enviar notas","esperar estudio","resultado homologacion","matricular asignaturas","formalizar homologacion","retomar estudios",
        "continuar tu formacion","segunda oportunidad","readmision","actualizar conocimientos","finalizar tu carrera","plan vigente","reincorporacion","culminar tu meta",
        "solicitud sencilla","formulario en linea","proceso claro","respuesta oportuna","apoyo en el tramite","fechas habilitadas",
        "requisitos minimos","tramite guiado","opciones de pago","financia tu regreso","planes de pago","credito disponible","facilidades",
        "bienvenido de nuevo","nos alegra tu regreso","retoma con exito","compromiso renovado","finaliza tu meta","estamos para apoyarte",
        "completa tu ciclo","completar solicitud","enviar carta","enviar formulario","esperar aprobacion","confirmar reintegro","realizar pago",
        "inscribir materias","formalizar regreso"
    }
}

requisitos_keywords = {
    "saludo": (1, 1/6),
    "indagacion": (1, 1/6),
    "programas": (1, 1/6),
    "argumentacion": (1, 1/6),
    "objecion": (1, 1/6),
    "cierre": (1, 1/6),
}

# ===================== Utilidades de análisis =====================
def _norm_token(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", s).strip()

def compilar_patrones(diccionarios: dict[str, set[str]]) -> dict[str, re.Pattern]:
    patrones = {}
    for cat, claves in diccionarios.items():
        claves_norm = sorted({_norm_token(c) for c in claves if c and c.strip()})
        if not claves_norm:
            patrones[cat] = re.compile(r"^\b$")
            continue
        altern = "|".join(re.escape(c) for c in claves_norm)
        patrones[cat] = re.compile(rf"(?<!\w)({altern})(?!\w)", flags=re.IGNORECASE)
    return patrones

def normalizar_texto(texto: str) -> str:
    if not isinstance(texto, str): return ""
    t = texto.lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("utf-8")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def etiqueta_sentimiento_por_polarity(p: float) -> str:
    if p >= 0.1:  return "positivo"
    if p <= -0.1: return "negativo"
    return "neutro"

# ===================== Cargar cédulas desde SQL =====================
def cargar_cedulas_por_correo() -> dict:
    """
    Devuelve dict: {correo_lower: cedula_str}
    Consulta: SELECT Identificacion AS cedula, box_mail AS Correo FROM dbo.Planta_Activa
    """
    mapping = {}
    conn = None
    try:
        # Construir conexión (Trusted o usuario/clave)
        if not SQL_SERVER or not SQL_DATABASE:
            raise ValueError("Faltan SQL_SERVER / SQL_DATABASE (usa .env).")
        if SQL_TRUSTED:
            conn_str = (
                f"DRIVER={{{SQL_DRIVER}}};"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                "Trusted_Connection=yes;"
            )
        else:
            if not SQL_USER or not SQL_PASSWORD:
                raise ValueError("Faltan SQL_USER / SQL_PASSWORD o activa SQL_TRUSTED=true.")
            conn_str = (
                f"DRIVER={{{SQL_DRIVER}}};"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"UID={SQL_USER};"
                f"PWD={SQL_PASSWORD};"
                "Trusted_Connection=no;"
            )
        conn = pyodbc.connect(conn_str)
        query = """
            SELECT 
                CAST(Identificacion AS VARCHAR(64)) AS cedula,
                CAST(box_mail AS VARCHAR(320))      AS Correo
            FROM dbo.Planta_Activa
            WHERE box_mail IS NOT NULL AND LTRIM(RTRIM(box_mail)) <> ''
        """
        df_map = pd.read_sql(query, conn)
        df_map["Correo"] = df_map["Correo"].str.strip().str.lower()
        df_map["cedula"] = df_map["cedula"].astype(str).str.strip()
        mapping = dict(zip(df_map["Correo"], df_map["cedula"]))
        print(f"🔗 Cargadas cédulas: {len(mapping)} correos en mapa.")
    except Exception as e:
        print(f"⚠️ No se pudo cargar cédulas desde SQL: {e}")
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
    return mapping

# Clasificador Naive Bayes para 'confianza'
train_data_sentiment = [
    ("Perfecto, entonces quedamos así", "positivo"),
    ("Sí, me interesa el producto", "positivo"),
    ("Muchas gracias por su ayuda", "positivo"),
    ("No me interesa en este momento", "negativo"),
    ("Estoy inconforme con la atención", "negativo"),
]
classifier_sentiment = NaiveBayesClassifier(train_data_sentiment)

# ===================== Normalizador robusto de HORA =====================
def _excel_fraction_to_hhmmss(val: float) -> str:
    # Excel guarda horas como fracción de día (0..1). Acepta 0..2 por si hay fecha+hora.
    try:
        if not (0 <= val < 2):
            return ""
        seconds = int(round((val % 1) * 86400))
        h = (seconds // 3600) % 24
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return ""

def _hora_to_hhmmss(x) -> str:
    if pd.isna(x):
        return ""
    # pandas Timestamp -> datetime
    if hasattr(x, "to_pydatetime"):
        try:
            return x.to_pydatetime().strftime("%H:%M:%S")
        except Exception:
            pass
    # datetime / time
    if isinstance(x, datetime):
        return x.strftime("%H:%M:%S")
    if isinstance(x, time):
        return x.strftime("%H:%M:%S")
    # Timedelta (e.g., '0 days 17:45:00')
    if hasattr(x, "components") and hasattr(x, "total_seconds"):
        try:
            total = int(x.total_seconds())
            h = (total // 3600) % 24
            m = (total % 3600) // 60
            s = total % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            pass
    xs = str(x).strip().replace(",", ".")  # coma decimal → punto
    # Caso típico SQL Server: '17:45:00.0000000' → tomar los 8 primeros HH:MM:SS
    m = re.match(r"^(\d{1,2}:\d{2}:\d{2})", xs)
    if m:
        return m.group(1)
    # Número (Excel fracción de día)
    try:
        fv = float(xs)
        hhmmss = _excel_fraction_to_hhmmss(fv)
        if hhmmss:
            return hhmmss
    except Exception:
        pass
    # Intentos controlados (sin TZ)
    for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
        try:
            return pd.to_datetime(xs, format=fmt).strftime("%H:%M:%S")
        except Exception:
            continue
    # Último recurso
    try:
        ts = pd.to_datetime(xs, errors="coerce")
        return ts.strftime("%H:%M:%S") if pd.notna(ts) else ""
    except Exception:
        return ""

def _to_time7_sql(hhmmss: str) -> str:
    # Convierte 'HH:MM:SS' → 'HH:MM:SS.0000000' (compatible con SQL Server TIME(7))
    return f"{hhmmss}.0000000" if hhmmss else ""

# ===================== Pipeline (limpieza + análisis) =====================
def pipeline_df4(df4: pd.DataFrame, tipo: str = TIPO_POR_DEFECTO) -> pd.DataFrame:
    if df4 is None or df4.empty:
        raise ValueError("df4 está vacío.")

    # 1) Limpieza: elimina CUNDigital/Channel User, etc.
    df_clean = limpiar_df4(df4, dest_col="Transcripción_limpia_v2")
    s_txt = df_clean["Transcripción_limpia_v2"].fillna("").astype(str)

    # 2) Patrones por categoría
    patrones = compilar_patrones(diccionarios_keywords)

    # 3) Conteos por categoría + puntaje/efectiva
    texto_norm = s_txt.map(normalizar_texto)
    conteos_list = [{cat: len(pat.findall(t)) for cat, pat in patrones.items()} for t in texto_norm]
    df_conteos = pd.DataFrame(conteos_list).fillna(0).astype(int)

    puntajes, efectivas = [], []
    for _, row in df_conteos.iterrows():
        p = sum(peso for cat, (minimo, peso) in requisitos_keywords.items()
                if row.get(cat, 0) >= minimo)
        puntajes.append(round(p, 3))
        efectivas.append("1" if p >= 0.8 else "0")

    # 4) Sentimiento (polarity/subjectivity) + clasificación + confianza NB
    polarities, subjects, clasifs, confs, palabras, oraciones = [], [], [], [], [], []
    for txt in s_txt:
        try:
            tb  = TextBlob(txt)
            pol = float(tb.sentiment.polarity)
            sub = float(tb.sentiment.subjectivity)
            palabras.append(len(tb.words))
            oraciones.append(len(tb.sentences))
        except Exception:
            pol, sub = 0.0, 0.0
            palabras.append(0)
            oraciones.append(0)
        try:
            nb_dist = classifier_sentiment.prob_classify(txt)
            nb_pred = nb_dist.max()
            nb_conf = float(nb_dist.prob(nb_pred))
        except Exception:
            nb_conf = 0.5 + 0.5 * min(1.0, abs(pol))
        polarities.append(round(pol, 3))
        subjects.append(round(sub, 3))
        clasifs.append(etiqueta_sentimiento_por_polarity(pol))
        confs.append(round(nb_conf, 2))

    # 5) Metadatos desde df4 (incluye HORA formateada para SQL TIME(7))
    def get_first_present(df, names, default=""):
        for n in names:
            if n in df.columns:
                return df[n]
        return pd.Series([default]*len(df))

    correo_series  = get_first_present(df4, ["correo","Correo","email","Email"]).fillna("").astype(str).str.strip().str.lower()
    asesor_series  = get_first_present(df4, ["asesor","Asesor","agente","Agente","NombreAsesor"]).fillna("").astype(str)
    celular_series = get_first_present(df4, ["Phone_Number","telefono","Teléfono"]).fillna("").astype(str)
    archivo_series = get_first_present(df4, ["Id_url","Conversation_ID","id_conversation"]).fillna("").astype(str)

    if "FechaCreacion" in df4.columns:
        fecha_series = pd.to_datetime(df4["FechaCreacion"], errors="coerce").dt.date.astype("string").fillna(datetime.now().strftime("%Y-%m-%d"))
    else:
        fecha_series = pd.Series([datetime.now().strftime("%Y-%m-%d")]*len(df4), dtype="string")

    # --- Parseo robusto de HORA y formateo final para SQL Server ---
    if "hora" in df4.columns:
        hora_norm = df4["hora"].map(_hora_to_hhmmss).astype(str)  # 'HH:MM:SS'
        hora_series = hora_norm.map(_to_time7_sql)                # 'HH:MM:SS.0000000'
    else:
        hora_series = pd.Series([""]*len(df4), dtype="string")

    # 6) Cargar cédulas desde SQL y mapear por correo
    if USE_SQL_CEDULAS:
        correo_to_cedula = cargar_cedulas_por_correo()
        cedula_series = correo_series.map(lambda c: correo_to_cedula.get(c, ""))
    else:
        cedula_series = pd.Series([""]*len(df4))

    # 7) Armar salida (formato tipo "ventas")
    df_out = pd.DataFrame({
        "correo": correo_series,
        "cedula_asesor": cedula_series,
        "asesor": asesor_series,
        "asesor_corto": asesor_series,
        "fecha": fecha_series,
        **df_conteos.to_dict(orient="list"),
        "puntaje": puntajes,
        "efectiva": efectivas,
        "polarity": polarities,
        "clasificacion": clasifs,
        "confianza": confs,
        "palabras": palabras,
        "oraciones": oraciones,
        "archivo": archivo_series,
        "tamano_B": 250,
        "celular": celular_series,
        "subjectivity": subjects,
        "tipo": tipo,
        # --- HORA (SQL TIME(7)) se reordena al final abajo
        "hora": hora_series.astype(str),
    })

    columnas_salida = [
        "correo","cedula_asesor","asesor","asesor_corto","fecha",
        "saludo","indagacion","programas","argumentacion","objecion","cierre",
        "puntaje","efectiva","polarity","clasificacion","confianza",
        "palabras","oraciones","archivo","tamano_B","celular","subjectivity","tipo",
        "hora"  # <-- al final
    ]
    for c in columnas_salida:
        if c not in df_out.columns:
            df_out[c] = ""
    df_out = df_out[columnas_salida]

    # (Opcional) Si quieres DATETIME2(7) en una sola columna, descomenta:
    # fecha_hora_sql = pd.to_datetime(
    #     df_out["fecha"].astype(str) + " " + df_out["hora"].str.replace(".0000000","", regex=False),
    #     errors="coerce",
    #     format="%Y-%m-%d %H:%M:%S"
    # ).dt.strftime("%Y-%m-%d %H:%M:%S.0000000")
    # df_out.insert(len(df_out.columns), "fecha_hora", fecha_hora_sql)

    return df_out

# ===================== Ejecución directa =====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evalúa chats: limpieza, keywords, sentimiento y (opcional) cédula por correo desde SQL Server.")
    parser.add_argument("--input", default=os.environ.get("INPUT_SRC",""), help="Ruta .xlsx/.csv de entrada.")
    parser.add_argument("--output", default=os.environ.get("OUTPUT_PATH","outputs/chats_evaluados.xlsx"), help="Ruta de salida (xlsx/csv).")
    parser.add_argument("--tipo", default=os.environ.get("TIPO_POR_DEFECTO","chats"), help="Etiqueta de tipo (ej. chats).")
    parser.add_argument("--no-sql", action="store_true", help="Desactiva enriquecimiento de cédulas por SQL.")
    args = parser.parse_args()

    if args.input:
        INPUT_SRC = args.input
    OUTPUT_PATH = args.output
    TIPO_POR_DEFECTO = args.tipo
    if args.no_sql:
        USE_SQL_CEDULAS = False

    # 1) Cargar
    df_in = load_input(INPUT_SRC)

    # 2) Ejecutar pipeline (limpieza + análisis + cédulas)
    df_resultado = pipeline_df4(df_in, tipo=TIPO_POR_DEFECTO)

    # 3) Guardar
    save_output(df_resultado, OUTPUT_PATH)

    # 4) Resumen
    total = len(df_resultado)
    efect = int((df_resultado["efectiva"] == "1").sum()) if "efectiva" in df_resultado.columns else 0
    porc  = (efect/total*100.0) if total else 0.0
    print(f"📊 Filas: {total} | Efectivas: {efect} ({porc:.1f}%)")
