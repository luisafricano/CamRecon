# Carpeta `conocidos/`

Acá van las fotos de referencia de las personas que el sistema debe reconocer.

## Reglas

- Una foto por persona (o varias, si querés mejorar la precisión).
- El **nombre del archivo** (sin extensión) es el nombre que se mostrará como resultado.
  - Ejemplo: `juan.jpg` → se reconoce como `juan`.
- Si querés varias fotos de la misma persona, usá un sufijo `_` seguido de cualquier texto:
  - Ejemplo: `juan.jpg`, `juan_perfil.jpg`, `juan_2.jpg` → todas se reconocen como `juan`.
- Formatos soportados: `.jpg`, `.jpeg`, `.png`.
- Cada foto debe mostrar **un solo rostro** claramente visible.

## Recarga

El servicio carga estas imágenes al iniciar. Si agregás o quitás fotos sin reiniciar
el backend, podés forzar la recarga llamando a:

```
POST /recargar-conocidos/
```
