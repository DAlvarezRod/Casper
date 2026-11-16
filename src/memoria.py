# Memoria de Casper (Fase 7): lo que sabe de ti, guardado en SQLite.
# Dos tablas, dos clases de memoria:
# - hechos: datos duraderos ("nací en 2007", "prefiero respuestas cortas").
#   Sobreviven a reinicios. Solo se guardan cuando TÚ dices "recuerda que...".
# - historial: los últimos turnos de la conversación. Es memoria de corto
#   plazo: el cerebro la ve para entender "cuantos años tengo" después de
#   "nací en 2007", pero no pretende ser un diario permanente.
# SQLite es de la librería estándar: un archivo, sin servidor, sin claves.
import os
import sqlite3
from datetime import datetime

DB_PATH = "casper.db"
MAX_TURNOS = 100  # el historial se poda: recordar todo, siempre, no escala


def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS hechos ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL, creado TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS historial ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, rol TEXT NOT NULL, "
        "texto TEXT NOT NULL, creado TEXT NOT NULL)")
    return conn


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def guardar_hecho(texto):
    # Devuelve el id del hecho guardado.
    conn = _conectar()
    try:
        cur = conn.execute("INSERT INTO hechos (texto, creado) VALUES (?, ?)",
                           (texto, _ahora()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def listar_hechos():
    # [(id, texto)] en orden de creación.
    conn = _conectar()
    try:
        return conn.execute("SELECT id, texto FROM hechos ORDER BY id").fetchall()
    finally:
        conn.close()


def borrar_hecho(numero):
    # Borra por posición (1 = el primer hecho) y devuelve su texto, o None.
    hechos = listar_hechos()
    try:
        hid, texto = hechos[int(numero) - 1]
    except (ValueError, IndexError):
        return None
    conn = _conectar()
    try:
        conn.execute("DELETE FROM hechos WHERE id = ?", (hid,))
        conn.commit()
    finally:
        conn.close()
    return texto


def guardar_turno(rol, texto):
    # rol: "usuario" o "casper". Después de guardar, poda lo viejo.
    conn = _conectar()
    try:
        conn.execute("INSERT INTO historial (rol, texto, creado) VALUES (?, ?, ?)",
                     (rol, texto, _ahora()))
        conn.execute(
            "DELETE FROM historial WHERE id NOT IN "
            "(SELECT id FROM historial ORDER BY id DESC LIMIT ?)", (MAX_TURNOS,))
        conn.commit()
    finally:
        conn.close()


def obtener_historial(n=10):
    # Los últimos n turnos, en orden cronológico (el más viejo primero).
    conn = _conectar()
    try:
        filas = conn.execute(
            "SELECT rol, texto FROM historial ORDER BY id DESC LIMIT ?",
            (n,)).fetchall()
        return list(reversed(filas))
    finally:
        conn.close()


def limpiar_memoria():
    # Borra hechos e historial. No hay papelera: pregúntale al usuario antes.
    conn = _conectar()
    try:
        conn.execute("DELETE FROM hechos")
        conn.execute("DELETE FROM historial")
        conn.commit()
    finally:
        conn.close()
