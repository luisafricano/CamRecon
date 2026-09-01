"""
Login simple (usuario/contraseña) para mostrar el sistema a un cliente.

No es un esquema de autenticación robusto para producción: gatea el acceso a las
páginas del frontend, pero no protege cada endpoint de la API individualmente.
Si el sistema se va a usar con datos reales de una empresa, conviene reforzar esto
(proteger también la API, expirar tokens más agresivamente, HTTPS obligatorio, etc.).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import env_store
from tracking.db import (
    crear_token as _crear_token,
    crear_usuario as _crear_usuario,
    eliminar_token,
    listar_usuarios,
    obtener_token,
    obtener_usuario,
)

DURACION_TOKEN = timedelta(hours=12)
ITERACIONES_HASH = 100_000


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERACIONES_HASH).hex()


def crear_usuario(usuario: str, password: str) -> None:
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    _crear_usuario(usuario, password_hash, salt, datetime.now(timezone.utc).isoformat())


def sembrar_usuario_inicial() -> None:
    """Crea el usuario admin de fábrica la primera vez que arranca el sistema.
    El usuario/contraseña salen del .env (ADMIN_USUARIO_INICIAL / ADMIN_PASSWORD_INICIAL)."""
    if listar_usuarios():
        return
    usuario = env_store.leer("ADMIN_USUARIO_INICIAL", "reconadmin")
    password = env_store.leer("ADMIN_PASSWORD_INICIAL", "recon123")
    crear_usuario(usuario, password)


def autenticar(usuario: str, password: str) -> str | None:
    """Si las credenciales son correctas, crea y devuelve un token nuevo."""
    fila = obtener_usuario(usuario)
    if fila is None:
        return None
    if _hash_password(password, fila["salt"]) != fila["password_hash"]:
        return None

    token = secrets.token_urlsafe(32)
    ahora = datetime.now(timezone.utc)
    _crear_token(token, usuario, ahora.isoformat(), (ahora + DURACION_TOKEN).isoformat())
    return token


def validar_token(token: str | None) -> str | None:
    """Devuelve el usuario dueño del token si es válido y no expiró."""
    if not token:
        return None
    fila = obtener_token(token)
    if fila is None:
        return None
    if datetime.fromisoformat(fila["expira"]) < datetime.now(timezone.utc):
        eliminar_token(token)
        return None
    return fila["usuario"]


def cerrar_sesion(token: str) -> None:
    eliminar_token(token)
