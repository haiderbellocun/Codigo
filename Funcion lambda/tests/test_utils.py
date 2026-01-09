\
import re
from src.app import extract_email_from_key, sanitize_job_name

def test_extract_email_from_key():
    key = "Grabaciones/juan.perez@cun.edu.co/llamada.wav"
    assert extract_email_from_key(key) == "juan.perez@cun.edu.co"

def test_extract_email_none():
    key = "Grabaciones/sin_correo/llamada.wav"
    assert extract_email_from_key(key) is None

def test_sanitize_job_name_length():
    key = "a" * 1000 + ".wav"
    name = sanitize_job_name(key)
    assert len(name) <= 200
