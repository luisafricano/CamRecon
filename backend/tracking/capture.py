"""Captura de frames desde cámaras IP tipo Xiongmai (protocolo usado por apps como iCSee/XMEye)."""

import cv2


def construir_rtsp_url(ip: str, usuario: str, password: str, puerto: int = 554, canal: int = 1) -> str:
    return (
        f"rtsp://{usuario}:{password}@{ip}:{puerto}/"
        f"user={usuario}&password={password}&channel={canal}&stream=0.sdp?real_stream"
    )


def capturar_frame_jpeg(rtsp_url: str, timeout_ms: int = 8000) -> bytes | None:
    """Se conecta al stream, toma un único frame y lo devuelve como JPEG en bytes."""
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)

    try:
        ok, frame = cap.read()
    finally:
        cap.release()

    if not ok or frame is None:
        return None

    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        return None

    return buffer.tobytes()
