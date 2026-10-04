import string
import unicodedata
import webbrowser
from datetime import datetime
from difflib import get_close_matches
from urllib.parse import quote_plus

# "def" define una funcion: nos ayuda a tener multiples funciones
# que podemos usar despues en varias partes del codigo.
# Separacion de Responsabilidades: no se trata de que una funcion
# solo haga una linea, sino de que una funcion no haga TODO.


def strip_accents(text):
    # NFD descompone un caracter acentuado como "e" en dos partes:
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
    "salir": cmd_salir,
}

# Comandos con argumento: la clave es la primera palabra ("abrir") y el
# resto del mensaje se pasa como argumento a la funcion.
# "abrir youtube" -> cmd_abrir("youtube")
ARG_COMMANDS = {
    "abrir": cmd_abrir,
}


def process_message(message):
    # 1. Coincidencia exacta: la forma mas rapida y segura.
    handler = COMMANDS.get(message)
    if handler is not None:
        return handler()
    # 2. Comandos con argumento: separamos la intencion ("abrir")
    # del argumento ("youtube") y se lo pasamos a la funcion.
    # La primera palabra tambien acepta typos: "avrir youtube" funciona.
    primera, _, resto = message.partition(" ")
    comando_arg = primera if primera in ARG_COMMANDS else fuzzy_match(primera, ARG_COMMANDS.keys())
    if comando_arg is not None:
        return ARG_COMMANDS[comando_arg](resto.strip())
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
