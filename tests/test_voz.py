"""Pruebas para la capa de voz (src/voz.py).

Nada aquí toca un micrófono ni un parlante de verdad: las librerías
se reemplazan por falsas. Si una prueba necesitara hardware real,
no se podría correr en cualquier computador.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import voz


def test_hablar_sin_libreria(monkeypatch):
    monkeypatch.setattr(voz, "pyttsx3", None)
    assert voz.hablar("hola") is False


def test_hablar_con_motor_falso(monkeypatch):
    class FakeVoice:
        name = "Microsoft Helena - Spanish"
        id = "HKEY...TTS_MS_ES-ES_HELENA_11.0"

    class FakeEngine:
        def __init__(self):
            self.said = []
            self.props = {}

        def setProperty(self, k, v):
            self.props[k] = v

        def getProperty(self, k):
            return [FakeVoice()] if k == "voices" else None

        def say(self, t):
            self.said.append(t)

        def runAndWait(self):
            pass

        def stop(self):
            pass

    engines = []

    class FakePyttsx3:
        def init(self):
            e = FakeEngine()
            engines.append(e)
            return e

    monkeypatch.setattr(voz, "pyttsx3", FakePyttsx3())
    assert voz.hablar("hola mundo") is True
    assert engines[0].said == ["hola mundo"]
    # Eligió la voz en español por su nombre.
    assert engines[0].props.get("voice") == "HKEY...TTS_MS_ES-ES_HELENA_11.0"


def test_hablar_motor_roto(monkeypatch):
    class FakePyttsx3:
        def init(self):
            raise RuntimeError("sin voces")

    monkeypatch.setattr(voz, "pyttsx3", FakePyttsx3())
    assert voz.hablar("hola") is False


def test_escuchar_sin_sounddevice(monkeypatch):
    monkeypatch.setattr(voz, "sd", None)
    texto, error = voz.escuchar()
    assert texto is None and "sounddevice" in error


def test_escuchar_sin_sr(monkeypatch):
    monkeypatch.setattr(voz, "sd", object())
    monkeypatch.setattr(voz, "sr", None)
    texto, error = voz.escuchar()
    assert texto is None and "SpeechRecognition" in error


class FakeAudio:
    def tobytes(self):
        return b"\x00\x00" * 100


class FakeSD:
    def rec(self, n, samplerate, channels, dtype):
        return FakeAudio()

    def wait(self):
        pass


class FakeUnknown(Exception):
    pass


class FakeRequest(Exception):
    pass


class FakeRecognizer:
    def __init__(self, resultado=None, error=None):
        self.resultado = resultado
        self.error = error

    def record(self, src):
        return "datos"

    def recognize_google(self, datos, language="es-ES"):
        assert language == "es-ES"
        if self.error is not None:
            raise self.error
        return self.resultado


class FakeAudioFile:
    def __init__(self, ruta):
        pass

    def __enter__(self):
        return "fuente"

    def __exit__(self, *a):
        return False


class FakeSR:
    UnknownValueError = FakeUnknown
    RequestError = FakeRequest

    def __init__(self, resultado=None, error=None):
        self._resultado = resultado
        self._error = error

    def Recognizer(self):
        return FakeRecognizer(self._resultado, self._error)

    def AudioFile(self, ruta):
        return FakeAudioFile(ruta)


def test_escuchar_ok(monkeypatch):
    monkeypatch.setattr(voz, "sd", FakeSD())
    monkeypatch.setattr(voz, "sr", FakeSR(resultado="que hora es"))
    texto, error = voz.escuchar()
    assert texto == "que hora es" and error is None


def test_escuchar_no_entiende(monkeypatch):
    monkeypatch.setattr(voz, "sd", FakeSD())
    monkeypatch.setattr(voz, "sr", FakeSR(error=FakeUnknown()))
    texto, error = voz.escuchar()
    assert texto is None and "No te entendí" in error


def test_escuchar_sin_respuesta_servicio(monkeypatch):
    monkeypatch.setattr(voz, "sd", FakeSD())
    monkeypatch.setattr(voz, "sr", FakeSR(error=FakeRequest()))
    texto, error = voz.escuchar()
    assert texto is None and "no responde" in error


def test_escuchar_sin_microfono(monkeypatch):
    class SDNoMic:
        def rec(self, *a, **k):
            raise OSError("sin micrófono")

        def wait(self):
            pass

    monkeypatch.setattr(voz, "sd", SDNoMic())
    monkeypatch.setattr(voz, "sr", FakeSR(resultado="hola"))
    texto, error = voz.escuchar()
    assert texto is None and "micrófono" in error
