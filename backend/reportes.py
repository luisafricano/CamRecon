"""Cálculo de tiempo total y generación del reporte descargable de recorrido por empleado."""

from datetime import datetime, timezone

from formato import formatear_duracion, formatear_fecha
from tracking.db import listar_sesiones, obtener_empleado


def calcular_tiempo_total_segundos(sesiones: list[dict]) -> int:
    """Suma la duración de todos los tramos. El tramo abierto (todavía sin salida)
    cuenta el tiempo transcurrido hasta ahora."""
    ahora = datetime.now(timezone.utc)
    total = 0
    for s in sesiones:
        if s["duracion_segundos"] is not None:
            total += s["duracion_segundos"]
        else:
            entrada = datetime.fromisoformat(s["entrada"])
            total += int((ahora - entrada).total_seconds())
    return total


def generar_reporte_texto(empleado_id: int) -> tuple[str, str]:
    """Devuelve (nombre_de_archivo, contenido) de un reporte de recorrido en texto plano."""
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")

    sesiones = listar_sesiones(empleado["clave"])
    total_segundos = calcular_tiempo_total_segundos(sesiones)
    nombre_completo = " ".join(filter(None, [empleado["nombre"], empleado["apellido"]]))

    lineas = [
        "REPORTE DE RECORRIDO",
        "=" * 60,
        f"Empleado: {nombre_completo}",
    ]
    if empleado["cargo"]:
        lineas.append(f"Cargo: {empleado['cargo']}")
    if empleado["legajo"]:
        lineas.append(f"Legajo: {empleado['legajo']}")
    lineas.append(f"Generado: {formatear_fecha(datetime.now(timezone.utc).isoformat())}")
    lineas.append("")

    if not sesiones:
        lineas.append("Todavía no hay detecciones registradas para esta persona.")
    else:
        col_zona, col_fecha, col_dur = 26, 21, 12
        encabezado = f"{'Zona':<{col_zona}}{'Entrada':<{col_fecha}}{'Salida':<{col_fecha}}{'Duración':<{col_dur}}"
        lineas.append(encabezado)
        lineas.append("-" * len(encabezado))
        for s in sesiones:
            salida_txt = formatear_fecha(s["salida"]) if s["salida"] else "en curso"
            duracion_txt = (
                formatear_duracion(s["duracion_segundos"])
                if s["duracion_segundos"] is not None
                else "en curso"
            )
            lineas.append(
                f"{s['zona']:<{col_zona}}{formatear_fecha(s['entrada']):<{col_fecha}}"
                f"{salida_txt:<{col_fecha}}{duracion_txt:<{col_dur}}"
            )
        lineas.append("")
        lineas.append(f"Tiempo total detectado por el sistema: {formatear_duracion(total_segundos)}")

    contenido = "\n".join(lineas) + "\n"
    nombre_archivo = f"recorrido_{empleado['clave']}.txt"
    return nombre_archivo, contenido
