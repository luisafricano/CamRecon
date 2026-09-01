"""
API REST de reconocimiento facial.

Endpoint principal:
    POST /reconocer/  -> recibe una imagen y devuelve los rostros detectados.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse

import auth as auth_mod
import camaras as camaras_mod
import empleados as empleados_mod
import env_store
import reportes as reportes_mod
from recognition import recognizer
from tracking.db import (
    asignar_zona_camara,
    crear_camara,
    crear_zona,
    eliminar_zona,
    inicializar_db,
    listar_camaras,
    listar_detecciones_recientes,
    listar_personas,
    listar_sesiones,
    listar_sesiones_recientes,
    listar_zonas,
    obtener_camara,
    obtener_empleado,
)
from tracking.service import TrackingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

load_dotenv()

CAMERA_USER = os.environ["CAMERA_USER"]
CAMERA_PASSWORD = os.environ["CAMERA_PASSWORD"]

# Log legible de entradas/salidas por zona, además de la base de datos.
_log_recorrido_path = Path(__file__).parent / "tracking_recorrido.log"
_handler_recorrido = logging.FileHandler(_log_recorrido_path, encoding="utf-8")
_handler_recorrido.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logging.getLogger("tracking.recorrido").addHandler(_handler_recorrido)
logging.getLogger("tracking.recorrido").setLevel(logging.INFO)


def _camaras_para_tracking() -> list[dict]:
    """Sólo las cámaras que ya tienen una zona asignada entran al muestreo de tracking."""
    return [
        {
            "id": c["id"],
            "nombre": c["nombre"],
            "ip": c["ip"],
            "puerto": c["puerto"],
            "usuario": c["usuario"],
            "password": c["password"],
            "zona": c["zona_nombre"],
        }
        for c in camaras_mod.listar_camaras()
        if c["zona_nombre"]
    ]


tracking_service = TrackingService(
    obtener_camaras=_camaras_para_tracking,
    intervalo_segundos=int(os.environ.get("TRACKING_INTERVALO_SEGUNDOS", 15)),
)


def _migrar_camaras_iniciales() -> None:
    """La primera vez que corre, importa cameras.json a la base (luego se administra
    todo desde la API / interfaz, el archivo json deja de usarse)."""
    if listar_camaras():
        return
    ruta = Path(__file__).parent / "cameras.json"
    if not ruta.exists():
        return
    with open(ruta, encoding="utf-8") as f:
        camaras_iniciales = json.load(f)
    for c in camaras_iniciales:
        zona_id = crear_zona(c["zona"])
        crear_camara(c["id"], c["nombre"], c["ip"], puerto=554, usuario=CAMERA_USER, password=CAMERA_PASSWORD)
        env_store.guardar_credenciales_camara(c["id"], CAMERA_USER, CAMERA_PASSWORD)
        asignar_zona_camara(c["id"], zona_id)

app = FastAPI(
    title="API de Reconocimiento Facial",
    description="Microservicio para detectar e identificar rostros en imágenes.",
    version="1.0.0",
)

# En producción conviene restringir esto al dominio real del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    inicializar_db()
    _migrar_camaras_iniciales()
    empleados_mod.sincronizar_desde_conocidos()
    auth_mod.sembrar_usuario_inicial()


@app.get("/")
def salud():
    return {
        "status": "ok",
        "rostros_conocidos": len(recognizer.nombres_conocidos),
        "tracking_activo": tracking_service.activo,
    }


@app.post("/reconocer/")
async def reconocer(imagen: UploadFile = File(...)):
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo enviado no es una imagen válida")

    contenido = await imagen.read()

    if not contenido:
        raise HTTPException(status_code=400, detail="La imagen recibida está vacía")

    try:
        resultados = recognizer.reconocer(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Error inesperado procesando la imagen")
        raise HTTPException(status_code=500, detail="Error interno procesando la imagen")

    return {
        "rostros_detectados": len(resultados),
        "resultados": resultados,
    }


@app.post("/recargar-conocidos/")
def recargar_conocidos():
    """Vuelve a leer la carpeta `conocidos/` sin reiniciar el servicio."""
    recognizer.cargar_conocidos()
    return {"status": "ok", "rostros_conocidos": len(recognizer.nombres_conocidos)}


@app.get("/tracking/estado")
def tracking_estado():
    camaras = [
        {k: v for k, v in c.items() if k != "password"} for c in _camaras_para_tracking()
    ]
    return {
        "activo": tracking_service.activo,
        "intervalo_segundos": tracking_service.intervalo_segundos,
        "camaras": camaras,
        "errores": tracking_service.ultimo_error,
    }


@app.post("/tracking/iniciar")
def tracking_iniciar():
    tracking_service.iniciar()
    return {"status": "ok", "activo": tracking_service.activo}


@app.post("/tracking/detener")
def tracking_detener():
    tracking_service.detener()
    return {"status": "ok", "activo": tracking_service.activo}


@app.get("/tracking/detecciones-recientes")
def tracking_detecciones_recientes(limite: int = 20):
    return {"detecciones": listar_detecciones_recientes(limite)}


@app.get("/tracking/personas")
def tracking_personas():
    return {"personas": listar_personas()}


@app.get("/tracking/recorrido/{persona}")
def tracking_recorrido(persona: str):
    """
    Devuelve el recorrido de la persona como tramos por zona: entrada, salida y
    duración. El último tramo puede no tener `salida`/`duracion_minutos` todavía
    si la persona sigue actualmente en esa zona.
    """
    sesiones = listar_sesiones(persona)
    if not sesiones:
        raise HTTPException(
            status_code=404, detail=f"No hay sesiones registradas para '{persona}'"
        )
    return {"persona": persona, "recorrido": sesiones}


@app.get("/tracking/sesiones-recientes")
def tracking_sesiones_recientes(limite: int = 20):
    return {"sesiones": listar_sesiones_recientes(limite)}


@app.get("/tracking/log", response_class=PlainTextResponse)
def tracking_log(lineas: int = 200):
    """Devuelve las últimas líneas del log legible de entradas/salidas por zona."""
    if not _log_recorrido_path.exists():
        return "(todavía no hay nada registrado)"
    with open(_log_recorrido_path, encoding="utf-8") as f:
        todas = f.readlines()
    return "".join(todas[-lineas:]) or "(todavía no hay nada registrado)"


# --- Empleados ---------------------------------------------------------------


def _extension_de(nombre_archivo: str | None) -> str:
    if not nombre_archivo or "." not in nombre_archivo:
        return ".jpg"
    return "." + nombre_archivo.rsplit(".", 1)[-1]


@app.get("/empleados/")
def empleados_listar():
    return {"empleados": empleados_mod.listar_perfiles()}


async def _leer_fotos(fotos: list[UploadFile]) -> list[tuple[bytes, str]]:
    resultado = []
    for foto in fotos:
        contenido = await foto.read()
        if not contenido:
            continue
        resultado.append((contenido, _extension_de(foto.filename)))
    return resultado


@app.post("/empleados/")
async def empleados_crear(
    nombre: str = Form(...),
    apellido: str | None = Form(None),
    cargo: str | None = Form(None),
    legajo: str | None = Form(None),
    fotos: list[UploadFile] = File(...),
):
    fotos_leidas = await _leer_fotos(fotos)
    try:
        perfil = empleados_mod.crear_perfil(
            nombre=nombre,
            apellido=apellido,
            cargo=cargo,
            legajo=legajo,
            fotos=fotos_leidas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return perfil


@app.get("/empleados/{empleado_id}/foto")
def empleados_foto(empleado_id: int):
    ruta = empleados_mod.ruta_foto_principal(empleado_id)
    if ruta is None:
        raise HTTPException(status_code=404, detail="Este empleado no tiene foto cargada")
    return FileResponse(ruta)


@app.get("/empleados/{empleado_id}/fotos")
def empleados_listar_fotos(empleado_id: int):
    if obtener_empleado(empleado_id) is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return {"fotos": empleados_mod.listar_fotos(empleado_id)}


@app.get("/empleados/{empleado_id}/fotos/{nombre_archivo}")
def empleados_foto_especifica(empleado_id: int, nombre_archivo: str):
    if nombre_archivo not in empleados_mod.listar_fotos(empleado_id):
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    empleado = obtener_empleado(empleado_id)
    directorio = empleados_mod.dir_fotos(bool(empleado["activo"]))
    return FileResponse(directorio / nombre_archivo)


@app.get("/empleados/{empleado_id}")
def empleados_detalle(empleado_id: int):
    empleado = obtener_empleado(empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    perfiles = {p["id"]: p for p in empleados_mod.listar_perfiles()}
    empleado["cantidad_fotos"] = perfiles.get(empleado_id, {}).get("cantidad_fotos", 0)
    sesiones = listar_sesiones(empleado["clave"])
    empleado["recorrido"] = sesiones
    empleado["tiempo_total_segundos"] = reportes_mod.calcular_tiempo_total_segundos(sesiones)
    return empleado


@app.get("/empleados/{empleado_id}/logs/descargar")
def empleados_descargar_logs(empleado_id: int):
    try:
        nombre_archivo, contenido = reportes_mod.generar_reporte_texto(empleado_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=contenido,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@app.put("/empleados/{empleado_id}")
def empleados_actualizar(
    empleado_id: int,
    nombre: str = Form(...),
    apellido: str | None = Form(None),
    cargo: str | None = Form(None),
    legajo: str | None = Form(None),
):
    try:
        empleados_mod.actualizar_perfil(empleado_id, nombre, apellido, cargo, legajo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.put("/empleados/{empleado_id}/estado")
def empleados_cambiar_estado(empleado_id: int, activo: bool = Form(...)):
    try:
        empleados_mod.cambiar_estado(empleado_id, activo)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/empleados/{empleado_id}/fotos")
async def empleados_agregar_fotos(empleado_id: int, fotos: list[UploadFile] = File(...)):
    fotos_leidas = await _leer_fotos(fotos)
    try:
        empleados_mod.agregar_fotos(empleado_id, fotos_leidas)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.delete("/empleados/{empleado_id}")
def empleados_eliminar(empleado_id: int):
    try:
        empleados_mod.eliminar_perfil(empleado_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


# --- Zonas ---------------------------------------------------------------


@app.get("/zonas/")
def zonas_listar():
    return {"zonas": listar_zonas()}


@app.post("/zonas/")
def zonas_crear(nombre: str = Form(...)):
    nombre = nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la zona no puede estar vacío")
    zona_id = crear_zona(nombre)
    return {"id": zona_id, "nombre": nombre}


@app.delete("/zonas/{zona_id}")
def zonas_eliminar(zona_id: int):
    eliminar_zona(zona_id)
    return {"status": "ok"}


# --- Cámaras ---------------------------------------------------------------


@app.get("/camaras/")
def camaras_listar():
    camaras = camaras_mod.listar_camaras()
    for c in camaras:
        c.pop("password", None)  # no exponer la contraseña al listar
    return {"camaras": camaras}


@app.post("/camaras/probar")
def camaras_probar(
    ip: str = Form(...),
    puerto: int = Form(554),
    usuario: str = Form(...),
    password: str = Form(...),
):
    """Prueba la conexión antes de guardar la cámara (paso previo del asistente)."""
    return camaras_mod.probar_conexion(ip, puerto, usuario, password)


@app.post("/camaras/")
def camaras_crear(
    nombre: str = Form(...),
    ip: str = Form(...),
    puerto: int = Form(554),
    usuario: str = Form(...),
    password: str = Form(...),
    zona_id: int | None = Form(None),
):
    try:
        camara = camaras_mod.crear_camara_nueva(nombre, ip, puerto, usuario, password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if zona_id is not None:
        asignar_zona_camara(camara["id"], zona_id)
    return camara


@app.put("/camaras/{camara_id}/zona")
def camaras_asignar_zona(camara_id: str, zona_id: int | None = Form(None)):
    if obtener_camara(camara_id) is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    asignar_zona_camara(camara_id, zona_id)
    return {"status": "ok"}


@app.put("/camaras/{camara_id}/credenciales")
def camaras_actualizar_credenciales(
    camara_id: str, usuario: str = Form(...), password: str = Form(...)
):
    """Actualiza el usuario/contraseña de una cámara ya vinculada, escribiendo las
    variables correspondientes en el .env (no quedan en ningún otro lado)."""
    try:
        camaras_mod.actualizar_credenciales_camara(camara_id, usuario, password)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.delete("/camaras/{camara_id}")
def camaras_eliminar(camara_id: str):
    try:
        camaras_mod.eliminar_camara_existente(camara_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/camaras/{camara_id}/stream")
def camaras_stream(camara_id: str):
    camara = obtener_camara(camara_id)
    if camara is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    usuario, password = camaras_mod.obtener_credenciales(camara_id)
    return StreamingResponse(
        camaras_mod.generar_mjpeg(camara["ip"], usuario, password, puerto=camara["puerto"]),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# --- Login -------------------------------------------------------------------


def _token_de(authorization: str | None) -> str:
    if not authorization:
        return ""
    return authorization.removeprefix("Bearer ").strip()


@app.post("/auth/login")
def auth_login(usuario: str = Form(...), password: str = Form(...)):
    token = auth_mod.autenticar(usuario, password)
    if token is None:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return {"token": token, "usuario": usuario}


@app.get("/auth/verificar")
def auth_verificar(authorization: str | None = Header(None)):
    usuario = auth_mod.validar_token(_token_de(authorization))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return {"usuario": usuario}


@app.post("/auth/logout")
def auth_logout(authorization: str | None = Header(None)):
    token = _token_de(authorization)
    if token:
        auth_mod.cerrar_sesion(token)
    return {"status": "ok"}
