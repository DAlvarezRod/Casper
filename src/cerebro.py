# Cerebro de Casper (Fase 6): un modelo de lenguaje como última etapa
# del dispatcher. Cuando ningún comando coincide, el modelo decide:
# responde con texto (conversación, conocimiento) o llama a una de las
# herramientas de Casper (los comandos, expuestos como funciones).
#
# Proveedores (se elige con CASPER_LLM, por defecto "ollama"):
# - ollama: modelo local y gratis, sin clave. Requiere Ollama instalado
#   y un modelo descargado (ver README). Nada sale de tu computador.
# - gemini: API de Google, gratis con GEMINI_API_KEY (ver .env.example).
#
# Si el cerebro no está disponible (sin Ollama, sin clave, sin internet),
# responder() devuelve None y Casper contesta con lo que ya sabía.
# Un cerebro caído jamás debe romper al asistente.
import os

from web import WebError, post_json


def _herramienta(nombre, descripcion, propiedades=None, requeridos=None):
    return {
        "nombre": nombre,
        "descripcion": descripcion,
        "parametros": {
            "type": "object",
            "properties": propiedades or {},
            "required": requeridos or [],
        },
    }


def _texto(descripcion):
    return {"type": "string", "description": descripcion}


def _entero(descripcion):
    return {"type": "integer", "description": descripcion}


def _numero(descripcion):
    return {"type": "number", "description": descripcion}


# Los comandos de Casper, descritos para el modelo. El modelo solo ve
# nombres y descripciones: nunca ve el código ni las claves.
# A propósito NO están: apagar, reiniciar, bloquear, decir, voz, escuchar
# ni salir. Las acciones destructivas y el control de voz los inicia
# solo el humano, nunca el modelo.
DEFINICIONES_HERRAMIENTAS = [
    _herramienta("hora", "Dice la hora actual."),
    _herramienta("fecha", "Dice la fecha actual (día de la semana en español)."),
    _herramienta("estado", "Muestra el estado del sistema: CPU, RAM y disco."),
    _herramienta("bateria", "Muestra el nivel y estado de la batería."),
    _herramienta("chiste", "Cuenta un chiste."),
    _herramienta("resumen", "Resumen del día: fecha, tareas pendientes, notas y batería."),
    _herramienta("ver_notas", "Muestra las notas guardadas."),
    _herramienta("ver_tareas", "Muestra las tareas pendientes y completadas."),
    _herramienta("ver_recordatorios", "Muestra los recordatorios pendientes."),
    _herramienta("abrir", "Abre un sitio web en el navegador.",
                 {"sitio": _texto("Nombre del sitio, por ejemplo 'youtube' o 'gmail'.")}, ["sitio"]),
    _herramienta("abrir_app", "Abre una aplicación de Windows.",
                 {"nombre": _texto("Nombre de la app: notepad, calculadora, paint, explorador, cmd, powershell.")}, ["nombre"]),
    _herramienta("volumen", "Sube, baja o silencia el volumen.",
                 {"nivel": _texto("Uno de: subir, bajar, silenciar.")}, ["nivel"]),
    _herramienta("calcular", "Calcula una expresión matemática básica.",
                 {"expresion": _texto("Expresión como '15 * 3 + 2'.")}, ["expresion"]),
    _herramienta("azar", "Genera un número al azar entre un mínimo y un máximo.",
                 {"minimo": _entero("Mínimo."), "maximo": _entero("Máximo.")}, ["minimo", "maximo"]),
    _herramienta("nota", "Guarda una nota.",
                 {"texto": _texto("Texto de la nota.")}, ["texto"]),
    _herramienta("borrar_nota", "Borra una nota por su número.",
                 {"numero": _entero("Número de la nota (ver ver_notas).")}, ["numero"]),
    _herramienta("tarea", "Agrega una tarea pendiente.",
                 {"texto": _texto("Texto de la tarea.")}, ["texto"]),
    _herramienta("completar_tarea", "Marca una tarea como completada por su número.",
                 {"numero": _entero("Número de la tarea (ver ver_tareas).")}, ["numero"]),
    _herramienta("temporizador", "Inicia un temporizador que avisa al cumplirse.",
                 {"minutos": _numero("Minutos (puede ser decimal, por ejemplo 0.5).")}, ["minutos"]),
    _herramienta("wikipedia", "Busca un tema en Wikipedia y devuelve un resumen.",
                 {"tema": _texto("Tema a buscar, por ejemplo 'agujeros negros'.")}, ["tema"]),
    _herramienta("recuerdame", "Programa un recordatorio.",
                 {"texto": _texto("Qué hay que recordar."),
                  "cantidad": _entero("En cuántos minutos u horas."),
                  "unidad": _texto("Una de: minutos, horas.")}, ["texto", "cantidad", "unidad"]),
    _herramienta("cancelar_recordatorio", "Cancela un recordatorio por su número.",
                 {"numero": _entero("Número del recordatorio (ver ver_recordatorios).")}, ["numero"]),
    _herramienta("clima", "Clima actual de una ciudad.",
                 {"ciudad": _texto("Nombre de la ciudad, por ejemplo 'Bogotá'.")}, ["ciudad"]),
    _herramienta("convertir", "Convierte una cantidad entre monedas.",
                 {"cantidad": _numero("Cantidad a convertir."),
                  "origen": _texto("Código de la moneda origen: usd, cop, eur..."),
                  "destino": _texto("Código de la moneda destino: usd, cop, eur...")}, ["cantidad", "origen", "destino"]),
]


def _prompt_sistema(usuario):
    nombre = usuario.get("nombre", "el usuario")
    return (
        f"Eres Casper, el asistente personal de {nombre}, "
        "estudiante de Ingeniería de Sistemas en la Universidad Javeriana (Bogotá). "
        "Hablas español, eres directo y breve.\n"
        "Tienes herramientas para hacer cosas: úsalas cuando el usuario pida una acción concreta. "
        "Si no hay herramienta adecuada, responde tú mismo con lo que sabes.\n"
        f"Si preguntan quién es el usuario: es {nombre}.\n"
        "No inventes datos en tiempo real (clima, dólar, noticias): usa las herramientas."
    )


def _a_ollama(d):
    # Ollama espera {"type": "function", "function": {...}}.
    return {"type": "function", "function": {
        "name": d["nombre"],
        "description": d["descripcion"],
        "parameters": d["parametros"],
    }}


def _a_mayusculas(obj):
    # Gemini escribe los tipos en MAYÚSCULAS (OBJECT, STRING, INTEGER).
    if isinstance(obj, dict):
        return {k: ("OBJECT" if v == "object" else
                    "STRING" if v == "string" else
                    "INTEGER" if v == "integer" else
                    "NUMBER" if v == "number" else
                    "BOOLEAN" if v == "boolean" else
                    "ARRAY" if v == "array" else _a_mayusculas(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_a_mayusculas(v) for v in obj]
    return obj


def _a_gemini(d):
    return {"name": d["nombre"],
            "description": d["descripcion"],
            "parameters": _a_mayusculas(d["parametros"])}


def _preguntar_ollama(mensaje, usuario):
    # Devuelve (texto, llamada) donde llamada es {"nombre", "argumentos"} o None.
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat"
    modelo = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    datos = post_json(url, {
        "model": modelo,
        "messages": [
            {"role": "system", "content": _prompt_sistema(usuario)},
            {"role": "user", "content": mensaje},
        ],
        "tools": [_a_ollama(d) for d in DEFINICIONES_HERRAMIENTAS],
        "stream": False,
    }, timeout=120)
    msg = datos.get("message") or {}
    llamadas = msg.get("tool_calls") or []
    if llamadas:
        fn = llamadas[0].get("function") or {}
        return None, {"nombre": fn.get("name"), "argumentos": fn.get("arguments") or {}}
    return msg.get("content") or None, None


def _preguntar_gemini(mensaje, usuario):
    clave = os.environ.get("GEMINI_API_KEY")
    if not clave:
        raise WebError("Falta GEMINI_API_KEY.")
    modelo = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}"
           f":generateContent?key={clave}")
    datos = post_json(url, {
        "system_instruction": {"parts": [{"text": _prompt_sistema(usuario)}]},
        "contents": [{"role": "user", "parts": [{"text": mensaje}]}],
        "tools": [{"functionDeclarations": [_a_gemini(d) for d in DEFINICIONES_HERRAMIENTAS]}],
    }, timeout=60)
    candidatos = datos.get("candidates") or []
    if not candidatos:
        return None, None
    partes = (candidatos[0].get("content") or {}).get("parts") or []
    for parte in partes:
        llamada = parte.get("functionCall")
        if llamada:
            return None, {"nombre": llamada.get("name"), "argumentos": llamada.get("args") or {}}
    textos = [p.get("text", "") for p in partes if p.get("text")]
    return "".join(textos) or None, None


def responder(mensaje, ejecutores, usuario):
    # Pregunta al modelo y, si pide una herramienta, la ejecuta.
    # Devuelve el texto final, o None si el cerebro no está disponible.
    proveedor = os.environ.get("CASPER_LLM", "ollama").lower()
    try:
        if proveedor == "gemini":
            texto, llamada = _preguntar_gemini(mensaje, usuario)
        else:
            texto, llamada = _preguntar_ollama(mensaje, usuario)
    except WebError:
        return None
    if llamada is not None:
        funcion = ejecutores.get(llamada["nombre"])
        if funcion is None:
            return None
        try:
            return funcion(**llamada["argumentos"])
        except TypeError:
            # El modelo inventó un argumento que la función no acepta.
            return None
    return texto or None
