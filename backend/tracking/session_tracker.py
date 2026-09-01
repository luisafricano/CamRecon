"""
Mantiene, por persona, una única sesión "abierta" (la zona en la que está ahora mismo).

Cuando la persona es detectada en una cámara distinta a la de su sesión abierta,
se cierra esa sesión (con la duración = tiempo entre que entró y que apareció en
la otra cámara) y se abre una nueva en la zona nueva.
"""

import logging
from datetime import datetime

from formato import formatear_duracion

from .db import abrir_sesion, cerrar_sesion, obtener_sesion_abierta

logger = logging.getLogger("tracking.recorrido")


def procesar_evento(persona: str, zona: str, camara_id: str, timestamp: str) -> None:
    sesion = obtener_sesion_abierta(persona)

    if sesion is None:
        abrir_sesion(persona, zona, camara_id, timestamp)
        logger.info("%s entró a '%s'", persona, zona)
        return

    if sesion["zona"] == zona:
        # sigue en la misma zona, no hay transición que registrar
        return

    entrada = datetime.fromisoformat(sesion["entrada"])
    salida_dt = datetime.fromisoformat(timestamp)
    duracion_segundos = round((salida_dt - entrada).total_seconds())

    cerrar_sesion(sesion["id"], timestamp, duracion_segundos)
    logger.info(
        "%s salió de '%s' (permaneció %s) y entró a '%s'",
        persona,
        sesion["zona"],
        formatear_duracion(duracion_segundos),
        zona,
    )

    abrir_sesion(persona, zona, camara_id, timestamp)
