# -*- coding: utf-8 -*-
"""
Función Lambda para transcribir archivos de audio de S3 usando Amazon Transcribe.
Organiza las salidas en una carpeta única por día.
"""
import os
import json
import re
import urllib.parse
from datetime import datetime
from io import BytesIO # <--- Añadido para la mejora de Pandas

import boto3
from botocore.exceptions import ClientError
import pandas as pd

# ===================== CONFIG (leído de variables de entorno) =====================
REGION = os.environ.get("REGION", "us-east-1")
OUT_BUCKET = os.environ.get("OUT_BUCKET", "")
OUT_PREFIX = os.environ.get("OUT_PREFIX", "txt/prue") # Usamos el valor de tu config
LANGUAGE = os.environ.get("LANGUAGE", "auto")
SPEAKERS = int(os.environ.get("SPEAKERS", "0") or "0")
BASE_VENTAS_BUCKET = os.environ.get("BASE_VENTAS_BUCKET", "")
BASE_VENTAS_KEY = os.environ.get("BASE_VENTAS_KEY", "")

# ===================== AWS CLIENTS =====================
transcribe = boto3.client("transcribe", region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)

# ===================== CACHÉ Y LECTOR DE EXCEL =====================
APROBADOS_CACHE = None

def get_lista_aprobados() -> set:
    global APROBADOS_CACHE
    if APROBADOS_CACHE is not None:
        return APROBADOS_CACHE

    print("COLD START: Cargando la lista de correos desde el archivo Excel usando Pandas...")
    try:
        if not BASE_VENTAS_BUCKET or not BASE_VENTAS_KEY:
            raise ValueError("Variables de entorno BASE_VENTAS_BUCKET/KEY no configuradas.")
            
        obj = s3_client.get_object(Bucket=BASE_VENTAS_BUCKET, Key=BASE_VENTAS_KEY)
        excel_data = obj['Body'].read()
        df = pd.read_excel(BytesIO(excel_data)) # <-- Usando BytesIO para eliminar la advertencia
        
        df.columns = [str(col).lower() for col in df.columns]

        email_col = 'correo' if 'correo' in df.columns else 'email'
        if email_col not in df.columns:
            raise ValueError("No se encontró la columna 'correo' o 'email' en el archivo Excel.")

        correos = set(df[email_col].dropna().astype(str).str.strip().str.lower())
        
        print(f"Lista cargada exitosamente. Se encontraron {len(correos)} correos aprobados.")
        
        APROBADOS_CACHE = correos
        return APROBADOS_CACHE
        
    except Exception as e:
        print(f"ERROR CRÍTICO: No se pudo cargar la lista de aprobación. Error: {e}")
        APROBADOS_CACHE = set() 
        return APROBADOS_CACHE

# ===================== FUNCIONES AUXILIARES =====================

def extract_email_from_key(key: str) -> str | None:
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', key)
    return match.group(0).lower() if match else None

def sanitize_job_name(key: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(key))
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return f"tr-{ts}-{base}"[:200]

# ===================== HANDLER PRINCIPAL =====================

def lambda_handler(event, context):
    lista_aprobados = get_lista_aprobados()
    if not lista_aprobados:
        print("La lista de aprobación está vacía o no se pudo cargar.")
        return {'statusCode': 200, 'body': 'Lista de aprobación vacía.'}

    record = event['Records'][0]
    in_bucket = record['s3']['bucket']['name']
    in_key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')

    correo = extract_email_from_key(in_key)
    if not correo:
        print(f"No se pudo extraer correo de la ruta '{in_key}'. Omitiendo.")
        return {'statusCode': 200, 'body': 'No se encontró correo en la ruta.'}

    if correo not in lista_aprobados:
        print(f"Correo '{correo}' NO APROBADO. Omitiendo transcripción.")
        return {'statusCode': 200, 'body': 'Correo no aprobado.'}

    print(f"Correo '{correo}' APROBADO. Iniciando proceso de transcripción.")

    s3_uri = f"s3://{in_bucket}/{in_key}"
    job_name = sanitize_job_name(in_key)
    media_format = in_key.split('.')[-1].lower()
    
    # --- INICIO DEL CAMBIO IMPORTANTE ---
    # Crear un nombre de carpeta único para el día actual.
    nombre_carpeta_diaria = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Construimos la ruta de salida EXACTAMENTE como la pediste:
    # (prefijo_salida)/(carpeta_diaria)/Grabaciones
    output_path = os.path.join(OUT_PREFIX, nombre_carpeta_diaria, "Grabaciones")
    # --- FIN DEL CAMBIO IMPORTANTE ---

    transcribe_params = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": s3_uri},
        "MediaFormat": media_format,
        "OutputBucketName": OUT_BUCKET,
        "OutputKey": output_path + "/" 
    }

    if LANGUAGE == "auto":
        transcribe_params["IdentifyLanguage"] = True
    else:
        transcribe_params["LanguageCode"] = LANGUAGE

    if SPEAKERS >= 2:
        transcribe_params["Settings"] = {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": SPEAKERS
        }

    try:
        transcribe.start_transcription_job(**transcribe_params)
        print(f"Trabajo '{job_name}' iniciado correctamente. Salida en: {output_path}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"El trabajo '{job_name}' ya existe.")
        else:
            raise e
            
    return {
        'statusCode': 200,
        'body': f'Proceso de transcripción iniciado para {in_key}'
    }