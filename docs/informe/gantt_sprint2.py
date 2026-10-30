"""Diagrama de Gantt del Sprint 2 (fechas PLANIFICADAS), mismo estilo que el del Sprint 1."""
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

TAREAS = [  # id, nombre corto, inicio, fin (inclusive), fase
    ("2.1", "Seleccionar técnica de modelado", date(2026, 10, 12), date(2026, 10, 14), 4),
    ("2.2", "Preparar modelo y registrar plantillas", date(2026, 10, 14), date(2026, 10, 18), 4),
    ("2.3", "Validar y ajustar parámetros", date(2026, 10, 17), date(2026, 10, 20), 4),
    ("2.4", "Definir métricas y valores objetivo", date(2026, 10, 19), date(2026, 10, 20), 5),
    ("2.5", "Evaluar con prueba y fijar umbral", date(2026, 10, 21), date(2026, 10, 22), 5),
    ("2.6", "Probar con video y decidir despliegue", date(2026, 10, 22), date(2026, 10, 23), 5),
]
COLOR = {4: "#2e75b6", 5: "#548235"}
LEYENDA = {4: "Fase 4: Modelado", 5: "Fase 5: Evaluación"}

fig, ax = plt.subplots(figsize=(10.2, 4.6), dpi=200)
for k, (tid, nom, ini, fin, fase) in enumerate(TAREAS):
    dur = (fin - ini).days + 1
    ax.barh(k, dur, left=mdates.date2num(ini), height=0.55, color=COLOR[fase], edgecolor="#1f3864", linewidth=1.2)
    ax.text(mdates.date2num(ini) + dur / 2, k, f"{dur} d", ha="center", va="center", color="white", fontweight="bold", fontsize=10)
ax.set_yticks(range(len(TAREAS))); ax.set_yticklabels([f"{t[0]} {t[1]}" for t in TAREAS], fontsize=10); ax.invert_yaxis()
d0, d1 = date(2026, 10, 12), date(2026, 10, 24)
ax.set_xlim(mdates.date2num(d0), mdates.date2num(d1))
ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
ax.grid(axis="x", linestyle="--", color="#d0d0d0"); ax.set_axisbelow(True)
for s in ["top", "right"]: ax.spines[s].set_visible(False)
ax.set_xlabel("Fecha (2026)", fontsize=10)
ax.legend(handles=[Patch(color=COLOR[f], label=LEYENDA[f]) for f in (4, 5)], frameon=False, fontsize=9, loc="upper right")
plt.tight_layout()
out = Path(__file__).parent / "figuras" / "gantt_sprint2.png"
plt.savefig(out); print(out)
