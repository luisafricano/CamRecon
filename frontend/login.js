// Si ya hay una sesión guardada, no tiene sentido mostrar el login de nuevo.
(function redirigirSiYaLogueado() {
  if (localStorage.getItem("camrecon_token")) {
    window.location.href = "panel.html";
  }
})();

const form = document.getElementById("form-login");
const errorEl = document.getElementById("error-login");
const btnLogin = document.getElementById("btn-login");

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  errorEl.hidden = true;
  btnLogin.disabled = true;
  btnLogin.textContent = "Ingresando...";

  const formData = new FormData();
  formData.append("usuario", document.getElementById("login-usuario").value.trim());
  formData.append("password", document.getElementById("login-password").value);

  try {
    const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body: formData });
    if (!res.ok) {
      const detalle = await res.json().catch(() => ({}));
      throw new Error(detalle.detail || "No se pudo iniciar sesión.");
    }
    const data = await res.json();
    localStorage.setItem("camrecon_token", data.token);
    localStorage.setItem("camrecon_usuario", data.usuario);
    window.location.href = "panel.html";
  } catch (error) {
    errorEl.textContent = error.message || "Error de conexión con el servidor.";
    errorEl.hidden = false;
    btnLogin.disabled = false;
    btnLogin.textContent = "Ingresar";
  }
});
