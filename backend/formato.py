"""Formato consistente de fechas y duraciones para toda la app (API, logs y reportes)."""

from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_HORARIA_LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")


def formatear_duracion(segundos: float | int | None) -> str:
    """Convierte segundos a 'HH:MM:SS'. Nunca en minutos con decimales."""
    if segundos is None:
        return "-"
    segundos = int(round(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{seg:02d}"


def formatear_fecha(iso: str | None) -> str:
    """Convierte un timestamp ISO (UTC) a 'YYYY-MM-DD HH:MM:SS' en horario de Argentina."""
    if not iso:
        return "-"
    dt = datetime.fromisoformat(iso)
    return dt.astimezone(ZONA_HORARIA_LOCAL).strftime("%Y-%m-%d %H:%M:%S")
