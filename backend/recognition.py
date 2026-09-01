"""
Lógica de reconocimiento facial.

Carga las imágenes de referencia desde la carpeta `conocidos/`, genera sus
codificaciones (encodings) una sola vez al iniciar el servicio, y expone una
función para comparar una imagen nueva contra esas codificaciones.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import face_recognition
import numpy as np

logger = logging.getLogger("recognition")

CONOCIDOS_DIR = Path(__file__).parent / "conocidos"
EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png"}
TOLERANCIA = 0.65  # menor = más estricto (subido para tolerar desenfoque de movimiento + video IR nocturno)


class FaceRecognizer:
    """Mantiene en memoria las codificaciones de los rostros conocidos."""

    def __init__(self, conocidos_dir: Path = CONOCIDOS_DIR) -> None:
        self.conocidos_dir = conocidos_dir
        self.encodings_conocidos: list[np.ndarray] = []
        self.nombres_conocidos: list[str] = []
        self.cargar_conocidos()

    def cargar_conocidos(self) -> None:
        """Recorre `conocidos/` y genera un encoding por cada imagen."""
        self.encodings_conocidos.clear()
        self.nombres_conocidos.clear()

        if not self.conocidos_dir.exists():
            logger.warning("La carpeta %s no existe", self.conocidos_dir)
            return

        for archivo in sorted(self.conocidos_dir.iterdir()):
            if archivo.suffix.lower() not in EXTENSIONES_VALIDAS:
                continue

            imagen = face_recognition.load_image_file(archivo)
            encodings = face_recognition.face_encodings(imagen)

            if not encodings:
                logger.warning("No se detectó ningún rostro en %s, se omite", archivo.name)
                continue

            # nombre de la persona = nombre del archivo sin extensión
            # (permite "juan.jpg", "juan_2.jpg", etc. para el mismo nombre)
            nombre = archivo.stem.split("_")[0]

            self.encodings_conocidos.append(encodings[0])
            self.nombres_conocidos.append(nombre)
            logger.info("Cargado rostro de referencia: %s", nombre)

        logger.info("Total de rostros conocidos cargados: %d", len(self.nombres_conocidos))

    def reconocer(self, imagen_bytes: bytes) -> list[dict]:
        """
        Recibe los bytes de una imagen, detecta los rostros presentes y
        devuelve una lista con el resultado de cada rostro encontrado.
        """
        np_array = np.frombuffer(imagen_bytes, dtype=np.uint8)
        imagen_bgr = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if imagen_bgr is None:
            raise ValueError("No se pudo decodificar la imagen recibida")

        imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)

        ubicaciones = face_recognition.face_locations(imagen_rgb)
        encodings = face_recognition.face_encodings(imagen_rgb, ubicaciones)

        resultados = []
        for encoding, ubicacion in zip(encodings, ubicaciones):
            nombre = "Desconocido"
            confianza = None

            if self.encodings_conocidos:
                distancias = face_recognition.face_distance(self.encodings_conocidos, encoding)
                mejor_indice = int(np.argmin(distancias))
                mejor_distancia = float(distancias[mejor_indice])

                if mejor_distancia <= TOLERANCIA:
                    nombre = self.nombres_conocidos[mejor_indice]
                    confianza = round(1 - mejor_distancia, 4)

            top, right, bottom, left = ubicacion
            resultados.append(
                {
                    "nombre": nombre,
                    "confianza": confianza,
                    "ubicacion": {"top": top, "right": right, "bottom": bottom, "left": left},
                }
            )

        return resultados


# Instancia única compartida por la app (se carga al importar el módulo)
recognizer = FaceRecognizer()
