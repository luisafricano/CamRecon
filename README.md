# CamRecon

**CamRecon** es un sistema de reconocimiento facial que se conecta a cámaras IP (RTSP)
para identificar personas y trazar automáticamente su recorrido: en qué zona estuvo,
a qué hora entró y salió, y cuánto tiempo permaneció en cada una.

Incluye un panel de administración con gestión de empleados (con reconocimiento
multi-foto), vinculación de cámaras a áreas configurables, vista en vivo, reportes de
recorrido descargables, y un login simple para el acceso.

## Funcionalidades

- 🎥 Conexión a cámaras IP/DVR/NVR vía RTSP, con vista en vivo desde el navegador.
- 🧠 Reconocimiento facial (FastAPI + `face_recognition`/`dlib`) con soporte multi-foto por perfil.
- 👤 Gestión de empleados: alta, edición, baja/reactivación, carga de fotos por cámara o archivo.
- 🗺️ Zonas configurables y asignación de cámaras a cada área desde un asistente guiado, con prueba de conexión.
- ⏱️ Tracking automático de sesiones por zona, con entrada, salida y duración en formato `HH:MM:SS`.
- 📄 Reportes descargables por empleado con el recorrido completo y el tiempo total detectado.
- 🔐 Login simple para el acceso al panel.
- 🌙 Interfaz oscura, responsive, sin frameworks de frontend (HTML + JS vainilla + Tailwind CDN).

## Stack

| Capa | Tecnologías |
|---|---|
| Backend | Python, FastAPI, OpenCV, `face_recognition` (dlib), SQLite |
| Frontend | HTML, JavaScript vainilla, Tailwind CSS (CDN) |
| Despliegue | Docker / Docker Compose |

## Estructura del proyecto

```
reconocimiento-facial/
├── backend/
│   ├── main.py              # Endpoints de la API (FastAPI)
│   ├── recognition.py       # Reconocimiento facial (face_recognition)
│   ├── auth.py               # Login (usuario/contraseña + tokens)
│   ├── empleados.py          # Alta/edición/baja de empleados
│   ├── camaras.py            # Alta/baja de cámaras, stream en vivo
│   ├── reportes.py           # Reporte descargable de recorrido
│   ├── formato.py            # Formato de fechas/duraciones (HH:MM:SS)
│   ├── tracking/              # Muestreo de cámaras, sesiones y base de datos
│   ├── conocidos/             # Fotos de referencia para el reconocimiento
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── login.html             # Login
│   ├── panel.html             # Panel de administración
│   ├── tracking.html          # Vista liviana de recorrido en vivo
│   ├── index.html             # Demo simple de captura por webcam
│   └── config.js              # URL del backend (editar según entorno)
└── docs/
    ├── funcionamiento.md / .html / .pdf   # Arquitectura y flujo completo
    └── manual-de-uso.md / .html / .pdf    # Manual de uso del panel
```

## Puesta en marcha (entorno local)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copiar `.env.example` a `.env` y completar los valores:

```bash
cp .env.example .env
```

```
CAMERA_USER=admin
CAMERA_PASSWORD=tu_contraseña
TRACKING_INTERVALO_SEGUNDOS=3
ADMIN_USUARIO_INICIAL=reconadmin
ADMIN_PASSWORD_INICIAL=tu_contraseña
```

> El `.env` es el único lugar donde vive información sensible (contraseñas de cámaras,
> credencial inicial del panel). **Nunca se sube al repositorio** (está en
> `.gitignore`). Cada cámara que se vincula desde el panel agrega/actualiza sus propias
> variables ahí solo (`CAM_<ID>_USER` / `CAM_<ID>_PASSWORD>`), sin que haga falta
> tocar el archivo a mano.

Levantar el servidor:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd frontend
python3 -m http.server 5500
```

Abrir `http://localhost:5500/login.html`.

> Si accedés desde otro dispositivo, actualizá `API_URL` en `frontend/config.js` con la
> IP/dominio real del backend. Para usar la cámara del celular hace falta HTTPS (los
> navegadores bloquean el acceso a cámara en HTTP salvo en `localhost`).

## Acceso al sistema

El panel requiere iniciar sesión. Usuario de fábrica (se crea automáticamente la primera
vez que arranca el backend, con los valores de `ADMIN_USUARIO_INICIAL` /
`ADMIN_PASSWORD_INICIAL` del `.env`):

```
Usuario:     reconadmin
Contraseña:  recon123
```

> ⚠️ Este login está pensado para demostraciones/uso controlado. Antes de usarlo con
> datos reales de una empresa, cambiar la contraseña por defecto y revisar los alcances
> de seguridad (ver `docs/funcionamiento.md`).

## Despliegue

El backend está listo para desplegarse en un VPS con Docker:

```bash
cd backend
docker compose up -d --build
```

El frontend son archivos estáticos: se pueden servir desde el mismo VPS o cualquier
hosting estático, apuntando `config.js` al dominio del backend.

## Documentación

- [`docs/funcionamiento.md`](docs/funcionamiento.md) — arquitectura y flujo completo del sistema.
- [`docs/manual-de-uso.md`](docs/manual-de-uso.md) — guía de uso del panel, paso a paso.

(Ambos documentos también están disponibles en `.html` y `.pdf` dentro de la misma carpeta.)

---
Copyright © 2026 - Designed & Developed by Ing. Luis Africano
