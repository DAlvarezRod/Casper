"""Pruebas para Casper. Se ejecutan con: python -m pytest

Cada prueba comprueba que una parte pequeña del programa hace lo que
debería. Si alguna falla, pytest dice exactamente cuál y por qué.
"""
import os
import re
import sys

# Agrega la carpeta src al path para poder importar main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import main


def test_strip_accents():
    assert main.strip_accents("Quién") == "Quien"
    assert main.strip_accents("canción") == "cancion"
    # Sin acentos no cambia nada
    assert main.strip_accents("hola") == "hola"


def test_normalize_text():
    assert main.normalize_text("¿Quién eres?") == "quien eres"
    assert main.normalize_text("  HOLA!!!  ") == "hola"
    assert main.normalize_text("Salir") == "salir"


def test_process_message_exact():
    assert main.process_message("hola") == "Hola. ¿En que puedo ayudarte?"
    assert main.process_message("quien eres") == "Soy Casper, tu asistente personal"
    assert main.process_message("salir") == "salir"


def test_process_message_prefix():
    # "que dia es hoy" no es un comando exacto,
    # pero empieza con "que dia es" y debe funcionar igual.
    assert main.process_message("que dia es hoy").startswith("Hoy es")
    assert main.process_message("que hora es por favor").startswith("Son las")


def test_process_message_unknown():
    assert main.process_message("dime un chiste") == "Todavia no se como responder a eso"


def test_cmd_hora_format():
    # La hora debe tener el formato "Son las HH:MM"
    assert re.fullmatch(r"Son las \d{2}:\d{2}", main.cmd_hora())


def test_cmd_abrir_known_site(monkeypatch):
    # monkeypatch reemplaza webbrowser.open por una función falsa,
    # así la prueba no abre un navegador de verdad.
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.cmd_abrir("youtube") == "Abriendo youtube..."
    assert opened == ["https://www.youtube.com"]


def test_cmd_abrir_unknown_site_uses_google(monkeypatch):
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.cmd_abrir("stack overflow") == "Abriendo stack overflow..."
    assert opened == ["https://www.google.com/search?q=stack+overflow"]


def test_cmd_abrir_without_argument():
    assert main.cmd_abrir("") == "¿Qué sitio quieres que abra?"


def test_process_message_with_argument(monkeypatch):
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.process_message("abrir github") == "Abriendo github..."
    assert opened == ["https://github.com"]


def test_cmd_fecha_en_espanol():
    # El dia debe salir en español sin importar el idioma del sistema.
    from datetime import datetime
    esperado = main.DIAS_ES[datetime.now().weekday()]
    respuesta = main.cmd_fecha()
    assert esperado in respuesta
    assert respuesta.startswith("Hoy es ")


def test_fuzzy_match_typos():
    # Typos comunes deben resolverse al comando correcto.
    assert main.process_message("holaa") == "Hola. ¿En que puedo ayudarte?"
    assert main.process_message("ola") == "Hola. ¿En que puedo ayudarte?"
    assert main.process_message("que ora es").startswith("Son las")


def test_fuzzy_match_rejects_gibberish():
    # Texto sin parecido a ningun comando sigue siendo desconocido.
    assert main.process_message("xyz") == "Todavia no se como responder a eso"
    assert main.process_message("qwerty") == "Todavia no se como responder a eso"


def test_fuzzy_match_arg_command(monkeypatch):
    # Typos en la primera palabra de un comando con argumento tambien funcionan.
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.process_message("avrir youtube") == "Abriendo youtube..."
    assert opened == ["https://www.youtube.com"]
