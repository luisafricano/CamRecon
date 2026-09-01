// Se incluye en index.html, tracking.html y panel.html (después de config.js).
// Corta la carga de la página si no hay una sesión válida.

(function () {
  if (!localStorage.getItem("camrecon_token")) {
    window.location.href = "login.html";
  }
})();

async function verificarSesion() {
  const token = localStorage.getItem("camrecon_token");
  if (!token) {
    window.location.href = "login.html";
    return;
  }
  try {
    const res = await fetch(`${API_URL}/auth/verificar`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error();
  } catch {
    localStorage.removeItem("camrecon_token");
    localStorage.removeItem("camrecon_usuario");
    window.location.href = "login.html";
  }
}

function cerrarSesion() {
  const token = localStorage.getItem("camrecon_token");
  fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).finally(() => {
    localStorage.removeItem("camrecon_token");
    localStorage.removeItem("camrecon_usuario");
    window.location.href = "login.html";
  });
}

verificarSesion();
