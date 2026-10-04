import ctypes
import os
import string
import subprocess
import unicodedata
import webbrowser
from datetime import datetime
from difflib import get_close_matches
from urllib.parse import quote_plus

import psutil
from PIL import ImageGrab

try:
    # pyautogui necesita un entorno gráfico para importarse.
    # En un servidor sin pantalla falla, así que lo hacemos opcional.
    import pyautogui
except Exception:
    pyautogui = None

# "def" define una funcion: nos ayuda a tener multiples funciones
# que podemos usar despues en varias partes del codigo.
# Separacion de Responsabilidades: no se trata de que una funcion
# solo haga una linea, sino de que una funcion no haga TODO.


def strip_accents(text):
    # NFD descompone un caracter acentuado como "é" en dos partes:
    # la letra base "e" + la marca de acento combinada.
    # unicodedata.combining() detecta esas marcas, asi que nos
    # quedamos solo con las letras base.
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_text(text):
    # .lower() pasa el input a minusculas.
    # .strip() elimina los espacios al inicio y al final.
    text = text.lower().strip()
    # Quitamos los acentos ANTES de comparar con los comandos,
    # asi "Quien eres?" coincide con "quien eres".
    text = strip_accents(text)
    punctuation = string.punctuation + "¿¡"
    table = str.maketrans("", "", punctuation)
    text = text.translate(table)
    return text


def fuzzy_match(texto, opciones, umbral=0.8):
    # get_close_matches compara texto con cada opcion y devuelve las
    # mas parecidas, ordenadas de mejor a peor.
    # n=1: solo nos interesa la mejor candidata.
    # cutoff=umbral: que tan parecida debe ser (0.8 = 80% similar).
    # Asi "holaa" coincide con "hola", pero "xyz" no coincide con nada.
    parecidos = get_close_matches(texto, opciones, n=1, cutoff=umbral)
    return parecidos[0] if parecidos else None


# Cada comando es una funcion que devuelve la respuesta de Casper.
# Al ser funciones independientes, cada una se puede probar por separado.

def cmd_hola():
    return "Hola. ¿En que puedo ayudarte?"


def cmd_quien_eres():
    return "Soy Casper, tu asistente personal"


def cmd_hora():
    # datetime.now() devuelve la fecha y hora actual del sistema.
    # strftime la formatea: %H = hora (24h), %M = minutos.
    ahora = datetime.now()
    return "Son las " + ahora.strftime("%H:%M")


# Dias de la semana en español. weekday() devuelve un numero del 0 (lunes)
# al 6 (domingo), sin depender del idioma del sistema operativo.
# Asi la respuesta siempre sale en español, en cualquier computador.
DIAS_ES = ["lunes", "martes", "miercoles", "jueves",
           "viernes", "sabado", "domingo"]


def cmd_fecha():
    hoy = datetime.now()
    dia = DIAS_ES[hoy.weekday()]
    # f-string: la f antes de las comillas permite meter {variables}
    # directamente dentro del texto. Equivale a concatenar con +.
    return f"Hoy es {dia} {hoy.strftime('%d/%m/%Y')}"


def cmd_salir():
    return "salir"


# --- Fase 2: control del sistema ---

def cmd_estado():
    # psutil lee el estado real del equipo: CPU, memoria y disco.
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    unidad = "C:\\" if os.name == "nt" else "/"
    disco = psutil.disk_usage(unidad)
    return (f"CPU: {cpu}% | RAM: {ram.percent}% en uso "
            f"({ram.used // 1024**2} MB de {ram.total // 1024**2} MB) | "
            f"Disco: {disco.percent}% en uso")


def cmd_captura():
    # ImageGrab toma una foto de la pantalla y la guardamos con fecha y hora.
    try:
        imagen = ImageGrab.grab()
    except Exception:
        return "No pude tomar la captura en este equipo."
    nombre = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    imagen.save(nombre)
    return f"Captura guardada como {nombre}"


# Aplicaciones conocidas: nombre que dice el usuario -> ejecutable en Windows.
APPS = {
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calculadora": "calc.exe",
    "paint": "mspaint.exe",
}


def cmd_abrir_app(nombre):
    if not nombre:
        return "¿Qué aplicación quieres abrir?"
    exe = APPS.get(nombre)
    if exe is None:
        return f"No conozco la aplicación '{nombre}'."
    if os.name != "nt":
        return "Abrir aplicaciones solo funciona en Windows por ahora."
    subprocess.Popen(exe)
    return f"Abriendo {nombre}..."


def cmd_volumen(nivel):
    # pyautogui simula la pulsación de las teclas multimedia del teclado.
    teclas = {"subir": "volumeup", "bajar": "volumedown", "silenciar": "volumemute"}
    tecla = teclas.get(nivel)
    if tecla is None:
        return "Uso: volumen subir | volumen bajar | volumen silenciar"
    if pyautogui is None:
        return "El control de volumen no está disponible en este equipo."
    pyautogui.press(tecla)
    return f"Volumen: {nivel}"


def cmd_bloquear():
    # Bloquear es reversible (solo pide la contraseña), así que no
    # necesita confirmación, a diferencia de apagar o reiniciar.
    if os.name != "nt":
        return "Bloquear solo funciona en Windows por ahora."
    ctypes.windll.user32.LockWorkStation()
    return "Equipo bloqueado."


# Acción pendiente de confirmación. Guarda la función que se ejecutará
# cuando el usuario escriba "si". Es la memoria de corto plazo de Casper:
# recuerda que estábamos en medio de algo peligroso.
_confirmacion_pendiente = {"nombre": None, "funcion": None}


def pedir_confirmacion(nombre, funcion):
    _confirmacion_pendiente["nombre"] = nombre
    _confirmacion_pendiente["funcion"] = funcion
    return f"¿Seguro que quieres {nombre}? Escribe 'si' para confirmar o 'no' para cancelar."


def cmd_si():
    funcion = _confirmacion_pendiente["funcion"]
    _confirmacion_pendiente["nombre"] = None
    _confirmacion_pendiente["funcion"] = None
    if funcion is None:
        return "No hay nada que confirmar."
    return funcion()


def cmd_no():
    _confirmacion_pendiente["nombre"] = None
    _confirmacion_pendiente["funcion"] = None
    return "Cancelado."


def _apagar_ahora():
    if os.name != "nt":
        return "Apagar solo funciona en Windows por ahora."
    os.system("shutdown /s /t 5")
    return "Apagando el equipo en 5 segundos..."


def _reiniciar_ahora():
    if os.name != "nt":
        return "Reiniciar solo funciona en Windows por ahora."
    os.system("shutdown /r /t 5")
    return "Reiniciando el equipo en 5 segundos..."


def cmd_apagar():
    # Las acciones destructivas SIEMPRE piden confirmación primero.
    return pedir_confirmacion("apagar el equipo", _apagar_ahora)


def cmd_reiniciar():
    return pedir_confirmacion("reiniciar el equipo", _reiniciar_ahora)


# Tabla de sitios conocidos: nombre corto -> URL.
SITES = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "netflix": "https://www.netflix.com",
}


def cmd_abrir(sitio):
    # A diferencia de los otros comandos, este RECIBE un argumento:
    # el sitio que el usuario quiere abrir.
    if not sitio:
        return "¿Qué sitio quieres que abra?"
    # SITES.get busca el sitio conocido; si no existe, lo buscamos en Google.
    # quote_plus convierte "stack overflow" en "stack+overflow" para la URL.
    url = SITES.get(sitio)
    if url is None:
        url = "https://www.google.com/search?q=" + quote_plus(sitio)
    webbrowser.open(url)
    return "Abriendo " + sitio + "..."


# Registro de comandos: la clave es el texto normalizado que el usuario
# escribe, y el valor es la FUNCION que lo atiende (sin parentesis: no la
# estamos llamando, solo la estamos guardando).
# En Python las funciones son objetos como cualquier otro y se pueden
# guardar en un diccionario. A eso se le llama "funciones de primera clase".
# Varias claves pueden apuntar a la misma funcion (son alias del comando).
COMMANDS = {
    "hola": cmd_hola,
    "quien eres": cmd_quien_eres,
    "hora": cmd_hora,
    "que hora es": cmd_hora,
    "fecha": cmd_fecha,
    "que dia es": cmd_fecha,
    "estado": cmd_estado,
    "estado del sistema": cmd_estado,
    "captura": cmd_captura,
    "captura de pantalla": cmd_captura,
    "bloquear": cmd_bloquear,
    "bloquear equipo": cmd_bloquear,
    "apagar": cmd_apagar,
    "apagar equipo": cmd_apagar,
    "reiniciar": cmd_reiniciar,
    "reiniciar equipo": cmd_reiniciar,
    "si": cmd_si,
    "no": cmd_no,
    "salir": cmd_salir,
}

# Comandos con argumento: la clave es el inicio del mensaje ("abrir app")
# y el resto se pasa como argumento a la funcion.
# "abrir app notepad" -> cmd_abrir_app("notepad")
ARG_COMMANDS = {
    "abrir": cmd_abrir,
    "abrir app": cmd_abrir_app,
    "volumen": cmd_volumen,
}


def _extraer_comando_arg(message):
    # Busca un comando con argumento del MÁS LARGO al más corto, para que
    # "abrir app" gane a "abrir" cuando el mensaje es "abrir app notepad".
    for command in sorted(ARG_COMMANDS, key=len, reverse=True):
        if message == command or message.startswith(command + " "):
            return ARG_COMMANDS[command], message[len(command):].strip()
    return None, None


def process_message(message):
    # 1. Coincidencia exacta: la forma mas rapida y segura.
    handler = COMMANDS.get(message)
    if handler is not None:
        return handler()
    # 2. Comandos con argumento: separamos la intencion ("abrir app")
    # del argumento ("notepad") y se lo pasamos a la funcion.
    func, arg = _extraer_comando_arg(message)
    if func is None:
        # 2b. Typo en el comando: corregimos la primera palabra con
        # fuzzy matching y reintentamos el paso 2 una sola vez.
        primera, _, resto = message.partition(" ")
        inicios = {c.split(" ")[0] for c in ARG_COMMANDS}
        parecido = fuzzy_match(primera, inicios)
        if parecido is not None and parecido != primera:
            corregido = parecido + (" " + resto if resto else "")
            func, arg = _extraer_comando_arg(corregido)
    if func is not None:
        return func(arg)
    # 3. Coincidencia por prefijo: "que dia es hoy" empieza con "que dia es".
    # Asi el usuario no tiene que adivinar la frase exacta del comando.
    for command, func in COMMANDS.items():
        if message.startswith(command):
            return func()
    # 4. Coincidencia difusa: si nada anterior funciono, buscamos el comando
    # mas parecido. "holaa" -> "hola", pero "xyz" no coincide con nada.
    parecido = fuzzy_match(message, COMMANDS.keys())
    if parecido is not None:
        return COMMANDS[parecido]()
    return "Todavia no se como responder a eso"


def main():
    print("Casper iniciado.")
    print("Escribe 'salir' para terminar.")

    while True:
        user_input = input("Tu: ")
        message = normalize_text(user_input)
        response = process_message(message)

        if response == "salir":
            print("Casper: Hasta luego.")
            break

        print("Casper:", response)


if __name__ == "__main__":
    # __name__ vale "__main__" cuando ejecutamos este archivo directamente.
    main()
