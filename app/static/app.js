// Captura una ráfaga de fotogramas con la cámara del navegador y la envía al servidor.
// Modo A: "Nombre + rostro" (/api/verificar). Modo B: "Solo cámara" (/api/identificar).
// Si la cuenta tiene palabra clave, el servidor pide un segundo paso (/api/clave). El servidor no guarda imágenes.
(function () {
  const $ = (id) => document.getElementById(id);
  const video = $("video"), lienzo = $("lienzo"), sinCamara = $("sin-camara");
  const btnCamara = $("btn-camara"), btnVerificar = $("btn-verificar"), selUsuario = $("usuario");
  const progreso = $("progreso"), caja = $("resultado");
  const pasoClave = $("paso-clave"), campoClave = $("clave");

  const NOMBRE_ESTADO = {
    valido: "rostro válido", sin_rostro: "sin rostro", varios_rostros: "varios rostros", lejos: "muy lejos",
    borroso: "borroso", oscuro: "oscuro", sobreexpuesto: "demasiada luz",
  };
  let stream = null, modo = "A", token = null;
  // Modo explicación: copia de los fotogramas SOLO en memoria para dibujar el camino de la decisión; se borra en el siguiente intento.
  const chkExplicar = $("explicar");
  let fotosExplicacion = [];
  const quiereExplicar = () => !!(CONFIG.explicacion && chkExplicar && chkExplicar.checked);
  if (chkExplicar) {
    try { chkExplicar.checked = localStorage.getItem("faceid-explicar") === "1"; } catch (e) {}
    chkExplicar.addEventListener("change", () => {
      try { localStorage.setItem("faceid-explicar", chkExplicar.checked ? "1" : "0"); } catch (e) {}
      if (!chkExplicar.checked) Explicacion.ocultar();
    });
  }
  const marco = $("marco-camara"), puntos = Array.from(document.querySelectorAll("#contador i"));
  const ICONO = { permitido: "✓ ", denegado: "✕ ", bloqueado: "⏳ ", error: "! ", no_concluyente: "? ", no_identificado: "? " };

  function actualizarBoton() {
    btnVerificar.disabled = !(stream && (modo === "B" || selUsuario.value)) || token !== null;
    btnVerificar.textContent = modo === "B" ? "Identificarme" : "Verificar";
  }

  function elegirModo(m) {
    modo = m; token = null; pasoClave.hidden = true; caja.hidden = true; Explicacion.ocultar();
    $("tab-a").setAttribute("aria-selected", m === "A"); $("tab-b").setAttribute("aria-selected", m === "B");
    $("panel-a").hidden = m !== "A"; $("panel-b").hidden = m !== "B";
    actualizarBoton();
  }
  $("tab-a").addEventListener("click", () => elegirModo("A"));
  $("tab-b").addEventListener("click", () => elegirModo("B"));

  btnCamara.addEventListener("click", async () => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null; video.srcObject = null; sinCamara.hidden = false;
      btnCamara.textContent = "Encender cámara"; actualizarBoton(); return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false });
      video.srcObject = stream; sinCamara.hidden = true; btnCamara.textContent = "Apagar cámara";
    } catch (e) {
      sinCamara.hidden = false;
      $("sin-camara-texto").textContent = "No se pudo usar la cámara: " + e.message + ". Revise los permisos del navegador.";
    }
    actualizarBoton();
  });
  selUsuario.addEventListener("change", actualizarBoton);

  function capturar() {
    lienzo.width = video.videoWidth || 640; lienzo.height = video.videoHeight || 480;
    lienzo.getContext("2d").drawImage(video, 0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL("image/jpeg", 0.9);
  }
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const caso = () => ($("caso") ? $("caso").value.trim() : "");

  async function enviar(url, cuerpo) {
    const resp = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    return [resp, await resp.json()];
  }
  function tiempoPrueba(r, seg) {        // solo en modo pruebas
    if (r.id_intento) enviar("/api/prueba/tiempo", { id_intento: r.id_intento, segundos_total: seg });
  }

  btnVerificar.addEventListener("click", async () => {
    btnVerificar.disabled = true; caja.hidden = true; Explicacion.ocultar(); fotosExplicacion = [];
    const t0 = performance.now();
    const fotogramas = [];
    marco.classList.add("capturando"); puntos.forEach((p) => p.classList.remove("hecho"));
    for (let i = 0; i < CONFIG.n; i++) {
      progreso.textContent = `Capturando fotograma ${i + 1} de ${CONFIG.n}…`;
      fotogramas.push(capturar());
      if (puntos[i]) puntos[i].classList.add("hecho");
      if (i < CONFIG.n - 1) await esperar(CONFIG.intervaloMs);
    }
    marco.classList.remove("capturando");
    const explicar = quiereExplicar();
    if (explicar) fotosExplicacion = fotogramas.slice();
    const segCaptura = (performance.now() - t0) / 1000;
    progreso.textContent = modo === "B" ? "Identificando…" : "Verificando…";
    try {
      const [resp, r] = modo === "B"
        ? await enviar("/api/identificar", { fotogramas, segundos_captura: segCaptura, caso: caso(), explicar })
        : await enviar("/api/verificar", { usuario: selUsuario.value, fotogramas, segundos_captura: segCaptura, caso: caso(), explicar });
      const segTotal = (performance.now() - t0) / 1000;
      if (resp.ok && r.resultado === "requiere_clave") {
        token = r.token; pasoClave.hidden = false; campoClave.value = ""; campoClave.focus();
        mostrar({ titulo: r.titulo, motivo: r.motivo, resultado: "no_concluyente", estados: r.estados }, true, segTotal, segCaptura, r);
      } else {
        mostrar(r, resp.ok, segTotal, segCaptura, r);
        explicarSiHay(r, false);
      }
      tiempoPrueba(r, segTotal);
    } catch (e) {
      mostrar({ titulo: "Error de conexión", motivo: e.message }, false);
    } finally {
      fotogramas.length = 0; progreso.textContent = ""; marco.classList.remove("capturando"); actualizarBoton();
    }
  });

  async function enviarClave() {
    if (!token) return;
    $("btn-clave").disabled = true;
    try {
      const [resp, r] = await enviar("/api/clave", { token, clave: campoClave.value, caso: caso() });
      mostrar(r, resp.ok, null, null, r);
      explicarSiHay(r, true);
    } catch (e) {
      mostrar({ titulo: "Error de conexión", motivo: e.message }, false);
    } finally {
      token = null; campoClave.value = ""; pasoClave.hidden = true; $("btn-clave").disabled = false; actualizarBoton();
    }
  }
  $("btn-clave").addEventListener("click", enviarClave);
  campoClave.addEventListener("keydown", (e) => { if (e.key === "Enter") enviarClave(); });
  $("btn-cancelar-clave").addEventListener("click", () => {
    token = null; campoClave.value = ""; pasoClave.hidden = true; caja.hidden = true; fotosExplicacion = []; actualizarBoton();
  });

  function explicarSiHay(r, conClave) {
    if (r && r.explicacion) Explicacion.mostrar(r.explicacion, fotosExplicacion, { titulo: r.titulo, motivo: r.motivo, conClave });
    fotosExplicacion = [];
  }

  function mostrar(r, ok, seg, segCaptura, crudo) {
    caja.hidden = false;
    caja.className = "resultado " + (ok ? r.resultado : "error");
    $("res-titulo").textContent = (ICONO[ok ? r.resultado : "error"] || "") + (ok ? r.titulo : (r.titulo || "No se pudo procesar"));
    $("res-motivo").textContent = ok ? r.motivo : (r.error || r.motivo || "");
    const cont = $("res-fotogramas");
    cont.innerHTML = "";
    (r.estados || []).forEach((e, i) => {
      const s = document.createElement("span");
      s.className = "estado " + (e === "valido" ? "ok" : "mal");
      s.textContent = `${i + 1}: ${NOMBRE_ESTADO[e] || e}`;
      cont.appendChild(s);
    });
    $("res-tiempo").textContent = ok && seg !== null && crudo && crudo.segundos_servidor !== undefined
      ? `Tiempo: ${seg.toFixed(2)} s (captura ${segCaptura.toFixed(2)} s + envío y procesamiento ${(seg - segCaptura).toFixed(2)} s; servidor ${crudo.segundos_servidor.toFixed(2)} s)`
      : "";
  }
  elegirModo("A");
})();
