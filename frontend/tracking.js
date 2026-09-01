const tablaSesiones = document.getElementById("tabla-sesiones");
const logCrudo = document.getElementById("log-crudo");
const estadoTracking = document.getElementById("estado-tracking");

function formatearFecha(iso) {
  if (!iso) return "-";
  const fecha = new Date(iso);
  return fecha.toLocaleString("es-AR", { hour12: false });
}

function formatearDuracion(segundos) {
  if (segundos === null || segundos === undefined) return "-";
  segundos = Math.round(segundos);
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  const dos = (n) => String(n).padStart(2, "0");
  return `${dos(h)}:${dos(m)}:${dos(s)}`;
}

function renderEstado(activo) {
  estadoTracking.textContent = activo ? "Tracking activo" : "Tracking detenido";
  estadoTracking.className =
    "rounded-full px-3 py-1 text-xs font-bold " +
    (activo ? "bg-emerald-600" : "bg-red-600");
}

function renderSesiones(sesiones) {
  tablaSesiones.innerHTML = sesiones
    .map((s) => {
      const abierta = s.salida === null;
      return `
        <tr class="${abierta ? "bg-indigo-950/40" : ""}">
          <td class="px-4 py-2 font-medium">${s.persona}</td>
          <td class="px-4 py-2">${s.zona}</td>
          <td class="px-4 py-2 text-slate-300">${formatearFecha(s.entrada)}</td>
          <td class="px-4 py-2 text-slate-300">${abierta ? "en curso..." : formatearFecha(s.salida)}</td>
          <td class="px-4 py-2 font-mono">${abierta ? "en curso..." : formatearDuracion(s.duracion_segundos)}</td>
        </tr>
      `;
    })
    .join("");
}

async function actualizar() {
  try {
    const [estado, sesiones, log] = await Promise.all([
      fetch(`${API_URL}/tracking/estado`).then((r) => r.json()),
      fetch(`${API_URL}/tracking/sesiones-recientes?limite=30`).then((r) => r.json()),
      fetch(`${API_URL}/tracking/log`).then((r) => r.text()),
    ]);

    renderEstado(estado.activo);
    renderSesiones(sesiones.sesiones);
    logCrudo.textContent = log;
    logCrudo.scrollTop = logCrudo.scrollHeight;
  } catch (error) {
    console.error(error);
    estadoTracking.textContent = "Error de conexión";
    estadoTracking.className = "rounded-full px-3 py-1 text-xs font-bold bg-red-600";
  }
}

actualizar();
setInterval(actualizar, 5000);
