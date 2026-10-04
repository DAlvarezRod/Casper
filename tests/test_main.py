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


def test_cmd_abrir_youtube(monkeypatch):
    # monkeypatch reemplaza webbrowser.open por una función falsa,
    # así la prueba no abre un navegador de verdad.
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.cmd_abrir_youtube() == "Abriendo YouTube..."
    assert opened == ["https://www.youtube.com"]
