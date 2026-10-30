"""Reglas de decisión de un intento de verificación (funciones puras, sin modelo; se prueban con pytest).

Cada fotograma de la ráfaga se clasifica en un estado:
  "valido"          rostro único, cerca, nítido y con buena luz -> se compara con la plantilla
  "sin_rostro"      MTCNN no encuentra un rostro con probabilidad >= PROB_ROSTRO_MIN
  "varios_rostros"  hay otro rostro claro y grande además del principal
  "lejos"           el rostro detectado es demasiado pequeño
  "borroso"         varianza del laplaciano del recorte < LAPLACIANO_MIN
  "oscuro"          media de gris del recorte < BRILLO_MIN
  "sobreexpuesto"   media de gris del recorte > BRILLO_MAX

Decisión del intento (votación por mayoría, como en la tarea 2.6):
  - si hay menos de MIN_VALIDOS fotogramas válidos -> NO CONCLUYENTE (con el motivo más frecuente)
  - si al menos MIN_VOTOS fotogramas válidos tienen puntuación >= umbral -> PERMITIDO
  - en otro caso -> DENEGADO
"""
from collections import Counter

PERMITIDO, DENEGADO, NO_CONCLUYENTE = "permitido", "denegado", "no_concluyente"

TITULOS = {
    PERMITIDO: "Acceso permitido",
    DENEGADO: "Acceso denegado",
    NO_CONCLUYENTE: "No se pudo verificar de forma confiable",
}

MOTIVOS = {
    "sin_rostro": "No se detectó ningún rostro. Colóquese frente a la cámara.",
    "varios_rostros": "Hay más de un rostro en la imagen. Debe aparecer una sola persona.",
    "lejos": "El rostro está demasiado lejos. Acérquese a la cámara.",
    "borroso": "La imagen está muy borrosa. Quédese quieto y limpie la cámara.",
    "oscuro": "La imagen está muy oscura. Mejore la iluminación.",
    "sobreexpuesto": "La imagen tiene demasiada luz. Evite la luz directa.",
}


def clasificar_calidad(lap_var, brillo, lado, cfg):
    """Estado de un fotograma con un único rostro detectado, según su calidad."""
    if lado < cfg.LADO_ROSTRO_MIN:
        return "lejos"
    if brillo < cfg.BRILLO_MIN:
        return "oscuro"
    if brillo > cfg.BRILLO_MAX:
        return "sobreexpuesto"
    if lap_var < cfg.LAPLACIANO_MIN:
        return "borroso"
    return "valido"


def hay_varios_rostros(probs, areas, cfg):
    """True si, además del rostro más grande, hay otro claro (prob alta) y no pequeño."""
    if len(areas) < 2:
        return False
    k = max(range(len(areas)), key=lambda i: areas[i])
    return any(i != k and probs[i] >= cfg.SEGUNDO_ROSTRO_PROB and areas[i] >= cfg.SEGUNDO_ROSTRO_AREA * areas[k]
               for i in range(len(areas)))


def decidir(estados, puntuaciones, umbral, min_votos, min_validos):
    """estados: lista de estados por fotograma; puntuaciones: lista de floats (None si no es válido).
    Devuelve dict con resultado, título, motivo, votos y válidos (sin revelar puntuaciones)."""
    validos = [s for e, s in zip(estados, puntuaciones) if e == "valido"]
    n_val = len(validos)
    if n_val < min_validos:
        problemas = Counter(e for e in estados if e != "valido")
        principal = problemas.most_common(1)[0][0] if problemas else "sin_rostro"
        motivo = MOTIVOS.get(principal, "No hubo suficientes imágenes válidas.")
        motivo += f" (fotogramas válidos: {n_val} de {len(estados)}; se necesitan {min_validos})."
        return {"resultado": NO_CONCLUYENTE, "titulo": TITULOS[NO_CONCLUYENTE], "motivo": motivo,
                "votos": 0, "validos": n_val, "fotogramas": len(estados)}
    votos = sum(1 for s in validos if s >= umbral)
    if votos >= min_votos:
        return {"resultado": PERMITIDO, "titulo": TITULOS[PERMITIDO], "motivo": "El rostro coincide con el usuario seleccionado.",
                "votos": votos, "validos": n_val, "fotogramas": len(estados)}
    return {"resultado": DENEGADO, "titulo": TITULOS[DENEGADO], "motivo": "El rostro no coincide con el usuario seleccionado.",
            "votos": votos, "validos": n_val, "fotogramas": len(estados)}


# ---------------------------------------------------------------- modo B: identificación 1:N
NO_IDENTIFICADO = "no_identificado"
TITULOS[NO_IDENTIFICADO] = "No se pudo identificar de forma confiable"


def identificar(estados, puntuaciones, usuarios, umbral, margen, min_votos, min_validos):
    """Identificación 1:N por votación (sin revelar puntuaciones).

    estados: estado por fotograma; puntuaciones: por fotograma, lista de cosenos contra `usuarios` (None si no es válido).
    Un fotograma vota por su mejor candidato solo si la puntuación >= umbral y supera al segundo por >= margen.
    Se identifica a un usuario si recibe >= min_votos votos. Con menos de min_validos fotogramas válidos el intento es
    NO CONCLUYENTE; si no, y nadie reúne los votos (empate, ambigüedad o nadie supera el umbral), NO IDENTIFICADO.
    """
    validos = [p for e, p in zip(estados, puntuaciones) if e == "valido" and p is not None]
    n_val = len(validos)
    base = {"fotogramas": len(estados), "validos": n_val, "usuario": None}
    if n_val < min_validos:
        r = decidir(estados, [None] * len(estados), umbral, min_votos, min_validos)   # mismo mensaje de calidad
        r.update(base)
        return r
    votos = {}
    for p in validos:
        orden = sorted(range(len(usuarios)), key=lambda i: p[i], reverse=True)
        mejor = orden[0]
        segundo = p[orden[1]] if len(orden) > 1 else float("-inf")
        if p[mejor] >= umbral and p[mejor] - segundo >= margen:
            votos[usuarios[mejor]] = votos.get(usuarios[mejor], 0) + 1
    ganador = [u for u, v in votos.items() if v >= min_votos]
    if len(ganador) == 1:
        return dict(base, resultado=PERMITIDO, titulo=TITULOS[PERMITIDO], usuario=ganador[0],
                    motivo=f"Hola, {ganador[0]}.")
    return dict(base, resultado=NO_IDENTIFICADO, titulo=TITULOS[NO_IDENTIFICADO],
                motivo="El rostro no coincide de forma clara con ningún usuario registrado.")
