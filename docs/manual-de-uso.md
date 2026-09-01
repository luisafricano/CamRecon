# Manual de uso

Guía práctica para poner en marcha el sistema y usar el panel de administración.
Para entender cómo funciona por dentro, ver `docs/funcionamiento.md`.

## 1. Puesta en marcha (entorno local)

### Backend

```bash
cd reconocimiento-facial/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crear un archivo `.env` (si no existe) con las credenciales por defecto de las cámaras
y el intervalo de muestreo:

```
CAMERA_USER=admin
CAMERA_PASSWORD=tu_contraseña
TRACKING_INTERVALO_SEGUNDOS=3
```

Levantar el servidor:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd reconocimiento-facial/frontend
python3 -m http.server 5500
```

Abrir `http://localhost:5500/panel.html` en el navegador.

> Si accedés desde otro dispositivo (celular, otra PC), cambiá `API_URL` en
> `frontend/config.js` por la IP de red (o el dominio) del backend. Para usar la cámara
> del celular hace falta que el frontend se sirva por **HTTPS** (los navegadores
> bloquean el acceso a cámara en HTTP salvo en `localhost`).

## 2. El panel (`panel.html`)

Tiene tres secciones, accesibles desde el menú lateral (o el menú ☰ en mobile):

### Empleados

- **"+ Nuevo empleado"**: abre el formulario con nombre, apellido, cargo y legajo
  (opcional), y la sección de fotos:
  - **📷 Tomar foto**: pide permiso de cámara (del dispositivo desde el que estés
    usando el panel — notebook o celular) y permite capturar una o varias fotos.
  - **📁 Cargar foto**: permite elegir una o varias fotos ya guardadas.
  - Se puede combinar: tomar algunas y cargar otras. Cuantas más fotos (distintos
    ángulos, luz), mejor va a reconocer a esa persona.
  - Hace falta al menos una foto para crear el perfil.
- **Buscador**: filtra la tabla en vivo por nombre, apellido, cargo o legajo.
- Click en una fila abre el **detalle** del empleado: foto, datos, tiempo total
  detectado por el sistema, y dos acciones sobre los logs:
  - **"Ver logs"**: despliega la tabla completa de su recorrido (zona, entrada,
    salida, duración de cada tramo).
  - **"Descargar logs"**: descarga un archivo de texto prolijo con el mismo recorrido,
    los tiempos por zona y el tiempo total — pensado para compartir o archivar.
- Desde el detalle también se pueden agregar más fotos de referencia en cualquier
  momento (mismo mecanismo de tomar/cargar).
- Botones por fila:
  - **Editar**: modifica nombre/apellido/cargo/legajo y permite sumar fotos.
  - **Activar / Desactivar**: desactivar saca a la persona del reconocimiento (deja de
    generar detecciones nuevas) sin borrar su historial ni sus datos — útil para bajas
    temporales o definitivas sin perder el registro. Se puede reactivar en cualquier
    momento.
  - **Eliminar**: borra el perfil y sus fotos definitivamente. No se puede deshacer.

### Cámaras en vivo

Una tarjeta por cámara configurada, con botón **"Ver en vivo"** individual. Se
recomienda no activar muchas a la vez si las cámaras son de gama económica, ya que
suelen soportar pocas conexiones simultáneas — si una no carga, probá desactivando otra
primero.

### Configuración de cámaras

Wizard de tres pasos:

1. **Áreas / Zonas**: crear las zonas físicas que se quieren monitorear (ej.
   "Depósito", "Atención al cliente", "Comedor"). Se pueden crear todas las que hagan
   falta y eliminarlas cuando ya no se usen (las cámaras que tenían esa zona quedan
   "Sin asignar", no se borran).
2. **Vincular una cámara nueva**: cargar nombre, IP/dominio, puerto RTSP (por defecto
   `554`), usuario, contraseña y (opcionalmente) la zona. Antes de poder guardar hay
   que tocar **"Probar conexión"** — si falla, revisar IP/puerto/usuario/contraseña y
   que la cámara esté en una red alcanzable desde el servidor.
3. **Cámaras vinculadas**: lista de todas las cámaras cargadas, con un selector para
   cambiar su zona en cualquier momento (sin reiniciar nada) y un botón para
   eliminarlas.

> Una cámara **sin zona asignada** no participa del tracking (no genera sesiones ni
> recorridos), aunque sí se puede ver en vivo.

## 3. Formato de tiempos

Todas las duraciones en el sistema (pantalla, logs, reportes descargables) se muestran
siempre en formato `HH:MM:SS` (por ejemplo `00:12:05` = 12 minutos y 5 segundos). No se
usan minutos con decimales en ningún lado.

## 4. Otras páginas incluidas

- `index.html`: demo simple de captura por webcam contra el endpoint `/reconocer/`
  (útil para probar el reconocimiento de forma aislada, sin tracking).
- `tracking.html`: vista minimalista de solo lectura del recorrido en tiempo real
  (se actualiza sola cada 5 segundos) y el log crudo en texto — alternativa liviana
  al panel completo.

## 5. Problemas comunes

| Síntoma | Causa probable / solución |
|---|---|
| El navegador no deja usar la cámara | Necesita HTTPS (salvo en `localhost`). Ver sección de despliegue con túnel/certificado en el proyecto. |
| Siempre da "Desconocido" aunque la persona esté cargada | Agregar más fotos de referencia, en especial en las mismas condiciones de luz/cámara donde se lo quiere reconocer (ej. una foto nocturna IR si la cámara filma de noche). |
| Una cámara nunca aparece con detecciones | Revisar que tenga una **zona asignada** en Configuración → Cámaras vinculadas, y que "Probar conexión" dé éxito. |
| El botón "Ver en vivo" no carga imagen | La cámara puede estar rechazando otra conexión RTSP simultánea (además de la del tracking). Desactivar otras vistas en vivo y reintentar. |
| Faltan tramos de recorrido o quedan "en curso" para siempre | El sistema solo cierra un tramo cuando detecta a la persona en **otra** cámara. Si sale de todas las cámaras sin pasar por otra, ese último tramo queda abierto hasta la próxima detección. |
