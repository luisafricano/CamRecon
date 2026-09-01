const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const btnActivarCamara = document.getElementById("btn-activar-camara");
const btnCapturar = document.getElementById("btn-capturar");
const resultadoEl = document.getElementById("resultado");
const estadoEl = document.getElementById("estado");

async function activarCamara() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setEstado(
      "Este navegador no soporta acceso a la cámara, o la página no se está sirviendo por HTTPS.",
      "error"
    );
    return;
  }

  btnActivarCamara.disabled = true;
  setEstado("Pidiendo permiso de cámara...", "info");

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    });
    video.srcObject = stream;

    await new Promise((resolve) => {
      video.onloadedmetadata = resolve;
    });
    await video.play();

    setEstado("Cámara lista.", "ok");
    btnActivarCamara.classList.add("hidden");
    btnCapturar.classList.remove("hidden");
  } catch (error) {
    console.error(error);
    btnActivarCamara.disabled = false;

    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      setEstado(
        "Permiso de cámara denegado. Revisá el ícono de candado/cámara en la barra del navegador y habilitalo manualmente para este sitio.",
        "error"
      );
    } else if (error.name === "NotFoundError") {
      setEstado("No se encontró ninguna cámara en este dispositivo.", "error");
    } else {
      setEstado("No se pudo acceder a la cámara: " + error.message, "error");
    }
  }
}

function setEstado(texto, tipo = "info") {
  estadoEl.textContent = texto;
  estadoEl.className =
    tipo === "error"
      ? "text-sm text-red-400"
      : tipo === "ok"
      ? "text-sm text-emerald-400"
      : "text-sm text-slate-400";
}

function capturarFrame() {
  if (!video.videoWidth || !video.videoHeight) {
    throw new Error("La cámara todavía no está lista. Esperá un segundo y probá de nuevo.");
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.9);
  });
}

function renderResultado(data) {
  if (!data.resultados || data.resultados.length === 0) {
    resultadoEl.innerHTML = `<p class="text-slate-300">No se detectó ningún rostro en la imagen.</p>`;
    return;
  }

  resultadoEl.innerHTML = data.resultados
    .map((r) => {
      const esConocido = r.nombre !== "Desconocido";
      const badgeColor = esConocido ? "bg-emerald-500" : "bg-red-500";
      const confianza = r.confianza !== null ? `${(r.confianza * 100).toFixed(1)}%` : "N/A";

      return `
        <div class="flex items-center justify-between rounded-lg bg-slate-800 p-4">
          <div>
            <p class="text-lg font-semibold text-white">${r.nombre}</p>
            <p class="text-xs text-slate-400">Confianza: ${confianza}</p>
          </div>
          <span class="${badgeColor} rounded-full px-3 py-1 text-xs font-bold text-white">
            ${esConocido ? "Reconocido" : "Desconocido"}
          </span>
        </div>
      `;
    })
    .join("");
}

async function enviarAlBackend() {
  btnCapturar.disabled = true;
  setEstado("Capturando y analizando...", "info");
  resultadoEl.innerHTML = "";

  try {
    const blob = await capturarFrame();
    if (!blob) throw new Error("No se pudo capturar la imagen de la cámara.");

    const formData = new FormData();
    formData.append("imagen", blob, "captura.jpg");

    const respuesta = await fetch(`${API_URL}/reconocer/`, {
      method: "POST",
      body: formData,
    });

    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => ({}));
      throw new Error(detalle.detail || `Error del servidor (${respuesta.status})`);
    }

    const data = await respuesta.json();
    renderResultado(data);
    setEstado("Análisis completado.", "ok");
  } catch (error) {
    console.error(error);
    setEstado(error.message || "Ocurrió un error al conectar con el backend.", "error");
  } finally {
    btnCapturar.disabled = false;
  }
}

btnActivarCamara.addEventListener("click", activarCamara);
btnCapturar.addEventListener("click", enviarAlBackend);
