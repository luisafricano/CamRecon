"""Alta, edición, baja/activación y consulta de perfiles de empleados
(vinculados a las fotos de referencia usadas por el reconocimiento facial)."""

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from recognition import recognizer
from tracking.db import (
    actualizar_empleado,
    cambiar_estado_empleado,
    crear_empleado,
    eliminar_empleado as _eliminar_empleado,
    listar_empleados as _listar_empleados,
    obtener_empleado,
    obtener_empleado_por_clave,
)

CONOCIDOS_DIR = Path(__file__).parent / "conocidos"
INACTIVOS_DIR = CONOCIDOS_DIR / "_inactivos"
EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png"}


def normalizar_clave(nombre: str) -> str:
    """Convierte 'Luis Africano' -> 'Luis-Africano' (mismo criterio que usa recognition.py)."""
    limpio = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", limpio).strip("-")
    return limpio


def dir_fotos(activo: bool) -> Path:
    return CONOCIDOS_DIR if activo else INACTIVOS_DIR


def crear_perfil(
    nombre: str,
    apellido: str | None,
    cargo: str | None,
    legajo: str | None,
    fotos: list[tuple[bytes, str]],
) -> dict:
    """`fotos` es una lista de (bytes, extension). Se requiere al menos una."""
    nombre = nombre.strip()
    apellido = (apellido or "").strip() or None
    nombre_completo = f"{nombre} {apellido}".strip() if apellido else nombre
    clave = normalizar_clave(nombre_completo)

    if not nombre or not clave:
        raise ValueError("El nombre no puede estar vacío")
    if not fotos:
        raise ValueError("Se necesita al menos una foto de referencia")
    if obtener_empleado_por_clave(clave):
        raise ValueError(f"Ya existe un empleado con un nombre equivalente a '{nombre_completo}'")
    for _, extension in fotos:
        if extension.lower() not in EXTENSIONES_VALIDAS:
            raise ValueError("Las fotos deben ser .jpg, .jpeg o .png")

    CONOCIDOS_DIR.mkdir(exist_ok=True)
    _guardar_fotos(clave, fotos, CONOCIDOS_DIR)

    empleado_id = crear_empleado(
        nombre=nombre,
        apellido=apellido,
        cargo=(cargo or "").strip() or None,
        clave=clave,
        legajo=legajo or None,
        creado=datetime.now(timezone.utc).isoformat(),
    )
    recognizer.cargar_conocidos()
    return {"id": empleado_id, "nombre": nombre, "apellido": apellido, "clave": clave}


def _guardar_fotos(clave: str, fotos: list[tuple[bytes, str]], destino: Path) -> None:
    destino.mkdir(exist_ok=True)
    existentes = len(list(destino.glob(f"{clave}.*"))) + len(list(destino.glob(f"{clave}_*")))
    for i, (contenido, extension) in enumerate(fotos):
        if existentes == 0 and i == 0:
            nombre_archivo = f"{clave}{extension.lower()}"
        else:
            nombre_archivo = f"{clave}_{existentes + i + 1}{extension.lower()}"
        (destino / nombre_archivo).write_bytes(contenido)


def agregar_fotos(empleado_id: int, fotos: list[tuple[bytes, str]]) -> None:
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")
    for _, extension in fotos:
        if extension.lower() not in EXTENSIONES_VALIDAS:
            raise ValueError("Las fotos deben ser .jpg, .jpeg o .png")

    destino = dir_fotos(bool(empleado["activo"]))
    _guardar_fotos(empleado["clave"], fotos, destino)
    recognizer.cargar_conocidos()


def actualizar_perfil(
    empleado_id: int,
    nombre: str,
    apellido: str | None,
    cargo: str | None,
    legajo: str | None,
) -> None:
    if obtener_empleado(empleado_id) is None:
        raise ValueError("Empleado no encontrado")
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío")
    actualizar_empleado(
        empleado_id,
        nombre=nombre,
        apellido=(apellido or "").strip() or None,
        cargo=(cargo or "").strip() or None,
        legajo=legajo or None,
    )


def cambiar_estado(empleado_id: int, activo: bool) -> None:
    """Desactivar mueve las fotos fuera de `conocidos/` (deja de reconocerlo);
    activar las devuelve."""
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")
    if bool(empleado["activo"]) == activo:
        return

    origen = dir_fotos(bool(empleado["activo"]))
    destino = dir_fotos(activo)
    destino.mkdir(exist_ok=True)
    for foto in origen.glob(f"{empleado['clave']}*"):
        foto.rename(destino / foto.name)

    cambiar_estado_empleado(empleado_id, activo)
    recognizer.cargar_conocidos()


def ruta_foto_principal(empleado_id: int) -> Path | None:
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        return None
    directorio = dir_fotos(bool(empleado["activo"]))
    coincidencias = sorted(directorio.glob(f"{empleado['clave']}.*"))
    if coincidencias:
        return coincidencias[0]
    otras = sorted(directorio.glob(f"{empleado['clave']}_*"))
    return otras[0] if otras else None


def listar_fotos(empleado_id: int) -> list[str]:
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        return []
    directorio = dir_fotos(bool(empleado["activo"]))
    return sorted(f.name for f in directorio.glob(f"{empleado['clave']}*"))


def listar_perfiles() -> list[dict]:
    perfiles = _listar_empleados()
    for perfil in perfiles:
        directorio = dir_fotos(bool(perfil["activo"]))
        perfil["cantidad_fotos"] = len(list(directorio.glob(f"{perfil['clave']}*")))
    return perfiles


def eliminar_perfil(empleado_id: int) -> None:
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")
    for foto in CONOCIDOS_DIR.glob(f"{empleado['clave']}*"):
        foto.unlink()
    if INACTIVOS_DIR.exists():
        for foto in INACTIVOS_DIR.glob(f"{empleado['clave']}*"):
            foto.unlink()
    _eliminar_empleado(empleado_id)
    recognizer.cargar_conocidos()


def sincronizar_desde_conocidos() -> None:
    """Si hay fotos sueltas en conocidos/ sin perfil de empleado (caso de fotos cargadas
    a mano antes de que existiera este módulo), crea el registro automáticamente."""
    if not CONOCIDOS_DIR.exists():
        return

    claves_existentes = {e["clave"] for e in _listar_empleados()}
    for archivo in CONOCIDOS_DIR.iterdir():
        if archivo.is_dir() or archivo.suffix.lower() not in EXTENSIONES_VALIDAS:
            continue
        clave = archivo.stem.split("_")[0]
        if clave in claves_existentes:
            continue
        crear_empleado(
            nombre=clave.replace("-", " "),
            clave=clave,
            legajo=None,
            creado=datetime.now(timezone.utc).isoformat(),
        )
        claves_existentes.add(clave)
