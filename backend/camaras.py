"""CRUD de cámaras/zonas, prueba de conexión y generación del stream en vivo (MJPEG)."""

import re
import time
import unicodedata
from collections.abc import Generator

import cv2

import env_store
from tracking.capture import capturar_frame_jpeg, construir_rtsp_url
from tracking.db import crear_camara, eliminar_camara
from tracking.db import listar_camaras as _listar_camaras
from tracking.db import obtener_camara

# Usamos el sub-stream (más liviano) para la vista en vivo, así no compite tanto
# por ancho de banda / conexiones RTSP con el muestreo del tracking (que usa el
# stream principal). No todos los firmwares lo soportan, pero la mayoría sí.
CANAL_VISTA_EN_VIVO = 1


def generar_id(nombre: str) -> str:
    limpio = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", limpio).strip("_").lower()
    return limpio or "camara"


def listar_camaras() -> list[dict]:
    """Cámaras con sus credenciales "reales" tomadas del .env (fuente de verdad),
    no de lo que haya quedado guardado en la base de datos."""
    camaras = _listar_camaras()
    for c in camaras:
        usuario, password = env_store.obtener_credenciales_camara(
            c["id"], c.get("usuario", "admin"), c.get("password", "")
        )
        c["usuario"] = usuario
        c["password"] = password
    return camaras


def obtener_credenciales(camara_id: str) -> tuple[str, str] | None:
    camara = obtener_camara(camara_id)
    if camara is None:
        return None
    return env_store.obtener_credenciales_camara(
        camara_id, camara.get("usuario", "admin"), camara.get("password", "")
    )


def probar_conexion(ip: str, puerto: int, usuario: str, password: str) -> dict:
    """Intenta capturar un frame para validar IP/puerto/usuario/contraseña antes de guardar."""
    url = construir_rtsp_url(ip, usuario, password, puerto=puerto)
    try:
        jpeg = capturar_frame_jpeg(url, timeout_ms=6000)
    except Exception as exc:
        return {"ok": False, "detalle": f"Error de conexión: {exc}"}

    if jpeg is None:
        return {
            "ok": False,
            "detalle": (
                "No se pudo obtener imagen. Revisá IP, puerto, usuario y contraseña, "
                "y que la cámara esté en la misma red que el servidor."
            ),
        }
    return {"ok": True, "detalle": f"Conexión exitosa ({len(jpeg)} bytes recibidos)."}


def crear_camara_nueva(nombre: str, ip: str, puerto: int, usuario: str, password: str) -> dict:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la cámara no puede estar vacío")
    if not ip.strip():
        raise ValueError("La IP no puede estar vacía")

    camara_id = generar_id(nombre)
    existente = obtener_camara(camara_id)
    sufijo = 2
    id_final = camara_id
    while existente is not None:
        id_final = f"{camara_id}_{sufijo}"
        existente = obtener_camara(id_final)
        sufijo += 1

    # La base guarda un valor "de referencia" por compatibilidad con el esquema,
    # pero la credencial que realmente se usa para conectar vive en el .env.
    crear_camara(id_final, nombre, ip.strip(), puerto=puerto, usuario=usuario, password=password)
    env_store.guardar_credenciales_camara(id_final, usuario, password)
    return {"id": id_final, "nombre": nombre}


def actualizar_credenciales_camara(camara_id: str, usuario: str, password: str) -> None:
    if obtener_camara(camara_id) is None:
        raise ValueError("Cámara no encontrada")
    env_store.guardar_credenciales_camara(camara_id, usuario, password)


def eliminar_camara_existente(camara_id: str) -> None:
    if obtener_camara(camara_id) is None:
        raise ValueError("Cámara no encontrada")
    eliminar_camara(camara_id)
    env_store.eliminar_credenciales_camara(camara_id)


def generar_mjpeg(ip: str, usuario: str, password: str, puerto: int = 554, calidad: int = 60, fps_max: int = 8) -> Generator[bytes, None, None]:
    url = construir_rtsp_url(ip, usuario, password, puerto=puerto, canal=CANAL_VISTA_EN_VIVO)
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 8000)

    intervalo_min = 1 / fps_max

    try:
        while True:
            inicio = time.monotonic()
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, calidad])
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

            transcurrido = time.monotonic() - inicio
            if transcurrido < intervalo_min:
                time.sleep(intervalo_min - transcurrido)
    finally:
        cap.release()
