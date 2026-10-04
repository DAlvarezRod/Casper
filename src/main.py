import ast
import ctypes
import json
import operator
import os
import random
import re
import string
import subprocess
import threading
import time
import unicodedata
import urllib.request
import webbrowser
from datetime import datetime
from difflib import get_close_matches
from urllib.parse import quote, quote_plus

import psutil
from PIL import ImageGrab

try:
    # pyautogui necesita un entorno gráfico para importarse.
    # En un servidor sin pantalla falla, así que lo hacemos opcional.
    import pyautogui
except Exception:
    pyautogui = None

try:
    # winsound solo existe en Windows; se usa para el temporizador.
    import winsound
except ImportError:
    winsound = None

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
    # Letras repetidas por énfasis ("holaaaa" -> "hola"). Solo letras:
    # "1000" no debe convertirse en "10".
    text = re.sub(r"([a-z])\1{2,}", r"\1", text)
    # Palabras pegadas a números ("temporizador1" -> "temporizador 1").
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    # Estos caracteres se CONSERVAN porque tienen significado para comandos
    # como "calcular": en "calcular 3.5 * 2" el punto y el asterisco no son
    # decoración, son parte del mensaje. Todo lo demás se elimina.
    significativos = "+-*/%().,"
    borrar = "".join(c for c in string.punctuation + "¿¡" if c not in significativos)
    table = str.maketrans("", "", borrar)
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


# Palabras de relleno que no aportan significado al comando.
# Ojo: "si" y "no" NO están aquí porque son comandos que cambian estado.
STOPWORDS = {
    "por", "favor", "porfavor", "porfa", "me", "puedes", "podrias", "quiero", "quisiera", "deseo",
    "el", "la", "los", "las", "de", "del", "al", "un", "una", "unos", "unas",
    "que", "en", "mi", "mis", "tu", "tus", "su", "sus", "se", "es", "son",
    "esta", "este", "esto", "estos", "con", "para", "como", "muy",
    "tan", "pero", "y", "o", "a", "ante", "the", "of", "to",
}

# Números en palabras -> dígitos. Sin esto "borrar nota dos" sería inútil.
NUMEROS = {
    "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
    "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
    "nueve": "9", "diez": "10",
    "primera": "1", "primero": "1", "segunda": "2", "segundo": "2",
    "tercera": "3", "tercero": "3",
}

# Sinónimos y conjugaciones. Un sistema real usaría lematización (NLP);
# esto es la versión honesta con diccionario.
SINONIMOS = {
    "eliminar": "borrar", "elimina": "borrar", "quita": "borrar", "borra": "borrar",
    "apaga": "apagar", "reinicia": "reiniciar",
    "abre": "abrir",
    "muestra": "ver", "muestrame": "ver", "ensename": "ver",
    "anota": "nota", "anotar": "nota", "apunta": "nota",
    "chistes": "chiste", "notas": "nota", "tareas": "tarea", "capturas": "captura",
    "recuerda": "recuerdame",
}


def tokenizar(message):
    # Convierte el mensaje en palabras significativas: sin muletillas,
    # con números en dígitos y sinónimos unificados. Esto SOLO se usa
    # para buscar el comando; los argumentos salen del mensaje original.
    tokens = []
    for palabra in message.split():
        palabra = palabra.strip(",;:!?")
        if not palabra or palabra in STOPWORDS:
            continue
        palabra = NUMEROS.get(palabra, palabra)
        if palabra in SINONIMOS:
            palabra = SINONIMOS[palabra]
        elif palabra not in _vocabulario():
            # Typo por palabra: "elmina" -> "elimina". Solo si es muy
            # parecido (>=0.8); si no, se deja como está.
            corregida = fuzzy_match(palabra, _vocabulario())
            if corregida is not None:
                palabra = SINONIMOS.get(corregida, corregida)
        tokens.append(palabra)
    return tokens


# Vocabulario para corregir typos por palabra: todo lo que Casper conoce
# (comandos, inicios de comandos con argumento y sinónimos). Se construye
# una sola vez porque no cambia durante la ejecución.
_VOCABULARIO = None


def _vocabulario():
    global _VOCABULARIO
    if _VOCABULARIO is None:
        palabras = set(SINONIMOS.keys()) | set(SINONIMOS.values())
        for cmd in list(COMMANDS) + list(ARG_COMMANDS):
            palabras.update(cmd.split())
        _VOCABULARIO = palabras - STOPWORDS
    return _VOCABULARIO


def puntaje_tokens(tokens_msg, tokens_cmd):
    # Devuelve (palabras coincidentes, fracción del comando cubierta).
    # La tupla permite desempatar: más coincidencias gana.
    if not tokens_cmd:
        return (0, 0.0)
    comunes = set(tokens_msg) & set(tokens_cmd)
    return (len(comunes), len(comunes) / len(tokens_cmd))


# Comandos que cambian estado: en la etapa de tokens se excluyen para que
# una frase larga nunca dispare una confirmación por accidente.
COMANDOS_SENSIBLES = {"si", "no"}


# Respuesta cuando nada coincide. En vez de solo decir "no sé", enseña
# el camino: un buen asistente nunca deja al usuario sin siguiente paso.
RESPUESTA_DESCONOCIDA = "Todavía no sé cómo responder a eso. Escribe 'ayuda' para ver lo que puedo hacer."


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
    # Guardamos la ruta ABSOLUTA en _ultima_captura para poder responder
    # "¿dónde guardaste la captura?" más tarde.
    try:
        imagen = ImageGrab.grab()
    except Exception:
        return "No pude tomar la captura en este equipo."
    nombre = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    ruta = os.path.abspath(nombre)
    imagen.save(ruta)
    _ultima_captura["ruta"] = ruta
    return f"Captura guardada en {ruta}"


# Última captura tomada. Como la confirmación pendiente, es memoria de
# corto plazo: Casper recuerda lo último que hizo para poder hablar de ello.
_ultima_captura = {"ruta": None}


def cmd_donde_captura():
    ruta = _ultima_captura["ruta"]
    if ruta is None:
        return "Aún no he tomado ninguna captura en esta sesión."
    return f"La última captura está en {ruta}"


# Aplicaciones conocidas: nombre que dice el usuario -> ejecutable en Windows.
APPS = {
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calculadora": "calc.exe",
    "paint": "mspaint.exe",
    "explorador": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
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


# --- Diversión y utilidades ---

CHISTES = [
    "¿Por qué los pájaros no usan Facebook? Porque ya tienen Twitter.",
    "¿Qué hace una abeja en el gimnasio? ¡Zum-ba!",
    "¿Por qué el libro de matemáticas estaba triste? Porque tenía demasiados problemas.",
    "¿Cómo se llama el campeón de buceo japonés? Tokofondo.",
    "¿Qué le dice un bit al otro? Nos vemos en el bus.",
    "¿Por qué los programadores confunden Halloween con Navidad? Porque OCT 31 == DEC 25.",
    "¿Cómo se despiden los químicos? Ácido un placer.",
    "¿Qué hace un pez? ¡Nada!",
]


def cmd_chiste():
    return random.choice(CHISTES)


# Operadores permitidos en la calculadora. Todo lo demás (llamadas a
# funciones, atributos, imports) está prohibido por _evaluar.
_OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluar(nodo):
    # Recorre el árbol sintáctico de la expresión y solo permite números
    # y operadores básicos. Cualquier otra cosa lanza ValueError.
    if isinstance(nodo, ast.Expression):
        return _evaluar(nodo.body)
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        return nodo.value
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.left), _evaluar(nodo.right))
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.operand))
    raise ValueError("Expresión no permitida")


def cmd_calcular(expresion):
    # NUNCA usar eval() con texto del usuario: ejecutaría cualquier código,
    # como borrar archivos. En su lugar parseamos con ast y solo aceptamos
    # números y operadores de la lista blanca _OPERADORES.
    if not expresion:
        return "¿Qué quieres calcular? Ejemplo: calcular 15 * 3 + 2"
    expresion = expresion.replace(",", ".")  # coma decimal española -> punto
    try:
        arbol = ast.parse(expresion, mode="eval")
        return str(_evaluar(arbol))
    except ZeroDivisionError:
        return "No puedo dividir por cero."
    except Exception:
        return "Solo puedo calcular números y operaciones básicas (+, -, *, /, **, %)."


def cmd_dado():
    return f"El dado dice: {random.randint(1, 6)}"


def cmd_moneda():
    return f"Salió: {random.choice(['cara', 'sello'])}"


def cmd_azar(rango):
    partes = [NUMEROS.get(p, p) for p in rango.split()]
    try:
        minimo, maximo = int(partes[0]), int(partes[1])
    except (IndexError, ValueError):
        return "Uso: azar <mínimo> <máximo>. Ejemplo: azar 1 100"
    if minimo > maximo:
        return "El mínimo no puede ser mayor que el máximo."
    return f"Número al azar: {random.randint(minimo, maximo)}"


def cmd_bateria():
    bat = psutil.sensors_battery()
    if bat is None:
        return "No detecté batería (¿equipo de escritorio?)."
    estado = "cargando" if bat.power_plugged else "descargando"
    return f"Batería: {bat.percent}% ({estado})"


def cmd_limpiar():
    os.system("cls" if os.name == "nt" else "clear")
    return ""  # main() no imprime respuestas vacías


def cmd_temporizador(minutos):
    minutos = NUMEROS.get(minutos.strip(), minutos.strip())
    try:
        mins = float(minutos.replace(",", "."))
        if mins <= 0:
            raise ValueError
    except ValueError:
        return "Uso: temporizador <minutos>. Ejemplo: temporizador 5"

    def _avisar():
        if winsound is not None:
            winsound.Beep(880, 500)
        # Ojo: esto se imprime desde otro hilo, puede mezclarse con el
        # prompt. Es la forma simple; la robusta sería una cola de mensajes.
        print("\nCasper: ¡Tiempo cumplido!")

    threading.Timer(mins * 60, _avisar).start()
    return f"Temporizador de {minutos} minutos iniciado."


def cmd_ayuda():
    return (
        "Puedo ayudarte con:\n"
        "CONVERSACIÓN: hola, quien eres, chiste\n"
        "TIEMPO: hora, fecha, temporizador <minutos>\n"
        "RESUMEN: resumen, buenos dias\n"
        "WEB: abrir <sitio>, wikipedia <tema>\n"
        "SISTEMA: estado del sistema, bateria, captura de pantalla, "
        "abrir app <nombre>, volumen <subir|bajar|silenciar>, bloquear, apagar, reiniciar, limpiar\n"
        "NOTAS: nota <texto>, ver notas, borrar nota <n>\n"
        "TAREAS: tarea <texto>, ver tareas, completar tarea <n>\n"
        "RECORDATORIOS: recuerdame <texto> en <N> minutos|horas, ver recordatorios, cancelar recordatorio <n>\n"
        "MATEMÁTICAS Y AZAR: calcular <expresión>, dado, moneda, azar <min> <max>\n"
        "OTROS: donde esta la captura, ayuda, salir"
    )


def cmd_resumen():
    # El informe matutino de Jarvis: agrega fecha, tareas, notas y batería
    # en un solo mensaje proactivo. La proactividad es no esperar a que
    # te pregunten cada cosa por separado.
    hoy = datetime.now()
    dia = DIAS_ES[hoy.weekday()]
    tareas = _cargar_json(TAREAS_PATH, [])
    pendientes = [t for t in tareas if not t["hecha"]]
    notas = _cargar_json(NOTAS_PATH, [])
    lineas = [
        f"Buenos días. Hoy es {dia} {hoy.strftime('%d/%m/%Y')}, son las {hoy.strftime('%H:%M')}.",
        f"Tienes {len(pendientes)} tarea(s) pendiente(s).",
        f"Tienes {len(notas)} nota(s) guardada(s).",
    ]
    bat = psutil.sensors_battery()
    if bat is not None:
        estado = "cargando" if bat.power_plugged else "descargando"
        lineas.append(f"Batería al {bat.percent}% ({estado}).")
    if pendientes:
        lineas.append("Empieza por: " + pendientes[0]["texto"])
    return "\n".join(lineas)


def cmd_wikipedia(tema):
    # Investigación sin dependencias externas: la API REST de Wikipedia
    # devuelve JSON con urllib de la librería estándar.
    if not tema:
        return "¿Qué quieres buscar? Ejemplo: wikipedia agujeros negros"
    url = "https://es.wikipedia.org/api/rest_v1/page/summary/" + quote(tema)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Casper/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            datos = json.load(r)
    except Exception:
        return f"No encontré nada sobre '{tema}' en Wikipedia."
    if datos.get("type") == "disambiguation":
        return f"'{tema}' tiene varios significados. Sé más específico."
    resumen = datos.get("extract", "")
    if not resumen:
        return f"No encontré nada sobre '{tema}' en Wikipedia."
    return resumen[:500] + ("..." if len(resumen) > 500 else "")


# --- Notas y tareas (persistencia en archivos JSON) ---

NOTAS_PATH = "notas.json"
TAREAS_PATH = "tareas.json"


def _cargar_json(ruta, defecto):
    # Lee un archivo JSON. Si no existe o está corrupto, devuelve el valor
    # por defecto en vez de romper el programa.
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def _guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cmd_nota(texto):
    if not texto:
        return "¿Qué quieres anotar? Ejemplo: nota comprar leche"
    notas = _cargar_json(NOTAS_PATH, [])
    notas.append({"texto": texto, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")})
    _guardar_json(NOTAS_PATH, notas)
    return f"Nota {len(notas)} guardada."


def cmd_ver_notas():
    notas = _cargar_json(NOTAS_PATH, [])
    if not notas:
        return "No tienes notas guardadas."
    lineas = [f"{i + 1}. {n['texto']} ({n['fecha']})" for i, n in enumerate(notas)]
    return "\n".join(lineas)


def cmd_borrar_nota(numero):
    notas = _cargar_json(NOTAS_PATH, [])
    # Acepta "dos" además de "2": los números en palabras llegan aquí
    # cuando el comando se resolvió por tokens.
    numero = NUMEROS.get(numero.strip(), numero.strip())
    try:
        borrada = notas.pop(int(numero) - 1)
    except (ValueError, IndexError):
        return "Uso: borrar nota <número>. Mira tus notas con 'ver notas'."
    _guardar_json(NOTAS_PATH, notas)
    return f"Nota borrada: {borrada['texto']}"


def cmd_tarea(texto):
    if not texto:
        return "¿Qué tarea quieres agregar? Ejemplo: tarea estudiar para el parcial"
    tareas = _cargar_json(TAREAS_PATH, [])
    tareas.append({"texto": texto, "hecha": False})
    _guardar_json(TAREAS_PATH, tareas)
    return f"Tarea {len(tareas)} agregada."


def cmd_ver_tareas():
    tareas = _cargar_json(TAREAS_PATH, [])
    if not tareas:
        return "No tienes tareas pendientes. ¡Bien!"
    lineas = []
    for i, t in enumerate(tareas):
        marca = "x" if t["hecha"] else " "
        lineas.append(f"{i + 1}. [{marca}] {t['texto']}")
    return "\n".join(lineas)


def cmd_completar_tarea(numero):
    tareas = _cargar_json(TAREAS_PATH, [])
    numero = NUMEROS.get(numero.strip(), numero.strip())
    try:
        tarea = tareas[int(numero) - 1]
    except (ValueError, IndexError):
        return "Uso: completar tarea <número>. Mira tus tareas con 'ver tareas'."
    tarea["hecha"] = True
    _guardar_json(TAREAS_PATH, tareas)
    return f"Tarea completada: {tarea['texto']}"


# --- Recordatorios (completan la Fase 3: memoria que sobrevive reinicios) ---

RECORDATORIOS_PATH = "recordatorios.json"


def _programar_recordatorio(rec):
    # Programa el aviso para cuando llegue la hora. Devuelve False si ya venció.
    demora = rec["timestamp"] - time.time()
    if demora <= 0:
        return False
    threading.Timer(demora, lambda: _disparar_recordatorio(rec["id"])).start()
    return True


def _disparar_recordatorio(rid):
    recs = _cargar_json(RECORDATORIOS_PATH, [])
    rec = next((r for r in recs if r["id"] == rid), None)
    if rec is None:
        return  # fue cancelado antes de sonar
    if winsound is not None:
        winsound.Beep(880, 500)
    print(f"\nCasper: ¡Recordatorio! {rec['texto']}")
    _guardar_json(RECORDATORIOS_PATH, [r for r in recs if r["id"] != rid])


def _reprogramar_recordatorios():
    # Al iniciar, reprograma los recordatorios pendientes. Los que vencieron
    # mientras Casper estaba apagado se anuncian como perdidos: un asistente
    # no finge que nada pasó, te pone al día.
    recs = _cargar_json(RECORDATORIOS_PATH, [])
    ahora = time.time()
    pendientes = []
    for rec in recs:
        if not _programar_recordatorio(rec):
            print(f"Casper: Mientras estabas fuera debí recordarte: {rec['texto']}")
        else:
            pendientes.append(rec)
    _guardar_json(RECORDATORIOS_PATH, pendientes)


def cmd_recordar(args):
    # "llamar al banco en 30 minutos" -> texto="llamar al banco", 1800 segundos.
    match = re.search(r"\ben\s+(\d+)\s*(minutos?|horas?)\b", args)
    if not match:
        return "Uso: recuerdame <texto> en <N> minutos|horas. Ejemplo: recuerdame llamar al banco en 30 minutos"
    texto = args[:match.start()].strip()
    if not texto:
        return "¿Qué quieres que te recuerde?"
    cantidad = int(match.group(1))
    segundos = cantidad * 3600 if match.group(2).startswith("hora") else cantidad * 60
    recs = _cargar_json(RECORDATORIOS_PATH, [])
    nuevo_id = max([r["id"] for r in recs], default=0) + 1
    rec = {"id": nuevo_id, "texto": texto, "timestamp": time.time() + segundos}
    recs.append(rec)
    _guardar_json(RECORDATORIOS_PATH, recs)
    _programar_recordatorio(rec)
    unidad = "hora(s)" if match.group(2).startswith("hora") else "minuto(s)"
    return f"Te lo recordaré en {cantidad} {unidad}: {texto}"


def cmd_ver_recordatorios():
    recs = _cargar_json(RECORDATORIOS_PATH, [])
    if not recs:
        return "No tienes recordatorios pendientes."
    lineas = []
    for i, r in enumerate(recs):
        minutos = max(0, int((r["timestamp"] - time.time()) // 60))
        lineas.append(f"{i + 1}. {r['texto']} (en ~{minutos} min)")
    return "\n".join(lineas)


def cmd_cancelar_recordatorio(numero):
    recs = _cargar_json(RECORDATORIOS_PATH, [])
    try:
        idx = int(NUMEROS.get(numero.strip(), numero.strip())) - 1
        borrado = recs.pop(idx)
    except (ValueError, IndexError):
        return "Uso: cancelar recordatorio <número>. Míralos con 'ver recordatorios'."
    _guardar_json(RECORDATORIOS_PATH, recs)
    return f"Recordatorio cancelado: {borrado['texto']}"


# Tabla de sitios conocidos: nombre corto -> URL.
SITES = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "netflix": "https://www.netflix.com",
    "gmail": "https://mail.google.com",
    "correo": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "drive": "https://drive.google.com",
    "classroom": "https://classroom.google.com",
}


def cmd_abrir(sitio):
    # A diferencia de los otros comandos, este RECIBE un argumento:
    # el sitio que el usuario quiere abrir.
    # Limpiamos muletillas del argumento: "abrir el whatsapp por favor"
    # -> "whatsapp". (En "nota" no haríamos esto: ahí el texto es del usuario.)
    sitio = " ".join(p for p in sitio.split() if p not in STOPWORDS)
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
    "donde esta la captura": cmd_donde_captura,
    "donde guardaste la captura": cmd_donde_captura,
    "bloquear": cmd_bloquear,
    "bloquear equipo": cmd_bloquear,
    "apagar": cmd_apagar,
    "apagar equipo": cmd_apagar,
    "reiniciar": cmd_reiniciar,
    "reiniciar equipo": cmd_reiniciar,
    "si": cmd_si,
    "no": cmd_no,
    "chiste": cmd_chiste,
    "dime un chiste": cmd_chiste,
    "cuentame un chiste": cmd_chiste,
    "dado": cmd_dado,
    "tira el dado": cmd_dado,
    "moneda": cmd_moneda,
    "cara o sello": cmd_moneda,
    "bateria": cmd_bateria,
    "limpiar": cmd_limpiar,
    "limpia la pantalla": cmd_limpiar,
    "ayuda": cmd_ayuda,
    "resumen": cmd_resumen,
    "buenos dias": cmd_resumen,
    "resumen del dia": cmd_resumen,
    "ver recordatorios": cmd_ver_recordatorios,
    "ver notas": cmd_ver_notas,
    "ver tareas": cmd_ver_tareas,
    "salir": cmd_salir,
}

# Comandos con argumento: la clave es el inicio del mensaje ("abrir app")
# y el resto se pasa como argumento a la funcion.
# "abrir app notepad" -> cmd_abrir_app("notepad")
ARG_COMMANDS = {
    "abrir": cmd_abrir,
    "abrir app": cmd_abrir_app,
    "volumen": cmd_volumen,
    "calcular": cmd_calcular,
    "azar": cmd_azar,
    "nota": cmd_nota,
    "borrar nota": cmd_borrar_nota,
    "tarea": cmd_tarea,
    "completar tarea": cmd_completar_tarea,
    "temporizador": cmd_temporizador,
    "wikipedia": cmd_wikipedia,
    "recuerdame": cmd_recordar,
    "recordar": cmd_recordar,
    "cancelar recordatorio": cmd_cancelar_recordatorio,
}


def _extraer_comando_arg(message):
    # Busca un comando con argumento del MÁS LARGO al más corto, para que
    # "abrir app" gane a "abrir" cuando el mensaje es "abrir app notepad".
    for command in sorted(ARG_COMMANDS, key=len, reverse=True):
        if message == command or message.startswith(command + " "):
            return ARG_COMMANDS[command], message[len(command):].strip()
    return None, None


# Frases completas que se reescriben antes de buscar. Para casos donde
# quitar muletillas destruiría el significado: "mis notas" -> [nota]
# coincidiría con "agregar nota" en vez de con "ver notas".
FRASES = {
    "mis notas": "ver notas",
    "mis tareas": "ver tareas",
}


def process_message(message):
    # 0. Reescritura de frases completas (ver FRASES).
    message = FRASES.get(message, message)
    # 1. Coincidencia exacta: la forma mas rapida y segura.
    handler = COMMANDS.get(message)
    if handler is not None:
        return handler()
    # 2. Comandos con argumento: separamos la intencion ("abrir app")
    # del argumento ("notepad") y se lo pasamos a la funcion.
    func, arg = _extraer_comando_arg(message)
    if func is None:
        # 2b. Typo en el verbo: corregimos la primera palabra con
        # fuzzy matching y reintentamos el paso 2 una sola vez.
        primera, _, resto = message.partition(" ")
        inicios = {c.split(" ")[0] for c in ARG_COMMANDS}
        parecido = fuzzy_match(primera, inicios)
        if parecido is not None and parecido != primera:
            corregido = parecido + (" " + resto if resto else "")
            func, arg = _extraer_comando_arg(corregido)
    if func is not None:
        return func(arg)
    # 3. Prefijo con límite de palabra: "que dia es hoy" empieza con
    # "que dia es ". El espacio importa: antes "simple" disparaba "si".
    for command, func in COMMANDS.items():
        if message == command or message.startswith(command + " "):
            return func()
    # 4. Tokens: el orden y las muletillas dejan de importar.
    # "por favor elimina la primera nota" -> {borrar, 1, nota} -> borrar nota.
    # Los comandos sensibles ("si"/"no") se excluyen: una frase larga jamás
    # debe confirmar una acción destructiva por accidente.
    tokens_msg = tokenizar(message)
    mejor, mejor_llamada = (0, 0.0), None
    for command, func in COMMANDS.items():
        if command in COMANDOS_SENSIBLES:
            continue
        puntos = puntaje_tokens(tokens_msg, tokenizar(command))
        # Umbral 0.6: con 0.5, "dime un poema" coincidía con "dime un chiste"
        # (1 de 2 palabras). Ser permisivo está bien; inventar respuestas, no.
        if puntos > mejor and puntos[1] >= 0.6:
            mejor = puntos
            # f=func congela la función ahora: sin esto, lambda usaría
            # el último valor de func al llamarse (late binding).
            mejor_llamada = lambda f=func: f()
    for command in sorted(ARG_COMMANDS, key=len, reverse=True):
        puntos = puntaje_tokens(tokens_msg, tokenizar(command))
        if puntos > mejor and puntos[1] >= 0.6:
            usados = set(tokenizar(command))
            resto = [t for t in tokens_msg if t not in usados]
            mejor = puntos
            # lambda con valores por defecto: congela f y a en este momento.
            mejor_llamada = lambda f=ARG_COMMANDS[command], a=" ".join(resto): f(a)
    if mejor_llamada is not None:
        return mejor_llamada()
    # 5. Coincidencia difusa: si nada anterior funciono, buscamos el comando
    # mas parecido. "holaa" -> "hola", pero "xyz" no coincide con nada.
    parecido = fuzzy_match(message, COMMANDS.keys())
    if parecido is not None:
        return COMMANDS[parecido]()
    return RESPUESTA_DESCONOCIDA


def main():
    print("Casper iniciado.")
    # Al arrancar: reprograma recordatorios pendientes y avisa de los vencidos.
    _reprogramar_recordatorios()
    print("Escribe 'salir' para terminar.")

    while True:
        user_input = input("Tu: ")
        message = normalize_text(user_input)
        response = process_message(message)

        if response == "salir":
            print("Casper: Hasta luego.")
            break

        # Las respuestas vacías (como la de "limpiar") no se imprimen.
        if response:
            print("Casper:", response)


if __name__ == "__main__":
    # __name__ vale "__main__" cuando ejecutamos este archivo directamente.
    main()
