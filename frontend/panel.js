// ---------------------------------------------------------------------------
// Formato de duraciones (siempre HH:MM:SS, nunca minutos con decimales)
// ---------------------------------------------------------------------------

function formatearDuracion(segundos) {
  if (segundos === null || segundos === undefined) return "-";
  segundos = Math.round(segundos);
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  const dos = (n) => String(n).padStart(2, "0");
  return `${dos(h)}:${dos(m)}:${dos(s)}`;
}

// ---------------------------------------------------------------------------
// Navegación entre secciones
// ---------------------------------------------------------------------------

const SECCIONES = [
  { id: "empleados", etiqueta: "Empleados", target: "seccion-empleados" },
  { id: "camaras-vivo", etiqueta: "Cámaras en vivo", target: "seccion-camaras-vivo" },
  { id: "configuracion", etiqueta: "Configuración de cámaras", target: "seccion-configuracion" },
];

let seccionActual = "empleados";

function construirNav(contenedor) {
  contenedor.innerHTML = "";
  SECCIONES.forEach((s) => {
    const boton = document.createElement("button");
    boton.textContent = s.etiqueta;
    boton.dataset.seccion = s.id;
    boton.className = claseBotonNav(s.id === seccionActual);
    boton.addEventListener("click", () => irASeccion(s.id));
    contenedor.appendChild(boton);
  });
}

function claseBotonNav(activo) {
  return (
    "rounded-lg px-3 py-2 text-left text-sm font-medium transition " +
    (activo ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800")
  );
}

function irASeccion(id) {
  seccionActual = id;
  SECCIONES.forEach((s) => {
    document.getElementById(s.target).hidden = s.id !== id;
  });
  construirNav(document.getElementById("nav-desktop"));
  construirNav(document.getElementById("nav-mobile"));
  cerrarMenuMobile();

  if (id === "camaras-vivo") cargarCamarasEnVivo();
  if (id === "configuracion") cargarConfiguracion();
  if (id === "empleados") cargarEmpleados();
}

function cerrarMenuMobile() {
  document.getElementById("mobile-nav-overlay").hidden = true;
}

document.getElementById("btn-menu").addEventListener("click", () => {
  document.getElementById("mobile-nav-overlay").hidden = false;
});
document.getElementById("btn-cerrar-menu").addEventListener("click", cerrarMenuMobile);
document.getElementById("mobile-nav-backdrop").addEventListener("click", cerrarMenuMobile);
document.getElementById("btn-cerrar-sesion").addEventListener("click", cerrarSesion);
document.getElementById("btn-cerrar-sesion-mobile").addEventListener("click", cerrarSesion);

document.querySelectorAll("[data-cerrar-modal]").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.dataset.cerrarModal === "modal-form-empleado") cerrarCamaraCaptura();
    document.getElementById(btn.dataset.cerrarModal).hidden = true;
  });
});

// ---------------------------------------------------------------------------
// Empleados
// ---------------------------------------------------------------------------

let empleadosCache = [];

async function cargarEmpleados() {
  const res = await fetch(`${API_URL}/empleados/`);
  const data = await res.json();
  empleadosCache = data.empleados || [];
  renderEmpleados(empleadosCache);
}

function renderEmpleados(lista) {
  const tabla = document.getElementById("tabla-empleados");
  const vacio = document.getElementById("empleados-vacio");

  if (lista.length === 0) {
    tabla.innerHTML = "";
    vacio.hidden = false;
    return;
  }
  vacio.hidden = true;

  tabla.innerHTML = lista
    .map(
      (e) => `
      <tr class="cursor-pointer hover:bg-slate-900/60 ${e.activo ? "" : "opacity-50"}" data-id="${e.id}">
        <td class="px-4 py-2">
          <img src="${API_URL}/empleados/${e.id}/foto" onerror="this.style.visibility='hidden'"
            class="h-8 w-8 rounded-full object-cover bg-slate-800" />
        </td>
        <td class="px-4 py-2 font-medium">${e.nombre}</td>
        <td class="px-4 py-2 text-slate-400">${e.apellido || "-"}</td>
        <td class="px-4 py-2 text-slate-400">${e.cargo || "-"}</td>
        <td class="px-4 py-2 text-slate-400">${e.cantidad_fotos}</td>
        <td class="px-4 py-2">
          <span class="rounded-full px-2 py-0.5 text-xs ${e.activo ? "bg-emerald-900 text-emerald-300" : "bg-slate-800 text-slate-400"}">
            ${e.activo ? "Activo" : "Inactivo"}
          </span>
        </td>
        <td class="px-4 py-2 text-right whitespace-nowrap">
          <button data-editar="${e.id}" class="text-xs text-indigo-400 hover:text-indigo-300">Editar</button>
          <button data-toggle-estado="${e.id}" data-activo="${e.activo}" class="ml-2 text-xs text-amber-400 hover:text-amber-300">
            ${e.activo ? "Desactivar" : "Activar"}
          </button>
          <button data-eliminar="${e.id}" class="ml-2 text-xs text-red-400 hover:text-red-300">Eliminar</button>
        </td>
      </tr>
    `
    )
    .join("");

  tabla.querySelectorAll("tr[data-id]").forEach((fila) => {
    fila.addEventListener("click", (ev) => {
      if (ev.target.closest("button")) return;
      abrirDetalleEmpleado(Number(fila.dataset.id));
    });
  });

  tabla.querySelectorAll("[data-editar]").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      abrirModalEmpleado(Number(btn.dataset.editar));
    });
  });

  tabla.querySelectorAll("[data-toggle-estado]").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const activo = btn.dataset.activo === "true";
      const formData = new FormData();
      formData.append("activo", activo ? "false" : "true");
      await fetch(`${API_URL}/empleados/${btn.dataset.toggleEstado}/estado`, {
        method: "PUT",
        body: formData,
      });
      cargarEmpleados();
    });
  });

  tabla.querySelectorAll("[data-eliminar]").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!confirm("¿Eliminar este perfil y sus fotos de referencia? Esta acción no se puede deshacer.")) return;
      await fetch(`${API_URL}/empleados/${btn.dataset.eliminar}`, { method: "DELETE" });
      cargarEmpleados();
    });
  });
}

document.getElementById("buscador-empleados").addEventListener("input", (ev) => {
  const q = ev.target.value.trim().toLowerCase();
  const filtrados = empleadosCache.filter((e) =>
    [e.nombre, e.apellido, e.cargo, e.legajo]
      .filter(Boolean)
      .some((campo) => campo.toLowerCase().includes(q))
  );
  renderEmpleados(filtrados);
});

// --- Modal crear/editar empleado (con captura de cámara + carga de archivos) --------

let empleadoEditandoId = null;
let fotosNuevas = []; // { blob, previewUrl }
let streamCamaraCaptura = null;

document.getElementById("btn-nuevo-empleado").addEventListener("click", () => abrirModalEmpleado(null));

async function abrirModalEmpleado(id) {
  empleadoEditandoId = id;
  fotosNuevas = [];
  document.getElementById("form-empleado").reset();
  document.getElementById("error-form-empleado").classList.add("hidden");
  cerrarCamaraCaptura();
  renderMiniaturas();

  const titulo = document.getElementById("form-empleado-titulo");
  const btnGuardar = document.getElementById("btn-guardar-empleado");

  if (id === null) {
    titulo.textContent = "Nuevo empleado";
    btnGuardar.textContent = "Crear perfil";
  } else {
    titulo.textContent = "Editar empleado";
    btnGuardar.textContent = "Guardar cambios";
    const res = await fetch(`${API_URL}/empleados/${id}`);
    const e = await res.json();
    document.getElementById("empleado-nombre").value = e.nombre || "";
    document.getElementById("empleado-apellido").value = e.apellido || "";
    document.getElementById("empleado-cargo").value = e.cargo || "";
    document.getElementById("empleado-legajo").value = e.legajo || "";
  }

  document.getElementById("modal-form-empleado").hidden = false;
}

function renderMiniaturas() {
  const contenedor = document.getElementById("miniaturas-fotos");
  if (fotosNuevas.length === 0) {
    contenedor.innerHTML = `<span class="text-xs text-slate-500">Todavía no agregaste ninguna foto nueva.</span>`;
    return;
  }
  contenedor.innerHTML = fotosNuevas
    .map(
      (f, i) => `
      <div class="relative">
        <img src="${f.previewUrl}" class="h-16 w-16 rounded-lg object-cover" />
        <button type="button" data-quitar-foto="${i}"
          class="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs hover:bg-red-500">
          ✕
        </button>
      </div>
    `
    )
    .join("");

  contenedor.querySelectorAll("[data-quitar-foto]").forEach((btn) => {
    btn.addEventListener("click", () => {
      fotosNuevas.splice(Number(btn.dataset.quitarFoto), 1);
      renderMiniaturas();
    });
  });
}

function agregarFotoNueva(blob) {
  fotosNuevas.push({ blob, previewUrl: URL.createObjectURL(blob) });
  renderMiniaturas();
}

// -- Tomar foto (cámara del dispositivo) --

document.getElementById("btn-tomar-foto").addEventListener("click", async () => {
  const contenedor = document.getElementById("camara-captura-contenedor");
  const video = document.getElementById("camara-captura-video");
  const errorEl = document.getElementById("error-camara-captura");
  errorEl.classList.add("hidden");

  try {
    streamCamaraCaptura = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    });
    video.srcObject = streamCamaraCaptura;
    await new Promise((resolve) => (video.onloadedmetadata = resolve));
    await video.play();
    contenedor.hidden = false;
  } catch (error) {
    errorEl.textContent = "No se pudo acceder a la cámara: " + error.message;
    errorEl.classList.remove("hidden");
    contenedor.hidden = false;
  }
});

document.getElementById("btn-capturar-foto").addEventListener("click", () => {
  const video = document.getElementById("camara-captura-video");
  if (!video.videoWidth) return;

  const canvas = document.getElementById("canvas-captura");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob((blob) => {
    if (blob) agregarFotoNueva(blob);
  }, "image/jpeg", 0.9);
});

document.getElementById("btn-cerrar-camara").addEventListener("click", cerrarCamaraCaptura);

function cerrarCamaraCaptura() {
  if (streamCamaraCaptura) {
    streamCamaraCaptura.getTracks().forEach((t) => t.stop());
    streamCamaraCaptura = null;
  }
  document.getElementById("camara-captura-contenedor").hidden = true;
}

// -- Cargar foto (archivos del dispositivo) --

document.getElementById("btn-cargar-foto").addEventListener("click", () => {
  document.getElementById("input-cargar-foto").click();
});

document.getElementById("input-cargar-foto").addEventListener("change", (ev) => {
  Array.from(ev.target.files).forEach((file) => agregarFotoNueva(file));
  ev.target.value = "";
});

// -- Guardar (crear o editar) --

document.getElementById("form-empleado").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const errorEl = document.getElementById("error-form-empleado");
  errorEl.classList.add("hidden");

  if (empleadoEditandoId === null && fotosNuevas.length === 0) {
    errorEl.textContent = "Agregá al menos una foto de referencia (tomada o cargada).";
    errorEl.classList.remove("hidden");
    return;
  }

  const datos = new FormData();
  datos.append("nombre", document.getElementById("empleado-nombre").value);
  datos.append("apellido", document.getElementById("empleado-apellido").value);
  datos.append("cargo", document.getElementById("empleado-cargo").value);
  datos.append("legajo", document.getElementById("empleado-legajo").value);

  let res;
  if (empleadoEditandoId === null) {
    fotosNuevas.forEach((f, i) => datos.append("fotos", f.blob, `foto_${i}.jpg`));
    res = await fetch(`${API_URL}/empleados/`, { method: "POST", body: datos });
  } else {
    res = await fetch(`${API_URL}/empleados/${empleadoEditandoId}`, { method: "PUT", body: datos });
  }

  if (!res.ok) {
    const detalle = await res.json().catch(() => ({}));
    errorEl.textContent = detalle.detail || "No se pudo guardar el perfil.";
    errorEl.classList.remove("hidden");
    return;
  }

  if (empleadoEditandoId !== null && fotosNuevas.length > 0) {
    const datosFotos = new FormData();
    fotosNuevas.forEach((f, i) => datosFotos.append("fotos", f.blob, `foto_${i}.jpg`));
    await fetch(`${API_URL}/empleados/${empleadoEditandoId}/fotos`, { method: "POST", body: datosFotos });
  }

  cerrarCamaraCaptura();
  document.getElementById("modal-form-empleado").hidden = true;
  cargarEmpleados();
});

async function abrirDetalleEmpleado(id) {
  const res = await fetch(`${API_URL}/empleados/${id}`);
  if (!res.ok) return;
  const e = await res.json();

  document.getElementById("detalle-empleado-nombre").textContent =
    [e.nombre, e.apellido].filter(Boolean).join(" ");

  const filasRecorrido = (e.recorrido || [])
    .slice()
    .reverse()
    .map(
      (s) => `
      <tr>
        <td class="px-3 py-1.5">${s.zona}</td>
        <td class="px-3 py-1.5 text-slate-400">${new Date(s.entrada).toLocaleString("es-AR")}</td>
        <td class="px-3 py-1.5 text-slate-400">${s.salida ? new Date(s.salida).toLocaleString("es-AR") : "en curso..."}</td>
        <td class="px-3 py-1.5 font-mono">${s.salida ? formatearDuracion(s.duracion_segundos) : "en curso..."}</td>
      </tr>
    `
    )
    .join("");

  document.getElementById("detalle-empleado-contenido").innerHTML = `
    <div class="flex items-center gap-4">
      <img src="${API_URL}/empleados/${id}/foto" onerror="this.style.visibility='hidden'"
        class="h-20 w-20 rounded-lg object-cover bg-slate-800" />
      <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-300">
        <p><span class="text-slate-500">Nombre:</span> ${e.nombre}</p>
        <p><span class="text-slate-500">Apellido:</span> ${e.apellido || "-"}</p>
        <p><span class="text-slate-500">Cargo:</span> ${e.cargo || "-"}</p>
        <p><span class="text-slate-500">Legajo:</span> ${e.legajo || "-"}</p>
      </div>
    </div>

    <div class="rounded-lg border border-slate-800 bg-slate-950 px-4 py-3">
      <span class="text-slate-500">Tiempo total detectado por el sistema:</span>
      <span class="ml-2 font-mono text-base font-semibold text-emerald-400">${formatearDuracion(e.tiempo_total_segundos)}</span>
    </div>

    <div>
      <h4 class="mb-2 font-semibold">Agregar otra foto de referencia</h4>
      <input id="input-foto-extra" type="file" accept="image/*" multiple
        class="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white file:mr-3 file:rounded-md file:border-0 file:bg-slate-700 file:px-3 file:py-1 file:text-white" />
    </div>

    <div>
      <div class="flex flex-wrap gap-2">
        <button id="btn-ver-logs" class="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold hover:bg-slate-600">
          Ver logs
        </button>
        <a href="${API_URL}/empleados/${id}/logs/descargar" download
          class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500">
          Descargar logs
        </a>
      </div>
      <div id="contenedor-logs" hidden class="mt-3">
        ${
          filasRecorrido
            ? `<div class="overflow-hidden rounded-lg border border-slate-800">
                <table class="w-full text-left text-xs">
                  <thead class="bg-slate-950 text-slate-500">
                    <tr><th class="px-3 py-1.5">Zona</th><th class="px-3 py-1.5">Entrada</th><th class="px-3 py-1.5">Salida</th><th class="px-3 py-1.5">Duración</th></tr>
                  </thead>
                  <tbody class="divide-y divide-slate-800">${filasRecorrido}</tbody>
                </table>
              </div>`
            : `<p class="text-slate-500">Todavía no hay detecciones registradas para esta persona.</p>`
        }
      </div>
    </div>
  `;

  document.getElementById("btn-ver-logs").addEventListener("click", () => {
    const contenedor = document.getElementById("contenedor-logs");
    contenedor.hidden = !contenedor.hidden;
  });

  document.getElementById("input-foto-extra").addEventListener("change", async (ev) => {
    if (ev.target.files.length === 0) return;
    const formData = new FormData();
    Array.from(ev.target.files).forEach((archivo) => formData.append("fotos", archivo));
    await fetch(`${API_URL}/empleados/${id}/fotos`, { method: "POST", body: formData });
    cargarEmpleados();
    abrirDetalleEmpleado(id);
  });

  document.getElementById("modal-detalle-empleado").hidden = false;
}

// ---------------------------------------------------------------------------
// Cámaras en vivo
// ---------------------------------------------------------------------------

async function cargarCamarasEnVivo() {
  const res = await fetch(`${API_URL}/camaras/`);
  const data = await res.json();
  const camaras = data.camaras || [];
  const grid = document.getElementById("grid-camaras-vivo");
  const vacio = document.getElementById("camaras-vivo-vacio");

  if (camaras.length === 0) {
    grid.innerHTML = "";
    vacio.hidden = false;
    return;
  }
  vacio.hidden = true;

  grid.innerHTML = camaras
    .map(
      (c) => `
      <div class="overflow-hidden rounded-xl border border-slate-800 bg-black">
        <div class="flex aspect-video items-center justify-center bg-slate-900" data-contenedor="${c.id}">
          <button data-activar="${c.id}" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500">
            Ver en vivo
          </button>
        </div>
        <div class="flex items-center justify-between px-3 py-2 text-xs">
          <span class="font-medium">${c.nombre}</span>
          <span class="text-slate-500">${c.zona_nombre || "Sin zona"}</span>
        </div>
      </div>
    `
    )
    .join("");

  grid.querySelectorAll("[data-activar]").forEach((btn) => {
    btn.addEventListener("click", () => activarStream(btn.dataset.activar));
  });
}

function activarStream(camaraId) {
  const contenedor = document.querySelector(`[data-contenedor="${camaraId}"]`);
  contenedor.innerHTML = `
    <img src="${API_URL}/camaras/${camaraId}/stream" class="h-full w-full object-cover" />
  `;
  const boton = document.createElement("button");
  boton.textContent = "Detener";
  boton.className =
    "absolute m-2 rounded-lg bg-black/60 px-3 py-1 text-xs font-semibold hover:bg-black/80";
  contenedor.classList.add("relative");
  contenedor.appendChild(boton);
  boton.addEventListener("click", () => desactivarStream(camaraId));
}

function desactivarStream(camaraId) {
  const contenedor = document.querySelector(`[data-contenedor="${camaraId}"]`);
  contenedor.innerHTML = `
    <button data-activar="${camaraId}" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500">
      Ver en vivo
    </button>
  `;
  contenedor.querySelector("[data-activar]").addEventListener("click", () => activarStream(camaraId));
}

// ---------------------------------------------------------------------------
// Configuración: zonas y cámaras
// ---------------------------------------------------------------------------

async function cargarConfiguracion() {
  await Promise.all([cargarZonas(), cargarCamarasConfig()]);
}

async function cargarZonas() {
  const res = await fetch(`${API_URL}/zonas/`);
  const data = await res.json();
  const zonas = data.zonas || [];

  const lista = document.getElementById("lista-zonas");
  lista.innerHTML = zonas.length
    ? zonas
        .map(
          (z) => `
        <span class="flex items-center gap-2 rounded-full bg-slate-800 px-3 py-1 text-xs">
          ${z.nombre}
          <button data-eliminar-zona="${z.id}" class="text-slate-500 hover:text-red-400">✕</button>
        </span>
      `
        )
        .join("")
    : `<span class="text-xs text-slate-500">Todavía no creaste ninguna área.</span>`;

  lista.querySelectorAll("[data-eliminar-zona]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar esta área? Las cámaras vinculadas quedarán sin zona.")) return;
      await fetch(`${API_URL}/zonas/${btn.dataset.eliminarZona}`, { method: "DELETE" });
      cargarConfiguracion();
    });
  });

  const select = document.getElementById("cam-zona");
  const valorPrevio = select.value;
  select.innerHTML =
    `<option value="">Sin asignar (no se rastrea todavía)</option>` +
    zonas.map((z) => `<option value="${z.id}">${z.nombre}</option>`).join("");
  select.value = valorPrevio;
}

document.getElementById("form-zona").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const input = document.getElementById("input-zona-nombre");
  const formData = new FormData();
  formData.append("nombre", input.value);
  await fetch(`${API_URL}/zonas/`, { method: "POST", body: formData });
  input.value = "";
  cargarConfiguracion();
});

let ultimaPruebaCamaraOk = false;

document.getElementById("btn-probar-camara").addEventListener("click", async () => {
  const resultadoEl = document.getElementById("resultado-prueba-camara");
  const btnGuardar = document.getElementById("btn-guardar-camara");
  resultadoEl.textContent = "Probando conexión...";
  resultadoEl.className = "text-sm text-slate-400";
  btnGuardar.disabled = true;
  ultimaPruebaCamaraOk = false;

  const formData = new FormData();
  formData.append("ip", document.getElementById("cam-ip").value);
  formData.append("puerto", document.getElementById("cam-puerto").value);
  formData.append("usuario", document.getElementById("cam-usuario").value);
  formData.append("password", document.getElementById("cam-password").value);

  try {
    const res = await fetch(`${API_URL}/camaras/probar`, { method: "POST", body: formData });
    const data = await res.json();
    resultadoEl.textContent = data.detalle;
    resultadoEl.className = "text-sm " + (data.ok ? "text-emerald-400" : "text-red-400");
    ultimaPruebaCamaraOk = data.ok;
    btnGuardar.disabled = !data.ok;
  } catch (error) {
    resultadoEl.textContent = "Error de conexión con el backend.";
    resultadoEl.className = "text-sm text-red-400";
  }
});

document.getElementById("form-camara").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (!ultimaPruebaCamaraOk) return;

  const formData = new FormData();
  formData.append("nombre", document.getElementById("cam-nombre").value);
  formData.append("ip", document.getElementById("cam-ip").value);
  formData.append("puerto", document.getElementById("cam-puerto").value);
  formData.append("usuario", document.getElementById("cam-usuario").value);
  formData.append("password", document.getElementById("cam-password").value);
  const zonaId = document.getElementById("cam-zona").value;
  if (zonaId) formData.append("zona_id", zonaId);

  await fetch(`${API_URL}/camaras/`, { method: "POST", body: formData });

  ev.target.reset();
  document.getElementById("cam-puerto").value = "554";
  document.getElementById("resultado-prueba-camara").textContent = "";
  document.getElementById("btn-guardar-camara").disabled = true;
  ultimaPruebaCamaraOk = false;

  cargarConfiguracion();
});

async function cargarCamarasConfig() {
  const [resCamaras, resZonas] = await Promise.all([
    fetch(`${API_URL}/camaras/`),
    fetch(`${API_URL}/zonas/`),
  ]);
  const camaras = (await resCamaras.json()).camaras || [];
  const zonas = (await resZonas.json()).zonas || [];

  const contenedor = document.getElementById("lista-camaras-config");
  const vacio = document.getElementById("camaras-config-vacio");

  if (camaras.length === 0) {
    contenedor.innerHTML = "";
    vacio.hidden = false;
    return;
  }
  vacio.hidden = true;

  contenedor.innerHTML = camaras
    .map(
      (c) => `
      <div class="rounded-lg border border-slate-800 bg-slate-950 px-4 py-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p class="font-medium">${c.nombre}</p>
            <p class="text-xs text-slate-500">${c.ip}:${c.puerto} · usuario: ${c.usuario}</p>
          </div>
          <div class="flex items-center gap-2">
            <select data-zona-camara="${c.id}" class="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-white">
              <option value="">Sin asignar</option>
              ${zonas
                .map(
                  (z) =>
                    `<option value="${z.id}" ${z.id === c.zona_id ? "selected" : ""}>${z.nombre}</option>`
                )
                .join("")}
            </select>
            <button data-editar-credenciales="${c.id}" class="text-xs text-indigo-400 hover:text-indigo-300">
              Editar credenciales
            </button>
            <button data-eliminar-camara="${c.id}" class="text-xs text-red-400 hover:text-red-300">Eliminar</button>
          </div>
        </div>

        <form data-form-credenciales="${c.id}" hidden class="mt-3 flex flex-wrap items-end gap-2 border-t border-slate-800 pt-3">
          <label class="flex flex-col gap-1 text-xs text-slate-400">
            Usuario
            <input name="usuario" type="text" value="${c.usuario}" required
              class="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-white focus:border-indigo-500 focus:outline-none" />
          </label>
          <label class="flex flex-col gap-1 text-xs text-slate-400">
            Contraseña nueva
            <input name="password" type="password" required placeholder="••••••••"
              class="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-white focus:border-indigo-500 focus:outline-none" />
          </label>
          <button type="submit" class="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold hover:bg-indigo-500">
            Guardar en .env
          </button>
          <span data-resultado-credenciales="${c.id}" class="text-xs"></span>
        </form>
      </div>
    `
    )
    .join("");

  contenedor.querySelectorAll("[data-zona-camara]").forEach((select) => {
    select.addEventListener("change", async () => {
      const formData = new FormData();
      if (select.value) formData.append("zona_id", select.value);
      await fetch(`${API_URL}/camaras/${select.dataset.zonaCamara}/zona`, {
        method: "PUT",
        body: formData,
      });
    });
  });

  contenedor.querySelectorAll("[data-editar-credenciales]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = contenedor.querySelector(`[data-form-credenciales="${btn.dataset.editarCredenciales}"]`);
      form.hidden = !form.hidden;
    });
  });

  contenedor.querySelectorAll("[data-form-credenciales]").forEach((form) => {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const camaraId = form.dataset.formCredenciales;
      const resultadoEl = contenedor.querySelector(`[data-resultado-credenciales="${camaraId}"]`);
      const formData = new FormData(form);

      const res = await fetch(`${API_URL}/camaras/${camaraId}/credenciales`, {
        method: "PUT",
        body: formData,
      });

      if (res.ok) {
        resultadoEl.textContent = "Guardado ✓";
        resultadoEl.className = "text-xs text-emerald-400";
        setTimeout(() => cargarConfiguracion(), 800);
      } else {
        resultadoEl.textContent = "No se pudo guardar.";
        resultadoEl.className = "text-xs text-red-400";
      }
    });
  });

  contenedor.querySelectorAll("[data-eliminar-camara]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar esta cámara del sistema?")) return;
      await fetch(`${API_URL}/camaras/${btn.dataset.eliminarCamara}`, { method: "DELETE" });
      cargarConfiguracion();
    });
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

construirNav(document.getElementById("nav-desktop"));
construirNav(document.getElementById("nav-mobile"));
cargarEmpleados();
