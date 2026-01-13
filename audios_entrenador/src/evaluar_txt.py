# -*- coding: utf-8 -*-
"""
Pipeline de evaluación de .txt + merge con metadatos (call_id, fecha, numero_vapi, numero10_vapi)
Requisitos:
  pip install pandas textblob pyodbc openpyxl
"""

from __future__ import annotations
import os, re, unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from dotenv import load_dotenv

load_dotenv()

# ===================== CONFIG =====================
# Carpeta de entrada con .txt
INPUT_TXT_DIR = os.environ.get("INPUT_TXT_DIR", r"inputs\txt")
# Carpeta de salida
OUTPUT_DIR    = os.environ.get("OUTPUT_DIR", r"outputs")

# --- META DESDE SQL SERVER ---
SQL_SERVER = os.environ.get("SQL_SERVER", "")
SQL_DB     = os.environ.get("SQL_DB", "")
# Autenticación integrada:
SQL_DRIVER  = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
SQL_TRUSTED = os.environ.get("SQL_TRUSTED", "true").lower() in {"1","true","yes","y"}
SQL_USER    = os.environ.get("SQL_USER", "")
SQL_PASSWORD= os.environ.get("SQL_PASSWORD", "")

def build_sql_connstr() -> str:
    if not SQL_SERVER or not SQL_DB:
        raise ValueError("Faltan SQL_SERVER / SQL_DB en .env (o variables de entorno).")
    if SQL_TRUSTED:
        return (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};DATABASE={SQL_DB};Trusted_Connection=yes;"
        )
    if not SQL_USER or not SQL_PASSWORD:
        raise ValueError("Faltan SQL_USER / SQL_PASSWORD o activa SQL_TRUSTED=true.")
    return (
        f"DRIVER={{{SQL_DRIVER}}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DB};UID={SQL_USER};PWD={SQL_PASSWORD};Trusted_Connection=no;"
    )

# Filtro opcional de fechas del meta (semi-abierto). Deja None para no filtrar.
META_DESDE     = os.environ.get("META_DESDE", None) or None
META_HASTA_EXC = os.environ.get("META_HASTA_EXC", None) or None

# Tipo marcador de salida
TIPO = "entrenador"

# Si no hay fecha en meta para algún call_id, se usa esta por defecto:
FECHA_ANALISIS_DEF = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# ==================================================


# ====== DICCIONARIOS DE CATEGORÍAS  ====
DICCIONARIOS_KEYWORDS: Dict[str, List[str]] = {
    "saludo": [
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
    ],
    "indagacion": [
        "alguna vez has considerado la posibilidad de estudiar algo mas","hay algun tema que siempre te haya llamado la atencion y que quizas te gustaria estudiar","te has preguntado como seria estudiar",
        "te gustaria estudiar en la cun","que opinas sobre la educacion continua o el aprendizaje a lo largo de la vida","crees que en algun momento te gustaria ampliar tus conocimientos a traves de estudios",
        "te ves volviendo a estudiar en el futuro","que factores te harian considerar seriamente la opcion de estudiar","hay algo que te gustaria aprender o profundizar si tuvieras la oportunidad",
        "que tipo de habilidades o conocimientos te gustaria adquirir","te interesa el desarrollo personal y profesional a traves de la educacion","has visto algun programa o curso que te haya parecido interesante",
        "que piensas sobre la idea de invertir tiempo y recursos en tu formacion","crees que estudiar podria abrirte nuevas puertas en el futuro","que te detendria de estudiar en este momento",
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
        "instagram con un","paga con una","indicacion","indicacion indicacion","indicacion","indicacion indicamense","indicaciones de mas",
        "validar","confirmar","corroborar","comprobar","verificar","asegurar","certificar",
        "cuina con la","diana con el","digan con ustedes","financiaciones precisamente","mis indicaciones de","de vacaciones de",
        "financiar con un","inducciones cuatro","inducciones y sabemos","de vacaciones","de vacaciones en","brindarte con la",
        "indicando con que","financiado no te","de vacaciones y","inducciones entonces","nacional tengo","nacional como",
        "indicio de a","nacional en","a ligacion del","nacional como","nacional pues","nacional tengo","nacional como",
        "nacional con","ingresa in direzione","nacional manifiestas","una accion bancaria","nacional como","nacional de",
        "nacional estos","nacional me","tiendi con informacion","ciudad con daniel","viajar con aguas","nacional el",
        "nacional nosotros","ingles con beca","nacional la","nacional y queria","naciones de","nacional estamos","nacional tengo",
        "nacional el","que necesitas","cual problema","como usas","que buscas","cuanto inviertes","por que cambiaste","que esperas",
        "cuando decides","quien decide","que opinas","ya conocias","con que frecuencia","que presupuesto","donde aplicas","que resultados",
        "como manejas","que prioridad","has considerado","te interesa","que impacto","carrera","descubrimos","crecer","carreras","homologar"
    ],
    "programas": [
        "ingenieria","derecho","administracion","programa","carrera","empresas","tecnica","profesional","administrativos","gestion","administrativa",
        "snies","diseño","grafico","graficos","publicaciones","sistemas","informatica","software","industrial","productivos","modas","vestuario","patronaje",
        "audiovisuales","comunicacion","social","deportiva","seguridad","salud","publicidad","mercadeo","agroindustrial","contaduria",
        "contable","financiera","comerciales","comunicativa","mercados","deportivo","territorial","territoriales"
    ],
    "argumentacion": [
        "beca","descuento","financiacion","convenio","modalidad virtual","modalidad presencial","modalidad plus","plataforma","flexibilidad","titulo",
        "perfil egresado","competencias","salidas laborales","costo","valor semestre","inscripcion","metodos de pago","requisitos admision","fechas inscripcion",
        "pasos admision","icfes","homologacion","homologar","documentos homologacion","proceso homologacion","estudio homologacion","contenido programatico",
        "materias homologadas","viabilidad homologacion","solicitud de homologacion","ruta academica post-homologacion","plan homologacion","comparar modalidades",
        "comparar perfiles","comparar financiacion","analizar elegibilidad","analizar materias","analizar diferencias","reingreso","requisito reingreso",
        "proceso reingreso","formulario reingreso","verificar pendientes","elegibilidad reingreso","actualizar informacion","actualizar plan","diferencias actuales",
        "costos actuales","beneficios","requisitos","proceso","titulo previo","modalidad","presencial","virtual","distancia","convenio"
    ],
    "objecion": [        
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
    ],
    "cierre": [
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
        "solicitud sencilla","formulario en linea","proceso claro","respuesta oportuna","apoyo en el tramite","fechas habilitadas","requisitos minimos","tramite guiado",
        "opciones de pago","financia tu regreso","planes de pago","credito disponible","facilidades","bienvenido de nuevo","nos alegra tu regreso","retoma con exito",
        "compromiso renovado","finaliza tu meta","estamos para apoyarte","completa tu ciclo","completar solicitud","enviar carta","enviar formulario","esperar aprobacion",
        "confirmar reintegro","realizar pago","inscribir materias","formalizar regreso"
    ],
}

# Requisitos mínimos y pesos para puntaje (ajústalo a tu rúbrica)
REQ_PESOS: Dict[str, Tuple[int, float]] = {
    "saludo":        (1, 0.10),
    "indagacion":    (1, 0.20),
    "programas":     (1, 0.20),
    "argumentacion": (1, 0.25),
    "objecion":      (1, 0.10),
    "cierre":        (1, 0.15),
}

UMBRAL_EFECTIVA = 0.80
# ==================================================


# ============== UTILIDADES DE TEXTO ================
def quitar_acentos(s: str) -> str:
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def normalizar_texto(s: str) -> str:
    s = s.replace("\r", " ").replace("\n", " ")
    s = quitar_acentos(s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s

def compilar_patrones(dic: Dict[str, List[str]]) -> Dict[str, List[re.Pattern]]:
    patrones: Dict[str, List[re.Pattern]] = {}
    for cat, frases in dic.items():
        pats = []
        for frase in frases:
            f = re.escape(normalizar_texto(frase))
            pats.append(re.compile(rf"(?<!\w){f}(?!\w)"))
        patrones[cat] = pats
    return patrones

def contar_por_categoria(texto_norm: str, patrones: Dict[str, List[re.Pattern]]) -> Dict[str, int]:
    res: Dict[str, int] = {}
    for cat, pats in patrones.items():
        total = 0
        for p in pats:
            total += len(p.findall(texto_norm))
        res[cat] = total
    return res

def segmentar_oraciones(texto: str) -> List[str]:
    if not texto:
        return []
    partes = re.split(r"[.!?¡¿;\n\r]+", texto)
    return [p.strip() for p in partes if p.strip()]

def contar_palabras(texto: str) -> int:
    if not texto:
        return 0
    return len(re.findall(r"\w+", texto, flags=re.UNICODE))
# ==================================================


# ====== EXTRACCIÓN DESDE NOMBRE / TEXTO ===========
def extraer_call_id_desde_archivo(nombre_txt: str) -> str:
    # Asume "<call_id>.txt" (ej: "000d90e3-bd95-....txt")
    return Path(nombre_txt).stem.strip()

def extraer_celular_desde_texto(texto: str) -> str:
    m = re.search(r"(\+?57)?\s?(\d{10})", texto)
    if m:
        return (m.group(1) or "") + (m.group(2) or "")
    m2 = re.search(r"\+?\d{7,12}", texto)
    return m2.group(0) if m2 else ""
# ==================================================


# ============== SENTIMIENTO (TextBlob opcional) ===
def sentimiento_textblob(texto: str) -> Tuple[float, float]:
    try:
        from textblob import TextBlob
        tb = TextBlob(texto)
        return float(tb.sentiment.polarity), float(tb.sentiment.subjectivity)
    except Exception:
        # Fallback sencillo
        texto_n = normalizar_texto(texto)
        pos = {"excelente", "bueno", "genial", "me gusta", "agradable", "perfecto", "gracias"}
        neg = {"malo", "pesimo", "caro", "no me gusta", "terrible", "problema", "queja"}
        ppos = sum(texto_n.count(w) for w in pos)
        pneg = sum(texto_n.count(w) for w in neg)
        pol = 0.0 if (ppos + pneg) == 0 else (ppos - pneg) / (ppos + pneg)
        return float(pol), 0.0
# ==================================================


# ============== NORMALIZACIÓN NÚMERO (10 dígitos) =
def numero10_desde_numero_vapi(num: str) -> str:
    """
    Devuelve los últimos 10 dígitos del número (remueve todo lo no numérico).
    Maneja prefijos +57, 57, 0057, espacios, guiones, etc.
    """
    if num is None:
        return ""
    digits = re.sub(r"\D+", "", str(num))
    if not digits:
        return ""
    # Últimos 10 dígitos (estándar Colombia)
    return digits[-10:]
# ==================================================


# ============== META DESDE SQL =====================
def cargar_meta_desde_sql() -> pd.DataFrame:
    import pyodbc
    conn = pyodbc.connect(build_sql_connstr())
    where_parts = []
    if META_DESDE:
        where_parts.append(f"started_at >= CONVERT(datetime2(7), '{META_DESDE}T00:00:00', 126)")
    if META_HASTA_EXC:
        where_parts.append(f"started_at <  CONVERT(datetime2(7), '{META_HASTA_EXC}T00:00:00', 126)")
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    query = f"""
    SELECT
        call_id,
        number      AS numero_vapi,
        started_at  AS fecha,
        recording_url
    FROM dbo.vapi_entrenador
    {where_sql};
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Normaliza columnas y tipos
    df = df.rename(columns={"started_at": "fecha", "number": "numero_vapi"})
    df["call_id"] = df["call_id"].astype(str).str.lower().str.strip()
    df["numero_vapi"] = df["numero_vapi"].astype(str).str.strip()
    # numero10_vapi normalizado
    df["numero10_vapi"] = df["numero_vapi"].apply(numero10_desde_numero_vapi)
    # fecha a string estándar (opcional)
    try:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        pass
    return df[["call_id", "numero_vapi", "numero10_vapi", "fecha", "recording_url"]]
# ==================================================


# ============== PIPELINE PRINCIPAL ===============
def analizar_txts_y_exportar(df_meta: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    inp = Path(INPUT_TXT_DIR)
    outdir = Path(OUTPUT_DIR)
    outdir.mkdir(parents=True, exist_ok=True)

    # Recolecta .txt
    txt_files: List[Path] = []
    for dp, _, files in os.walk(inp):
        for f in files:
            if f.lower().endswith(".txt"):
                txt_files.append(Path(dp) / f)
    if not txt_files:
        print(f"❌ No encontré .txt en: {inp}")
        return pd.DataFrame()

    patrones = compilar_patrones(DICCIONARIOS_KEYWORDS)

    filas: List[dict] = []
    for p in txt_files:
        # Lee texto
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            texto = p.read_text(encoding="latin-1", errors="ignore")

        texto_norm = normalizar_texto(texto)

        # Conteos por categoría
        conteos = contar_por_categoria(texto_norm, patrones)

        # Puntaje
        puntaje = 0.0
        for cat, (min_req, peso) in REQ_PESOS.items():
            if conteos.get(cat, 0) >= min_req:
                puntaje += peso
        efectiva = "1" if puntaje >= UMBRAL_EFECTIVA else "0"

        # Sentimiento + métricas básicas
        polarity, subjectivity = sentimiento_textblob(texto)
        palabras   = contar_palabras(texto)
        oraciones  = len(segmentar_oraciones(texto))
        tamano_B   = p.stat().st_size if p.exists() else 0

        # call_id y celular desde texto
        call_id = extraer_call_id_desde_archivo(p.name)
        celular_txt = extraer_celular_desde_texto(texto)

        filas.append({
            "correo": None,
            "cedula_asesor": None,
            "asesor": None,
            "asesor_corto": None,
            "fecha": FECHA_ANALISIS_DEF,  # será reemplazada con meta si existe
            "saludo": conteos.get("saludo", 0),
            "indagacion": conteos.get("indagacion", 0),
            "programas": conteos.get("programas", 0),
            "argumentacion": conteos.get("argumentacion", 0),
            "objecion": conteos.get("objecion", 0),
            "cierre": conteos.get("cierre", 0),
            "puntaje": round(puntaje, 3),
            "efectiva": efectiva,
            "polarity": round(polarity, 3),
            "clasificacion": ("positivo" if polarity >= 0.1 else "negativo" if polarity <= -0.1 else "neutro"),
            "confianza": round(0.5 + abs(polarity)/2, 2),
            "palabras": palabras,
            "oraciones": oraciones,
            "archivo": p.name,
            "call_id": str(call_id),
            "numero_vapi": "",           # se llenará con meta
            "numero10_vapi": "",         # se calculará desde numero_vapi
            "tamano_B": tamano_B,
            "celular_texto": celular_txt,
            "subjectivity": round(subjectivity, 3),
            "tipo": TIPO,
            "recording_url": "",         # se llenará con meta
        })

    df_out = pd.DataFrame(filas)

    # --- normaliza call_id para merge ---
    df_out["call_id"] = df_out["call_id"].astype(str).str.lower().str.strip()

    # ========= MERGE con df_meta =========
    if df_meta is not None and not df_meta.empty:
        meta = df_meta.copy()

        # Asegura nombres esperados
        rename_map = {}
        if "started_at" in meta.columns and "fecha" not in meta.columns:
            rename_map["started_at"] = "fecha"
        if "number" in meta.columns and "numero_vapi" not in meta.columns:
            rename_map["number"] = "numero_vapi"
        if rename_map:
            meta = meta.rename(columns=rename_map)

        # Columnas útiles
        cols_keep = ["call_id", "fecha", "numero_vapi", "numero10_vapi", "recording_url"]
        meta = meta[[c for c in cols_keep if c in meta.columns]].copy()

        # Tipos limpios + normalización para join
        meta["call_id"] = meta["call_id"].astype(str).str.lower().str.strip()
        if "numero_vapi" in meta.columns:
            meta["numero_vapi"] = meta["numero_vapi"].astype(str).str.strip()

        # Si no viene numero10_vapi en meta, lo calculamos desde numero_vapi
        if "numero10_vapi" not in meta.columns and "numero_vapi" in meta.columns:
            meta["numero10_vapi"] = meta["numero_vapi"].apply(numero10_desde_numero_vapi)

        # Formatea fecha si viene como datetime
        if "fecha" in meta.columns:
            try:
                meta["fecha"] = pd.to_datetime(meta["fecha"]).dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                pass

        # MERGE
        df_out = df_out.merge(meta, on="call_id", how="left", suffixes=("", "_meta"))

        # Reemplaza fecha por la de meta si existe
        if "fecha_meta" in df_out.columns:
            df_out["fecha"] = df_out["fecha_meta"].combine_first(df_out["fecha"])
            df_out = df_out.drop(columns=["fecha_meta"])

        # Rellena numero_vapi, numero10_vapi y recording_url desde meta
        for c in ["numero_vapi", "numero10_vapi", "recording_url"]:
            if c + "_meta" in df_out.columns:
                df_out[c] = df_out[c].where(df_out[c].ne(""), df_out[c + "_meta"])
                df_out = df_out.drop(columns=[c + "_meta"])

    # Si quedó numero10_vapi vacío pero tenemos numero_vapi, lo calculamos aquí
    mask_vacios = (df_out["numero10_vapi"] == "") & (df_out["numero_vapi"] != "")
    df_out.loc[mask_vacios, "numero10_vapi"] = df_out.loc[mask_vacios, "numero_vapi"].apply(numero10_desde_numero_vapi)

    # ========= Orden y export =========
    columnas_salida = [
        "correo","cedula_asesor","asesor","asesor_corto","fecha",
        "saludo","indagacion","programas","argumentacion","objecion","cierre",
        "puntaje","efectiva","polarity","clasificacion","confianza",
        "palabras","oraciones","archivo","call_id",
        "numero_vapi","numero10_vapi","recording_url",
        "tamano_B","celular_texto","subjectivity","tipo"
    ]
    for c in columnas_salida:
        if c not in df_out.columns:
            df_out[c] = ""

    df_out = df_out[columnas_salida]

    base = os.environ.get("EXPORT_BASENAME", f"Entrenador_TXT_{datetime.now().strftime('%Y-%m-%d')}")
    xlsx = Path(OUTPUT_DIR) / f"{base}.xlsx"
    csv  = Path(OUTPUT_DIR) / f"{base}.csv"

    try:
        df_out.to_excel(xlsx, index=False)
        print(f"✅ Excel generado: {xlsx}")
    except Exception as e:
        print(f"⚠️ No se pudo escribir XLSX ({e}). Guardando CSV…")
        df_out.to_csv(csv, index=False, encoding="utf-8-sig")
        print(f"✅ CSV generado: {csv}")

    print(f"📊 Registros procesados: {len(df_out)} | Efectivas: {(df_out['efectiva']=='1').sum()}")
    print("🔎 Con numero_vapi:", (df_out["numero_vapi"] != "").sum(),
          "| Con numero10_vapi:", (df_out["numero10_vapi"] != "").sum())
    return df_out
# ================================================


# ============== MAIN =============================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evalúa transcripciones (.txt) de audios del entrenador y cruza metadatos desde SQL.")
    parser.add_argument("--input-txt-dir", default=os.environ.get("INPUT_TXT_DIR", INPUT_TXT_DIR), help="Carpeta con .txt")
    parser.add_argument("--output-dir", default=os.environ.get("OUTPUT_DIR", OUTPUT_DIR), help="Carpeta de salida")
    parser.add_argument("--no-sql", action="store_true", help="No consultar metadatos en SQL (solo procesa .txt).")
    parser.add_argument("--meta-desde", default=os.environ.get("META_DESDE", META_DESDE or ""), help="Fecha inicio (YYYY-MM-DD) para filtrar meta.")
    parser.add_argument("--meta-hasta", default=os.environ.get("META_HASTA_EXC", META_HASTA_EXC or ""), help="Fecha fin excluyente (YYYY-MM-DD) para filtrar meta.")
    parser.add_argument("--export-basename", default=os.environ.get("EXPORT_BASENAME", ""), help="Nombre base del export (sin extensión).")
    args = parser.parse_args()

    global INPUT_TXT_DIR, OUTPUT_DIR, META_DESDE, META_HASTA_EXC
    INPUT_TXT_DIR = args.input_txt_dir
    OUTPUT_DIR = args.output_dir
    META_DESDE = args.meta_desde or None
    META_HASTA_EXC = args.meta_hasta or None
    if args.export_basename:
        os.environ["EXPORT_BASENAME"] = args.export_basename

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if args.no_sql:
        df_meta = pd.DataFrame()
    else:
        try:
            df_meta = cargar_meta_desde_sql()
            print(f"ℹ️ df_meta: {len(df_meta)} filas (rango {META_DESDE or '-inf'} .. {META_HASTA_EXC or '+inf'})")
        except Exception as e:
            print(f"⚠️ No pude leer meta desde SQL: {e}")
            df_meta = pd.DataFrame()

    df_final = analizar_txts_y_exportar(df_meta=df_meta)
    if not df_final.empty:
        print(df_final.head(5))


if __name__ == "__main__":
    main()
