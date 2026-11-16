"""Pruebas para el cerebro (src/cerebro.py).

El modelo real nunca se llama: post_json se reemplaza por respuestas
falsas con la forma exacta de Ollama y de Gemini.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cerebro
from web import WebError


USUARIO = {"nombre": "David Esteban Álvarez Rodriguez"}


def test_prompt_sistema_conoce_al_usuario():
    prompt = cerebro._prompt_sistema(USUARIO)
    assert "David Esteban Álvarez Rodriguez" in prompt
    assert "español" in prompt


def test_conversion_herramientas():
    d = cerebro.DEFINICIONES_HERRAMIENTAS[0]
    ollama = cerebro._a_ollama(d)
    assert ollama["type"] == "function"
    assert ollama["function"]["name"] == d["nombre"]
    gemini = cerebro._a_gemini(d)
    assert gemini["name"] == d["nombre"]
    assert gemini["parameters"]["type"] == "OBJECT"


def test_no_herramientas_peligrosas():
    nombres = {d["nombre"] for d in cerebro.DEFINICIONES_HERRAMIENTAS}
    for prohibido in ("apagar", "reiniciar", "bloquear", "decir", "voz", "escuchar", "salir"):
        assert prohibido not in nombres


def _fake_ollama_tool(monkeypatch):
    def _post(url, payload, headers=None, timeout=60):
        assert "localhost:11434" in url
        assert payload["model"] == "qwen2.5:3b"
        assert payload["stream"] is False
        return {"message": {"role": "assistant", "content": "",
                            "tool_calls": [{"function": {"name": "borrar_nota",
                                                        "arguments": {"numero": 1}}}]}}
    monkeypatch.setattr(cerebro, "post_json", _post)


def test_ollama_llama_herramienta(monkeypatch):
    _fake_ollama_tool(monkeypatch)
    ejecutores = {"borrar_nota": lambda numero: f"borrada {numero}"}
    assert cerebro.responder("deshazte de la primera nota", ejecutores, USUARIO) == "borrada 1"


def test_ollama_responde_texto(monkeypatch):
    def _post(url, payload, headers=None, timeout=60):
        return {"message": {"role": "assistant", "content": "¡Muy bien! ¿Y tú?",
                            "tool_calls": []}}
    monkeypatch.setattr(cerebro, "post_json", _post)
    assert cerebro.responder("como estas", {}, USUARIO) == "¡Muy bien! ¿Y tú?"


def test_ollama_caido_devuelve_none(monkeypatch):
    def _post(*a, **k):
        raise WebError("sin conexión")
    monkeypatch.setattr(cerebro, "post_json", _post)
    assert cerebro.responder("hola", {}, USUARIO) is None


def test_responder_herramienta_desconocida(monkeypatch):
    _fake_ollama_tool(monkeypatch)
    assert cerebro.responder("haz algo raro", {}, USUARIO) is None


def test_responder_argumentos_invalidos(monkeypatch):
    _fake_ollama_tool(monkeypatch)
    # borrar_nota espera "numero", pero el ejecutor no acepta argumentos.
    ejecutores = {"borrar_nota": lambda: "nada"}
    assert cerebro.responder("borra la nota", ejecutores, USUARIO) is None


def test_gemini_llama_herramienta(monkeypatch):
    monkeypatch.setenv("CASPER_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "clave-falsa")

    def _post(url, payload, headers=None, timeout=60):
        assert "generativelanguage.googleapis.com" in url
        assert "key=clave-falsa" in url
        if "tools" in payload:
            # Primera llamada: el modelo pide el clima.
            assert payload["tools"][0]["functionDeclarations"]
            return {"candidates": [{"content": {"parts": [
                {"functionCall": {"name": "clima", "args": {"ciudad": "Bogotá"}}}]}}]}
        # Segunda pasada: sin herramientas, el modelo responde en texto.
        assert "clima de Bogotá" in payload["contents"][0]["parts"][0]["text"]
        return {"candidates": [{"content": {"parts": [
            {"text": "En Bogotá hace 16°C y está nublado."}]}}]}
    monkeypatch.setattr(cerebro, "post_json", _post)
    ejecutores = {"clima": lambda ciudad: f"clima de {ciudad}"}
    assert cerebro.responder("qué clima hace en Bogotá", ejecutores, USUARIO) == \
        "En Bogotá hace 16°C y está nublado."


def test_gemini_responde_texto(monkeypatch):
    monkeypatch.setenv("CASPER_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "clave-falsa")
    monkeypatch.setattr(cerebro, "post_json",
                        lambda *a, **k: {"candidates": [{"content": {"parts": [
                            {"text": "Eres David Esteban Álvarez Rodriguez."}]}}]})
    assert "David" in cerebro.responder("quien soy", {}, USUARIO)


def test_gemini_sin_clave_devuelve_none(monkeypatch):
    monkeypatch.setenv("CASPER_LLM", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert cerebro.responder("hola", {}, USUARIO) is None


def test_prompt_permite_crear_texto():
    assert "poema" in cerebro._prompt_sistema(USUARIO)
    assert "dominio público" in cerebro._prompt_sistema(USUARIO)


def test_responder_429_mensaje_claro(monkeypatch):
    def _post(*a, **k):
        raise WebError("El servicio devolvió un error (HTTP 429).")
    monkeypatch.setattr(cerebro, "post_json", _post)
    r = cerebro.responder("hola", {}, USUARIO)
    assert "demasiadas preguntas" in r and "Espera un minuto" in r


def test_responder_debug_imprime_error(monkeypatch, capsys):
    monkeypatch.setenv("CASPER_DEBUG", "1")

    def _post(*a, **k):
        raise WebError("sin conexión")
    monkeypatch.setattr(cerebro, "post_json", _post)
    assert cerebro.responder("hola", {}, USUARIO) is None
    assert "[cerebro] sin conexión" in capsys.readouterr().err


def test_responder_sin_debug_no_imprime(monkeypatch, capsys):
    monkeypatch.delenv("CASPER_DEBUG", raising=False)

    def _post(*a, **k):
        raise WebError("sin conexión")
    monkeypatch.setattr(cerebro, "post_json", _post)
    assert cerebro.responder("hola", {}, USUARIO) is None
    assert capsys.readouterr().err == ""


def test_responder_incluye_hechos_y_historial(monkeypatch):
    vistos = {}

    def _post(url, payload, headers=None, timeout=60):
        vistos["payload"] = payload
        return {"message": {"role": "assistant", "content": "ok", "tool_calls": []}}
    monkeypatch.setattr(cerebro, "post_json", _post)
    contexto = {"historial": [("usuario", "nací en 2007"), ("casper", "Entendido.")],
                "hechos": ["nací en 2007"]}
    assert cerebro.responder("cuantos años tengo", {}, USUARIO, contexto) == "ok"
    mensajes = vistos["payload"]["messages"]
    assert "nací en 2007" in mensajes[0]["content"]  # sistema: hechos
    assert mensajes[1] == {"role": "user", "content": "nací en 2007"}
    assert mensajes[2] == {"role": "assistant", "content": "Entendido."}
    assert mensajes[3] == {"role": "user", "content": "cuantos años tengo"}


def test_gemini_historial_alterna_roles(monkeypatch):
    monkeypatch.setenv("CASPER_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "clave-falsa")
    vistos = {}

    def _post(url, payload, headers=None, timeout=60):
        vistos["payload"] = payload
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
    monkeypatch.setattr(cerebro, "post_json", _post)
    contexto = {"historial": [("usuario", "a"), ("casper", "b"), ("usuario", "c")],
                "hechos": []}
    cerebro.responder("d", {}, USUARIO, contexto)
    roles = [c["role"] for c in vistos["payload"]["contents"]]
    # Dos turnos de usuario seguidos (c y d) se fusionan: Gemini los rechaza.
    assert roles == ["user", "model", "user"]
    assert vistos["payload"]["contents"][2]["parts"][0]["text"] == "c\nd"


def test_prompt_identidad_casper():
    prompt = cerebro._prompt_sistema(USUARIO)
    assert "creado por él" in prompt
    assert "Nunca digas que eres un modelo de Google" in prompt


def test_segunda_pasada_usa_resultado(monkeypatch):
    # El caso real: el modelo llama a fecha para calcular la edad y la
    # respuesta final debe ser la edad, no la fecha cruda.
    llamadas = []

    def _post(url, payload, headers=None, timeout=60):
        llamadas.append(payload)
        if len(llamadas) == 1:
            return {"message": {"role": "assistant", "content": "",
                                "tool_calls": [{"function": {"name": "fecha",
                                                            "arguments": {}}}]}}
        return {"message": {"role": "assistant",
                            "content": "Tienes 19 años: naciste en 2007 y hoy es 2026.",
                            "tool_calls": []}}
    monkeypatch.setattr(cerebro, "post_json", _post)
    ejecutores = {"fecha": lambda: "Hoy es lunes 16/11/2026"}
    r = cerebro.responder("naci en 2007, eso significa que tengo cuantos anos?",
                          ejecutores, USUARIO)
    assert r == "Tienes 19 años: naciste en 2007 y hoy es 2026."
    # La segunda llamada lleva el resultado de la herramienta y no ofrece herramientas.
    assert "Hoy es lunes 16/11/2026" in llamadas[1]["messages"][1]["content"]
    assert "tools" not in llamadas[1]


def test_segunda_pasada_fallida_devuelve_resultado(monkeypatch):
    def _post(url, payload, headers=None, timeout=60):
        if "tools" in payload:
            return {"message": {"role": "assistant", "content": "",
                                "tool_calls": [{"function": {"name": "hora",
                                                            "arguments": {}}}]}}
        raise WebError("sin conexión")
    monkeypatch.setattr(cerebro, "post_json", _post)
    ejecutores = {"hora": lambda: "Son las 08:51"}
    assert cerebro.responder("que hora es", ejecutores, USUARIO) == "Son las 08:51"
