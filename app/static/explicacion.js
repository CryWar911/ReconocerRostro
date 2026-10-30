// Modo explicación (exposición): dibuja el camino que siguió la máquina para decidir.
// Usa solo lo que devolvió el servidor en este intento y los fotogramas que el navegador ya tenía en memoria.
// No guarda nada: al empezar otro intento o recargar la página, todo desaparece.
window.Explicacion = (function () {
  const NOMBRE_ESTADO = {
    valido: "rostro válido", sin_rostro: "sin rostro", varios_rostros: "varios rostros", lejos: "muy lejos",
    borroso: "borroso", oscuro: "oscuro", sobreexpuesto: "demasiada luz",
  };
  const num = (x, d = 3) => x.toFixed(d).replace(".", ",");

  function el(tag, attrs, ...hijos) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v;
      else if (k === "style") n.style.cssText = v;
      else n.setAttribute(k, v);
    }
    for (const h of hijos.flat()) if (h !== null && h !== undefined && h !== false) n.append(h);
    return n;
  }

  function paso(titulo, que, ...contenido) {
    return el("li", {}, el("h3", {}, titulo), el("p", { class: "que" }, que), ...contenido);
  }

  // ---------------------------------------------------------------- 1. fotogramas con las cajas del detector
  function miniatura(src, f, i, elegido, pie) {
    const lienzo = el("canvas", { width: 320, height: 240, "aria-label": `Fotograma ${i + 1}` });
    const img = new Image();
    img.onload = () => {
      const ctx = lienzo.getContext("2d");
      lienzo.width = 320; lienzo.height = Math.round(320 * img.height / img.width);
      const s = lienzo.width / (f.ancho || img.width);
      ctx.drawImage(img, 0, 0, lienzo.width, lienzo.height);
      const caja = (b, color, ancho) => {
        ctx.strokeStyle = color; ctx.lineWidth = ancho;
        ctx.strokeRect(b[0] * s, b[1] * s, (b[2] - b[0]) * s, (b[3] - b[1]) * s);
      };
      (f.otras || []).forEach((b) => caja(b, "#f87171", 2));
      if (f.caja) caja(f.caja, f.estado === "valido" ? "#2dd4bf" : "#fbbf24", 3);
    };
    if (src) img.src = src;
    return el("figure", { class: "miniatura" + (elegido ? " elegido" : "") }, lienzo, el("figcaption", {}, pie));
  }

  // ---------------------------------------------------------------- 4. vector de 512 como mosaico de colores
  function vector(emb) {
    const max = Math.max(...emb.map(Math.abs)) || 1;
    const rejilla = el("div", { class: "vector", role: "img", "aria-label": "Vector de 512 números del rostro" });
    emb.forEach((v) => {
      const t = Math.min(1, Math.abs(v) / max);
      const c = v >= 0 ? `rgb(${241 - 21 * t},${245 - 207 * t},${249 - 211 * t})` : `rgb(${241 - 204 * t},${245 - 146 * t},${249 - 14 * t})`;
      rejilla.append(el("i", { style: `background:${c}`, title: num(v, 4) }));
    });
    return rejilla;
  }

  // ---------------------------------------------------------------- 5. barras de similitud con el umbral
  function barra(nombre, p, umbral, clase) {
    const ancho = Math.max(0, Math.min(1, p)) * 100;
    return el("div", { class: "barra-p" },
      el("span", { class: "nombre", title: nombre }, nombre),
      el("span", { class: "pista" },
        el("span", { class: "relleno " + clase, style: `display:block;width:${ancho}%` }),
        el("span", { class: "umbral", style: `left:${umbral * 100}%`, "data-t": "umbral " + num(umbral, 4) })),
      el("span", { class: "num" }, num(p)));
  }

  function mostrar(e, fotos, final) {
    const seccion = document.getElementById("explicacion"), flujo = document.getElementById("flujo");
    if (!seccion) return;
    flujo.replaceChildren();
    const F = e.fotogramas || [], R = e.rostro, elegido = R ? R.fotograma - 1 : -1;
    const validos = F.filter((f) => f.estado === "valido").length;

    // 1. Captura y detección
    flujo.append(paso("Captura y detección del rostro (MTCNN)",
      `La cámara tomó ${F.length} fotogramas. En cada uno, la red MTCNN busca rostros (caja turquesa = rostro válido; ` +
      `ámbar = rostro con mala calidad; roja = otro rostro) y se revisa nitidez, luz y distancia. Válidos: ${validos} de ${F.length}.`,
      el("div", { class: "tira" }, F.map((f, i) => {
        let pie = [el("b", {}, `F${i + 1}`), " · " + (NOMBRE_ESTADO[f.estado] || f.estado)];
        return miniatura(fotos[i], f, i, i === elegido, pie);
      }))));

    if (R) {
      // 2. Recorte
      flujo.append(paso("Recorte y alineación (160 × 160 píxeles)",
        `Se recorta el rostro del fotograma ${R.fotograma} (el de mayor similitud) y se lleva a 160 × 160. Es la única entrada que ve la red ` +
        `neuronal. A la derecha, las zonas que más activan los bloques intermedios (aproximación, no es Grad-CAM).`,
        el("div", { class: "fila" },
          el("figure", { class: "pieza" }, el("img", { src: R.recorte, alt: "Rostro recortado" }), el("figcaption", {}, "Entrada: 160 × 160 × 3")),
          el("span", { class: "flecha", "aria-hidden": "true" }, "→"),
          el("figure", { class: "pieza" }, el("img", { src: R.atencion, alt: "Mapa de activación sobre el rostro" }),
            el("figcaption", {}, "Dónde se activa la red (bloques A)")))));

      // 3. Capas de la CNN
      flujo.append(paso("Red neuronal convolucional FaceNet (Inception-ResNet v1)",
        "La imagen atraviesa las capas de la red (preentrenada con VGGFace2, sin modificar). Cada mosaico muestra 8 de los mapas de " +
        "activación más fuertes de esa capa (amarillo = activación alta). Al avanzar, los mapas son más pequeños y más abstractos.",
        el("div", { class: "capas" }, R.capas.map((c) => el("div", { class: "capa" },
          el("img", { src: c.mosaico, alt: "Mapas de activación de " + c.titulo }),
          el("h4", {}, c.titulo), el("span", { class: "forma" }, c.forma), el("p", {}, c.texto))))));

      // 4. Embedding
      flujo.append(paso("Vector de características: 512 números",
        "La salida de la red es un vector de 512 números normalizado (longitud 1): la «huella» del rostro. Rostros de la misma persona " +
        "dan vectores parecidos. Cada cuadro es un número (rojo = positivo, azul = negativo).",
        vector(R.embedding),
        el("div", { class: "leyenda" }, "negativo", el("span", { class: "degradado" }), "positivo")));
    } else {
      flujo.append(paso("La red neuronal no llegó a ejecutarse",
        "Ningún fotograma pasó el control de calidad, así que no se calculó ningún vector. Por eso el resultado es «no concluyente».",
        el("p", { class: "nota" }, "Mejore la luz, acérquese a la cámara y asegúrese de que solo aparezca su rostro.")));
    }

    // 5. Comparación
    if (e.modo === "A") {
      flujo.append(paso(`Comparación con la plantilla de «${e.usuario}» (1 a 1)`,
        `Similitud coseno entre el vector de cada fotograma y la plantilla guardada del usuario elegido. ` +
        `Un fotograma vota «sí» si llega al umbral ${num(e.umbral, 4)}, fijado en la evaluación del modelo (Sprint 2).`,
        el("div", { class: "barras" }, F.map((f, i) => f.puntuacion === null
          ? el("div", { class: "barra-p" }, el("span", { class: "nombre" }, `F${i + 1}`), el("span", { class: "suave" }, "sin vector (" + (NOMBRE_ESTADO[f.estado] || f.estado) + ")"), el("span"))
          : barra(`F${i + 1}`, f.puntuacion, e.umbral, f.voto ? "si" : "")))));
    } else {
      flujo.append(paso("Comparación con todos los usuarios de la app (1:N)",
        `Para cada fotograma se ordenan los usuarios por similitud. Cuenta como voto si el mejor llega al umbral ${num(e.umbral, 4)} ` +
        `y supera al segundo por al menos ${num(e.margen, 2)} (margen).`,
        el("div", { class: "grupos-f" }, F.map((f, i) => el("div", { class: "grupo-f" },
          el("h5", {}, el("span", {}, `Fotograma ${i + 1}`),
            el("span", { class: "suave" }, f.voto ? "vota por " + f.voto : (f.razon || NOMBRE_ESTADO[f.estado] || f.estado))),
          f.candidatos.length
            ? el("div", { class: "barras" }, f.candidatos.map((c, k) => barra(c.usuario, c.puntuacion, e.umbral,
                k === 0 ? (f.voto ? "si" : "cerca") : "")))
            : el("p", { class: "suave", style: "margin:0;font-size:.85rem" }, "Sin vector: no se compara."))))));
    }

    // 6. Votación
    const votos = F.map((f) => e.modo === "A" ? (f.puntuacion === null ? null : f.voto) : (f.candidatos.length ? f.voto : null));
    let resumen;
    if (e.modo === "A") {
      resumen = `${votos.filter((v) => v === true).length} de ${F.length} votos «sí» (se necesitan ${e.votos_necesarios}).`;
    } else {
      const cuenta = {};
      votos.forEach((v) => { if (v) cuenta[v] = (cuenta[v] || 0) + 1; });
      const mejor = Object.entries(cuenta).sort((a, b) => b[1] - a[1])[0];
      resumen = mejor ? `El más votado reúne ${mejor[1]} de ${F.length} votos (se necesitan ${e.votos_necesarios}).`
                      : `Ningún fotograma votó por un usuario (se necesitan ${e.votos_necesarios} votos del mismo).`;
    }
    flujo.append(paso("Votación de los fotogramas y decisión",
      `Un solo fotograma puede engañar (un parpadeo, un gesto). Por eso decide la mayoría: ${resumen}`,
      el("div", { class: "votos" }, votos.map((v, i) => {
        const clase = v === null ? "nulo" : (v ? "si" : "no");
        const txt = v === null ? "—" : (e.modo === "A" ? (v ? "sí" : "no") : (v || "no"));
        return el("div", { class: "voto " + clase }, el("b", {}, txt), `F${i + 1}`);
      })),
      final ? el("p", { class: "veredicto" }, "Resultado: " + final.titulo + (final.motivo ? ". " + final.motivo : "")) : null,
      final && final.conClave ? el("p", { class: "nota" }, "Además se pidió la palabra clave (paso 2); el acceso exige que el rostro y la clave sean correctos.") : null,
      el("p", { class: "nota" }, "Este prototipo no tiene detección de vida: una foto o un video de un usuario podría pasar estos mismos pasos.")));

    seccion.hidden = false;
    seccion.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  function ocultar() {
    const s = document.getElementById("explicacion");
    if (s) { s.hidden = true; document.getElementById("flujo").replaceChildren(); }
  }
  return { mostrar, ocultar };
})();
