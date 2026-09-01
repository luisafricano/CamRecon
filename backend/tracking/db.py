"""Persistencia de detecciones en SQLite."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "tracking.db"


@contextmanager
def _conectar():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_db() -> None:
    with _conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS detecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona TEXT NOT NULL,
                camara_id TEXT NOT NULL,
                zona TEXT NOT NULL,
                confianza REAL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_persona_timestamp ON detecciones(persona, timestamp)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona TEXT NOT NULL,
                zona TEXT NOT NULL,
                camara_id TEXT NOT NULL,
                entrada TEXT NOT NULL,
                salida TEXT,
                duracion_segundos INTEGER
            )
            """
        )
        columnas_sesiones = {fila[1] for fila in conn.execute("PRAGMA table_info(sesiones)")}
        if "duracion_segundos" not in columnas_sesiones:
            conn.execute("ALTER TABLE sesiones ADD COLUMN duracion_segundos INTEGER")
            if "duracion_minutos" in columnas_sesiones:
                # Datos guardados antes de este cambio (estaban en minutos con decimales).
                conn.execute(
                    "UPDATE sesiones SET duracion_segundos = CAST(ROUND(duracion_minutos * 60) AS INTEGER) "
                    "WHERE duracion_minutos IS NOT NULL"
                )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sesiones_persona ON sesiones(persona, entrada)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zonas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS camaras (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                ip TEXT NOT NULL,
                puerto INTEGER NOT NULL DEFAULT 554,
                usuario TEXT NOT NULL DEFAULT 'admin',
                password TEXT NOT NULL DEFAULT '',
                zona_id INTEGER REFERENCES zonas(id)
            )
            """
        )

        # Migración para bases creadas antes de que existieran estas columnas.
        columnas_actuales = {fila[1] for fila in conn.execute("PRAGMA table_info(camaras)")}
        if "puerto" not in columnas_actuales:
            conn.execute("ALTER TABLE camaras ADD COLUMN puerto INTEGER NOT NULL DEFAULT 554")
        if "usuario" not in columnas_actuales:
            conn.execute(
                "ALTER TABLE camaras ADD COLUMN usuario TEXT NOT NULL DEFAULT 'admin'"
            )
        if "password" not in columnas_actuales:
            conn.execute("ALTER TABLE camaras ADD COLUMN password TEXT NOT NULL DEFAULT ''")
        if {"usuario", "password"} - columnas_actuales:
            # Las cámaras migradas antes de este cambio no tenían credenciales propias;
            # las completamos con las globales del .env para que sigan funcionando.
            conn.execute(
                "UPDATE camaras SET usuario = ?, password = ? WHERE usuario = 'admin' AND password = ''",
                (os.environ.get("CAMERA_USER", "admin"), os.environ.get("CAMERA_PASSWORD", "")),
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT,
                cargo TEXT,
                clave TEXT NOT NULL UNIQUE,
                legajo TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                creado TEXT NOT NULL
            )
            """
        )
        columnas_empleados = {fila[1] for fila in conn.execute("PRAGMA table_info(empleados)")}
        if "apellido" not in columnas_empleados:
            conn.execute("ALTER TABLE empleados ADD COLUMN apellido TEXT")
        if "cargo" not in columnas_empleados:
            conn.execute("ALTER TABLE empleados ADD COLUMN cargo TEXT")
        if "activo" not in columnas_empleados:
            conn.execute("ALTER TABLE empleados ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                creado TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens_sesion (
                token TEXT PRIMARY KEY,
                usuario TEXT NOT NULL,
                creado TEXT NOT NULL,
                expira TEXT NOT NULL
            )
            """
        )


def registrar_deteccion(persona: str, camara_id: str, zona: str, confianza: float | None, timestamp: str) -> None:
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO detecciones (persona, camara_id, zona, confianza, timestamp) VALUES (?, ?, ?, ?, ?)",
            (persona, camara_id, zona, confianza, timestamp),
        )


def obtener_detecciones(persona: str, desde: str | None = None, hasta: str | None = None) -> list[dict]:
    query = "SELECT persona, camara_id, zona, confianza, timestamp FROM detecciones WHERE persona = ?"
    params: list = [persona]

    if desde:
        query += " AND timestamp >= ?"
        params.append(desde)
    if hasta:
        query += " AND timestamp <= ?"
        params.append(hasta)

    query += " ORDER BY timestamp ASC"

    with _conectar() as conn:
        cur = conn.execute(query, params)
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def listar_personas() -> list[str]:
    with _conectar() as conn:
        cur = conn.execute("SELECT DISTINCT persona FROM detecciones ORDER BY persona")
        return [fila[0] for fila in cur.fetchall()]


def listar_detecciones_recientes(limite: int = 20) -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT persona, camara_id, zona, confianza, timestamp FROM detecciones "
            "ORDER BY timestamp DESC LIMIT ?",
            (limite,),
        )
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def obtener_sesion_abierta(persona: str) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT id, persona, zona, camara_id, entrada, salida, duracion_minutos "
            "FROM sesiones WHERE persona = ? AND salida IS NULL "
            "ORDER BY entrada DESC LIMIT 1",
            (persona,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def abrir_sesion(persona: str, zona: str, camara_id: str, entrada: str) -> int:
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO sesiones (persona, zona, camara_id, entrada) VALUES (?, ?, ?, ?)",
            (persona, zona, camara_id, entrada),
        )
        return cur.lastrowid


def cerrar_sesion(sesion_id: int, salida: str, duracion_segundos: int) -> None:
    with _conectar() as conn:
        conn.execute(
            "UPDATE sesiones SET salida = ?, duracion_segundos = ? WHERE id = ?",
            (salida, duracion_segundos, sesion_id),
        )


def listar_sesiones(persona: str) -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT persona, zona, camara_id, entrada, salida, duracion_segundos "
            "FROM sesiones WHERE persona = ? ORDER BY entrada ASC",
            (persona,),
        )
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def listar_sesiones_recientes(limite: int = 20) -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT persona, zona, camara_id, entrada, salida, duracion_segundos "
            "FROM sesiones ORDER BY entrada DESC LIMIT ?",
            (limite,),
        )
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


# --- Zonas ---------------------------------------------------------------


def crear_zona(nombre: str) -> int:
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO zonas (nombre) VALUES (?) "
            "ON CONFLICT(nombre) DO UPDATE SET nombre = excluded.nombre",
            (nombre,),
        )
        fila = conn.execute("SELECT id FROM zonas WHERE nombre = ?", (nombre,)).fetchone()
        return fila[0]


def listar_zonas() -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute("SELECT id, nombre FROM zonas ORDER BY nombre ASC")
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def eliminar_zona(zona_id: int) -> None:
    with _conectar() as conn:
        conn.execute("UPDATE camaras SET zona_id = NULL WHERE zona_id = ?", (zona_id,))
        conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))


# --- Cámaras ---------------------------------------------------------------


def crear_camara(
    camara_id: str,
    nombre: str,
    ip: str,
    puerto: int = 554,
    usuario: str = "admin",
    password: str = "",
) -> None:
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO camaras (id, nombre, ip, puerto, usuario, password) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET nombre = excluded.nombre, ip = excluded.ip, "
            "puerto = excluded.puerto, usuario = excluded.usuario, password = excluded.password",
            (camara_id, nombre, ip, puerto, usuario, password),
        )


def listar_camaras() -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute(
            """
            SELECT c.id, c.nombre, c.ip, c.puerto, c.usuario, c.password, c.zona_id, z.nombre AS zona_nombre
            FROM camaras c
            LEFT JOIN zonas z ON z.id = c.zona_id
            ORDER BY c.nombre ASC
            """
        )
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def obtener_camara(camara_id: str) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            """
            SELECT c.id, c.nombre, c.ip, c.puerto, c.usuario, c.password, c.zona_id, z.nombre AS zona_nombre
            FROM camaras c
            LEFT JOIN zonas z ON z.id = c.zona_id
            WHERE c.id = ?
            """,
            (camara_id,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def asignar_zona_camara(camara_id: str, zona_id: int | None) -> None:
    with _conectar() as conn:
        conn.execute("UPDATE camaras SET zona_id = ? WHERE id = ?", (zona_id, camara_id))


def eliminar_camara(camara_id: str) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM camaras WHERE id = ?", (camara_id,))


# --- Empleados ---------------------------------------------------------------


def crear_empleado(
    nombre: str,
    clave: str,
    legajo: str | None,
    creado: str,
    apellido: str | None = None,
    cargo: str | None = None,
) -> int:
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO empleados (nombre, apellido, cargo, clave, legajo, creado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, apellido, cargo, clave, legajo, creado),
        )
        return cur.lastrowid


def listar_empleados() -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT id, nombre, apellido, cargo, clave, legajo, activo, creado "
            "FROM empleados ORDER BY nombre ASC"
        )
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def obtener_empleado(empleado_id: int) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT id, nombre, apellido, cargo, clave, legajo, activo, creado "
            "FROM empleados WHERE id = ?",
            (empleado_id,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def obtener_empleado_por_clave(clave: str) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT id, nombre, apellido, cargo, clave, legajo, activo, creado "
            "FROM empleados WHERE clave = ?",
            (clave,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def actualizar_empleado(
    empleado_id: int,
    nombre: str,
    apellido: str | None,
    cargo: str | None,
    legajo: str | None,
) -> None:
    with _conectar() as conn:
        conn.execute(
            "UPDATE empleados SET nombre = ?, apellido = ?, cargo = ?, legajo = ? WHERE id = ?",
            (nombre, apellido, cargo, legajo, empleado_id),
        )


def cambiar_estado_empleado(empleado_id: int, activo: bool) -> None:
    with _conectar() as conn:
        conn.execute("UPDATE empleados SET activo = ? WHERE id = ?", (int(activo), empleado_id))


def eliminar_empleado(empleado_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM empleados WHERE id = ?", (empleado_id,))


# --- Usuarios / sesiones de login ------------------------------------------


def crear_usuario(usuario: str, password_hash: str, salt: str, creado: str) -> None:
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO usuarios (usuario, password_hash, salt, creado) VALUES (?, ?, ?, ?)",
            (usuario, password_hash, salt, creado),
        )


def listar_usuarios() -> list[dict]:
    with _conectar() as conn:
        cur = conn.execute("SELECT id, usuario, creado FROM usuarios ORDER BY usuario ASC")
        columnas = [d[0] for d in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def obtener_usuario(usuario: str) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT id, usuario, password_hash, salt, creado FROM usuarios WHERE usuario = ?",
            (usuario,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def crear_token(token: str, usuario: str, creado: str, expira: str) -> None:
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO tokens_sesion (token, usuario, creado, expira) VALUES (?, ?, ?, ?)",
            (token, usuario, creado, expira),
        )


def obtener_token(token: str) -> dict | None:
    with _conectar() as conn:
        cur = conn.execute(
            "SELECT token, usuario, creado, expira FROM tokens_sesion WHERE token = ?",
            (token,),
        )
        fila = cur.fetchone()
        if fila is None:
            return None
        columnas = [d[0] for d in cur.description]
        return dict(zip(columnas, fila))


def eliminar_token(token: str) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM tokens_sesion WHERE token = ?", (token,))
