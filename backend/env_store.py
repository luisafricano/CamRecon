"""
Lee y escribe variables sensibles (usuarios/contraseñas) directamente en el archivo
`.env`, para que ninguna credencial quede hardcodeada en el código ni en la base de
datos en texto plano sin control — todo pasa por acá.

Cuando se vincula o edita una cámara desde el panel, sus credenciales se guardan con
una clave propia (`CAM_<ID>_USER` / `CAM_<ID>_PASSWORD`) en este mismo archivo.
"""

import os
import re
from pathlib import Path

from dotenv import set_key, unset_key

ENV_PATH = Path(__file__).parent / ".env"


def _asegurar_archivo() -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()


def guardar(clave: str, valor: str) -> None:
    """Escribe (o actualiza) una variable en `.env` y la aplica en caliente."""
    _asegurar_archivo()
    set_key(str(ENV_PATH), clave, valor, quote_mode="never")
    os.environ[clave] = valor


def eliminar(clave: str) -> None:
    _asegurar_archivo()
    unset_key(str(ENV_PATH), clave)
    os.environ.pop(clave, None)


def leer(clave: str, default: str | None = None) -> str | None:
    return os.environ.get(clave, default)


def _sufijo_camara(camara_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", camara_id.upper())


def clave_camara_usuario(camara_id: str) -> str:
    return f"CAM_{_sufijo_camara(camara_id)}_USER"


def clave_camara_password(camara_id: str) -> str:
    return f"CAM_{_sufijo_camara(camara_id)}_PASSWORD"


def guardar_credenciales_camara(camara_id: str, usuario: str, password: str) -> None:
    guardar(clave_camara_usuario(camara_id), usuario)
    guardar(clave_camara_password(camara_id), password)


def eliminar_credenciales_camara(camara_id: str) -> None:
    eliminar(clave_camara_usuario(camara_id))
    eliminar(clave_camara_password(camara_id))


def obtener_credenciales_camara(camara_id: str, usuario_defecto: str, password_defecto: str) -> tuple[str, str]:
    """Las credenciales "de verdad" viven en `.env`. Si una cámara todavía no tiene
    variables propias (caso de datos migrados antes de este cambio), se usan los
    valores por defecto que traía guardados (ej. desde la base de datos)."""
    usuario = leer(clave_camara_usuario(camara_id), usuario_defecto)
    password = leer(clave_camara_password(camara_id), password_defecto)
    return usuario, password
