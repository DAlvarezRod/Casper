"""Pruebas para la memoria (src/memoria.py).

Cada prueba usa su propia base de datos temporal: la memoria real
de Casper nunca se toca desde los tests.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import memoria


def test_hechos_guardar_listar_borrar(monkeypatch, tmp_path):
    monkeypatch.setattr(memoria, "DB_PATH", str(tmp_path / "t.db"))
    assert memoria.listar_hechos() == []
    assert memoria.guardar_hecho("nací en 2007") == 1
    memoria.guardar_hecho("prefiero respuestas cortas")
    assert [t for _, t in memoria.listar_hechos()] == [
        "nací en 2007", "prefiero respuestas cortas"]
    assert memoria.borrar_hecho("1") == "nací en 2007"
    assert [t for _, t in memoria.listar_hechos()] == ["prefiero respuestas cortas"]
    assert memoria.borrar_hecho("99") is None
    assert memoria.borrar_hecho("x") is None


def test_historial_orden_y_poda(monkeypatch, tmp_path):
    monkeypatch.setattr(memoria, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(memoria, "MAX_TURNOS", 3)
    for i in range(5):
        memoria.guardar_turno("usuario", f"pregunta {i}")
    assert [t for _, t in memoria.obtener_historial(10)] == [
        "pregunta 2", "pregunta 3", "pregunta 4"]
    assert memoria.obtener_historial(2) == [
        ("usuario", "pregunta 3"), ("usuario", "pregunta 4")]


def test_memoria_persiste_entre_conexiones(monkeypatch, tmp_path):
    monkeypatch.setattr(memoria, "DB_PATH", str(tmp_path / "t.db"))
    memoria.guardar_hecho("nací en 2007")
    # Nueva "sesión": los datos siguen ahí.
    assert [t for _, t in memoria.listar_hechos()] == ["nací en 2007"]


def test_limpiar_memoria(monkeypatch, tmp_path):
    monkeypatch.setattr(memoria, "DB_PATH", str(tmp_path / "t.db"))
    memoria.guardar_hecho("x")
    memoria.guardar_turno("usuario", "hola")
    memoria.limpiar_memoria()
    assert memoria.listar_hechos() == []
    assert memoria.obtener_historial() == []
