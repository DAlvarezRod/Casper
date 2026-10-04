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


# --- Fase 2: control del sistema ---

def _reset_confirmacion():
    main._confirmacion_pendiente["nombre"] = None
    main._confirmacion_pendiente["funcion"] = None


def test_cmd_estado(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(main.psutil, "cpu_percent", lambda interval=1: 42.0)
    monkeypatch.setattr(main.psutil, "virtual_memory",
                        lambda: SimpleNamespace(percent=55.0, used=4 * 1024**3, total=8 * 1024**3))
    monkeypatch.setattr(main.psutil, "disk_usage", lambda unidad: SimpleNamespace(percent=70.0))
    respuesta = main.cmd_estado()
    assert "42.0" in respuesta and "55.0" in respuesta and "70.0" in respuesta


def test_cmd_captura(monkeypatch):
    from types import SimpleNamespace
    guardadas = []
    fake_imagen = SimpleNamespace(save=lambda nombre: guardadas.append(nombre))
    monkeypatch.setattr(main.ImageGrab, "grab", lambda: fake_imagen)
    respuesta = main.cmd_captura()
    assert len(guardadas) == 1 and guardadas[0].endswith(".png")
    assert guardadas[0] in respuesta


def test_cmd_abrir_app(monkeypatch):
    lanzadas = []
    monkeypatch.setattr(main.os, "name", "nt")
    monkeypatch.setattr(main.subprocess, "Popen", lambda exe: lanzadas.append(exe))
    assert main.cmd_abrir_app("notepad") == "Abriendo notepad..."
    assert lanzadas == ["notepad.exe"]
    assert "No conozco" in main.cmd_abrir_app("photoshop")
    assert "Qué aplicación" in main.cmd_abrir_app("")


def test_cmd_volumen(monkeypatch):
    from types import SimpleNamespace
    pressed = []
    monkeypatch.setattr(main, "pyautogui", SimpleNamespace(press=lambda k: pressed.append(k)))
    assert main.cmd_volumen("subir") == "Volumen: subir"
    assert pressed == ["volumeup"]
    assert "Uso" in main.cmd_volumen("turbo")


def test_cmd_bloquear_windows(monkeypatch):
    from types import SimpleNamespace
    bloqueos = []
    fake_user32 = SimpleNamespace(LockWorkStation=lambda: bloqueos.append(True))
    monkeypatch.setattr(main.os, "name", "nt")
    monkeypatch.setattr(main.ctypes, "windll", SimpleNamespace(user32=fake_user32), raising=False)
    assert main.cmd_bloquear() == "Equipo bloqueado."
    assert bloqueos == [True]


def test_confirmacion_apagar_si(monkeypatch):
    _reset_confirmacion()
    monkeypatch.setattr(main.os, "name", "nt")
    ejecutados = []
    monkeypatch.setattr(main.os, "system", lambda cmd: ejecutados.append(cmd))
    assert "Seguro" in main.cmd_apagar()
    assert "5 segundos" in main.cmd_si()
    assert ejecutados == ["shutdown /s /t 5"]
    # Después de confirmar no queda nada pendiente
    assert main.cmd_si() == "No hay nada que confirmar."


def test_confirmacion_apagar_no():
    _reset_confirmacion()
    main.cmd_apagar()
    assert main.cmd_no() == "Cancelado."
    assert main.cmd_si() == "No hay nada que confirmar."


def test_dispatch_abrir_app_gana_a_abrir(monkeypatch):
    # "abrir app notepad" debe ir a cmd_abrir_app, no a cmd_abrir.
    lanzadas = []
    monkeypatch.setattr(main.os, "name", "nt")
    monkeypatch.setattr(main.subprocess, "Popen", lambda exe: lanzadas.append(exe))
    assert main.process_message("abrir app notepad") == "Abriendo notepad..."
    assert lanzadas == ["notepad.exe"]


def test_dispatch_abrir_sitio_sigue_funcionando(monkeypatch):
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.process_message("abrir youtube") == "Abriendo youtube..."
    assert opened == ["https://www.youtube.com"]


def test_captura_recuerda_ruta(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.chdir(tmp_path)
    main._ultima_captura["ruta"] = None
    fake_imagen = SimpleNamespace(save=lambda ruta: None)
    monkeypatch.setattr(main.ImageGrab, "grab", lambda: fake_imagen)
    respuesta = main.cmd_captura()
    ruta = main._ultima_captura["ruta"]
    assert ruta is not None and os.path.isabs(ruta)
    assert ruta in respuesta


def test_donde_captura():
    main._ultima_captura["ruta"] = None
    assert "ninguna captura" in main.cmd_donde_captura()
    main._ultima_captura["ruta"] = "/tmp/captura_x.png"
    assert "/tmp/captura_x.png" in main.cmd_donde_captura()
    # La frase exacta del usuario también debe funcionar (vía fuzzy matching)
    assert "/tmp/captura_x.png" in main.process_message("donde guardaste esa captura")
