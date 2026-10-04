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
    # "dime un chiste" ahora SÍ es un comando; usamos otra frase desconocida.
    assert main.process_message("dime un poema") == main.RESPUESTA_DESCONOCIDA


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
    assert main.process_message("xyz") == main.RESPUESTA_DESCONOCIDA
    assert main.process_message("qwerty") == main.RESPUESTA_DESCONOCIDA


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


# --- Comandos nuevos: normalización que conserva caracteres ---

def test_normalize_preserva_caracteres_matematicos():
    # Los caracteres con significado para "calcular" no se eliminan.
    assert main.normalize_text("calcular 3.5 * (2 + 1)") == "calcular 3.5 * (2 + 1)"
    # Pero la decoración sí se sigue limpiando.
    assert main.normalize_text("¡¡hola!!!") == "hola"


def test_cmd_calcular():
    assert main.cmd_calcular("2 + 3 * 4") == "14"
    assert main.cmd_calcular("(10 - 4) / 2") == "3.0"
    assert main.cmd_calcular("2 ** 10") == "1024"
    assert main.cmd_calcular("3.5 * 2") == "7.0"
    assert main.cmd_calcular("3,5 * 2") == "7.0"  # coma decimal española
    assert main.cmd_calcular("") == "¿Qué quieres calcular? Ejemplo: calcular 15 * 3 + 2"
    assert main.cmd_calcular("1 / 0") == "No puedo dividir por cero."


def test_cmd_calcular_rechaza_codigo():
    # Un intento de inyección de código debe ser rechazado, no ejecutado.
    assert "Solo puedo calcular" in main.cmd_calcular("__import__('os').system('x')")
    assert "Solo puedo calcular" in main.cmd_calcular("open('/etc/passwd').read()")


def test_cmd_chiste():
    assert main.cmd_chiste() in main.CHISTES


def test_cmd_dado_moneda_azar():
    for _ in range(20):
        assert 1 <= int(main.cmd_dado().split(": ")[1]) <= 6
        assert main.cmd_moneda().split(": ")[1] in ("cara", "sello")
        assert 1 <= int(main.cmd_azar("1 10").split(": ")[1]) <= 10
    assert "Uso" in main.cmd_azar("10")
    assert "mayor" in main.cmd_azar("10 1")


def test_notas_flujo_completo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert main.cmd_nota("") == "¿Qué quieres anotar? Ejemplo: nota comprar leche"
    assert main.cmd_nota("comprar leche") == "Nota 1 guardada."
    assert main.cmd_nota("llamar al banco") == "Nota 2 guardada."
    listado = main.cmd_ver_notas()
    assert "comprar leche" in listado and "llamar al banco" in listado
    assert "Nota borrada" in main.cmd_borrar_nota("1")
    assert "comprar leche" not in main.cmd_ver_notas()
    assert "Uso" in main.cmd_borrar_nota("99")
    assert "Uso" in main.cmd_borrar_nota("abc")


def test_notas_persisten_en_disco(monkeypatch, tmp_path):
    import json
    monkeypatch.chdir(tmp_path)
    main.cmd_nota("persistencia real")
    with open("notas.json", encoding="utf-8") as f:
        datos = json.load(f)
    assert datos[0]["texto"] == "persistencia real"


def test_tareas_flujo_completo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert main.cmd_tarea("estudiar") == "Tarea 1 agregada."
    assert main.cmd_tarea("hacer ejercicio") == "Tarea 2 agregada."
    listado = main.cmd_ver_tareas()
    assert "[ ]" in listado and "estudiar" in listado
    assert "completada" in main.cmd_completar_tarea("1")
    assert "[x]" in main.cmd_ver_tareas()
    assert "Uso" in main.cmd_completar_tarea("99")


def test_cmd_bateria(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(main.psutil, "sensors_battery", lambda: None)
    assert "batería" in main.cmd_bateria()
    monkeypatch.setattr(main.psutil, "sensors_battery",
                        lambda: SimpleNamespace(percent=80, power_plugged=True))
    assert main.cmd_bateria() == "Batería: 80% (cargando)"


def test_cmd_temporizador_invalido():
    assert "Uso" in main.cmd_temporizador("")
    assert "Uso" in main.cmd_temporizador("abc")
    assert "Uso" in main.cmd_temporizador("-5")


def test_cmd_temporizador_valido(monkeypatch):
    creados = []
    class FakeTimer:
        def __init__(self, segundos, funcion):
            creados.append((segundos, funcion))
        def start(self):
            pass
    monkeypatch.setattr(main.threading, "Timer", FakeTimer)
    assert main.cmd_temporizador("5") == "Temporizador de 5 minutos iniciado."
    assert creados[0][0] == 300


def test_cmd_ayuda_lista_comandos():
    ayuda = main.cmd_ayuda()
    for palabra in ["calcular", "nota", "tarea", "abrir", "chiste", "temporizador"]:
        assert palabra in ayuda


def test_cmd_limpiar(monkeypatch):
    monkeypatch.setattr(main.os, "system", lambda cmd: None)
    assert main.cmd_limpiar() == ""


def test_dispatch_calcular_y_nota(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert main.process_message("calcular 6 * 7") == "42"
    assert main.process_message("nota probar dispatch") == "Nota 1 guardada."
    assert "probar dispatch" in main.process_message("ver notas")


# --- Sinónimos, resumen, Wikipedia ---

def test_aplicar_sinonimos():
    assert main.aplicar_sinonimos("eliminar nota 1") == "borrar nota 1"
    assert main.aplicar_sinonimos("abre youtube") == "abrir youtube"
    assert main.aplicar_sinonimos("apaga el equipo") == "apagar el equipo"
    # Solo la primera palabra cambia: los argumentos se conservan intactos.
    assert main.aplicar_sinonimos("nota eliminar duplicados") == "nota eliminar duplicados"
    assert main.aplicar_sinonimos("hola") == "hola"


def test_sinonimo_en_dispatch(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main.cmd_nota("nota para eliminar")
    # "eliminar" no existe como comando, pero el sinónimo lo resuelve.
    assert "Nota borrada" in main.process_message("eliminar nota 1")
    assert main.cmd_ver_notas() == "No tienes notas guardadas."


def test_respuesta_desconocida_sugiere_ayuda():
    assert "ayuda" in main.RESPUESTA_DESCONOCIDA
    assert main.process_message("dime un poema") == main.RESPUESTA_DESCONOCIDA


def test_cmd_resumen(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main.psutil, "sensors_battery",
                        lambda: SimpleNamespace(percent=80, power_plugged=False))
    main.cmd_tarea("estudiar redes")
    main.cmd_nota("recordatorio")
    resumen = main.cmd_resumen()
    assert "Buenos días" in resumen
    assert "1 tarea(s) pendiente(s)" in resumen
    assert "1 nota(s)" in resumen
    assert "80%" in resumen
    assert "estudiar redes" in resumen


def test_cmd_wikipedia_ok(monkeypatch):
    import json
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"extract": "Python es un lenguaje de programación."}).encode()
    monkeypatch.setattr(main.urllib.request, "urlopen", lambda req, timeout=10: FakeResp())
    assert main.cmd_wikipedia("python") == "Python es un lenguaje de programación."
    assert main.cmd_wikipedia("") == "¿Qué quieres buscar? Ejemplo: wikipedia agujeros negros"


def test_cmd_wikipedia_falla_con_gracia(monkeypatch):
    def _boom(req, timeout=10):
        raise Exception("sin internet")
    monkeypatch.setattr(main.urllib.request, "urlopen", _boom)
    assert "No encontré nada" in main.cmd_wikipedia("xyz123")


def test_sites_nuevos(monkeypatch):
    opened = []
    monkeypatch.setattr(main.webbrowser, "open", lambda url: opened.append(url))
    assert main.process_message("abrir gmail") == "Abriendo gmail..."
    assert opened == ["https://mail.google.com"]


def test_ayuda_menciona_nuevo():
    ayuda = main.cmd_ayuda()
    assert "resumen" in ayuda and "wikipedia" in ayuda
