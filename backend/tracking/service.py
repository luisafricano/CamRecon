"""Loop en background que muestrea cada cámara, reconoce rostros y registra detecciones."""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from recognition import recognizer

from .capture import capturar_frame_jpeg, construir_rtsp_url
from .db import registrar_deteccion
from .session_tracker import procesar_evento

logger = logging.getLogger("tracking.service")


class TrackingService:
    def __init__(self, obtener_camaras: Callable[[], list[dict]], intervalo_segundos: int = 15):
        """`obtener_camaras` se llama en cada vuelta del loop y debe devolver diccionarios
        con id/nombre/ip/puerto/usuario/password/zona propios de cada cámara, así los
        cambios hechos desde la interfaz (altas, bajas, credenciales, zona) se aplican
        sin reiniciar el servicio."""
        self.obtener_camaras = obtener_camaras
        self.intervalo_segundos = intervalo_segundos
        self._hilo: threading.Thread | None = None
        self._detener = threading.Event()
        self.ultimo_error: dict[str, str] = {}

    @property
    def activo(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    def iniciar(self) -> None:
        if self.activo:
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()
        logger.info("Tracking iniciado (intervalo=%ss)", self.intervalo_segundos)

    def detener(self) -> None:
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=5)
        logger.info("Tracking detenido")

    def _loop(self) -> None:
        with ThreadPoolExecutor(max_workers=4) as executor:
            while not self._detener.is_set():
                inicio = datetime.now(timezone.utc)
                camaras = self.obtener_camaras()
                list(executor.map(self._procesar_camara, camaras))
                transcurrido = (datetime.now(timezone.utc) - inicio).total_seconds()
                espera = max(self.intervalo_segundos - transcurrido, 0)
                self._detener.wait(espera)

    def _procesar_camara(self, camara: dict) -> None:
        url = construir_rtsp_url(
            camara["ip"], camara["usuario"], camara["password"], puerto=camara.get("puerto", 554)
        )

        try:
            jpeg = capturar_frame_jpeg(url)
            if jpeg is None:
                self.ultimo_error[camara["id"]] = "No se pudo capturar frame"
                logger.warning("No se pudo capturar frame de %s", camara["nombre"])
                return

            resultados = recognizer.reconocer(jpeg)
            self.ultimo_error.pop(camara["id"], None)
        except Exception as exc:
            self.ultimo_error[camara["id"]] = str(exc)
            logger.exception("Error procesando cámara %s", camara["nombre"])
            return

        ahora = datetime.now(timezone.utc).isoformat()
        for resultado in resultados:
            if resultado["nombre"] == "Desconocido":
                continue

            registrar_deteccion(
                persona=resultado["nombre"],
                camara_id=camara["id"],
                zona=camara["zona"],
                confianza=resultado["confianza"],
                timestamp=ahora,
            )
            procesar_evento(
                persona=resultado["nombre"],
                zona=camara["zona"],
                camara_id=camara["id"],
                timestamp=ahora,
            )
