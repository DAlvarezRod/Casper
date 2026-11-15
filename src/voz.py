# Capa de voz de Casper (Fase 5): hablar (TTS) y escuchar (STT).
# Las tres librerías son opcionales: si alguna falta, la función
# correspondiente avisa honestamente en vez de romper el programa.
# - pyttsx3: texto a voz offline, con las voces del sistema (SAPI en Windows).
# - sounddevice: graba del micrófono (su rueda de Windows trae PortAudio).
# - SpeechRecognition: convierte audio en texto (Google, gratis, sin clave).
import os
import tempfile
import wave

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import sounddevice as sd
except Exception:
    sd = None

SEGUNDOS_ESCUCHA = 5
MUESTRAS_POR_SEGUNDO = 44100


def hablar(texto):
    # El motor se crea en cada llamada: es un poco más lento, pero evita
    # problemas de hilos (el motor no es seguro entre hilos) y no deja
    # un motor global a medio inicializar si algo falla.
    if pyttsx3 is None:
        return False
    try:
        motor = pyttsx3.init()
        motor.setProperty("rate", 175)
        # Si hay una voz en español instalada, usarla.
        for voz in motor.getProperty("voices"):
            nombre = voz.name.lower()
            ident = voz.id.lower()
            if "spanish" in nombre or "español" in nombre or "es-" in ident:
                motor.setProperty("voice", voz.id)
                break
        motor.say(texto)
        motor.runAndWait()
        motor.stop()
        return True
    except Exception:
        return False


def escuchar(segundos=SEGUNDOS_ESCUCHA):
    # Devuelve (texto, error): solo uno de los dos tiene valor.
    # Separar el éxito del error en dos valores es más claro que
    # devolver un mensaje que podría confundirse con una transcripción.
    if sd is None:
        return None, "La grabación de voz no está disponible en este equipo (falta sounddevice)."
    if sr is None:
        return None, "El reconocimiento de voz no está disponible (falta SpeechRecognition)."
    try:
        audio = sd.rec(int(segundos * MUESTRAS_POR_SEGUNDO),
                       samplerate=MUESTRAS_POR_SEGUNDO, channels=1, dtype="int16")
        sd.wait()
    except Exception:
        return None, "No pude acceder al micrófono."
    # SpeechRecognition lee archivos WAV, no arreglos de audio:
    # guardamos uno temporal y lo borramos al final (finally).
    ruta = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            ruta = f.name
        with wave.open(ruta, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(MUESTRAS_POR_SEGUNDO)
            wf.writeframes(audio.tobytes())
        rec = sr.Recognizer()
        with sr.AudioFile(ruta) as fuente:
            datos = rec.record(fuente)
        texto = rec.recognize_google(datos, language="es-ES")
        return texto, None
    except sr.UnknownValueError:
        return None, "No te entendí, ¿puedes repetir?"
    except sr.RequestError:
        return None, "El servicio de voz no responde (¿hay internet?)."
    except Exception:
        return None, "Algo falló al procesar tu voz."
    finally:
        if ruta and os.path.exists(ruta):
            os.unlink(ruta)
