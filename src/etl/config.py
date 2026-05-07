"""
config.py — Parámetros globales del ETL.
"""

from datetime import date

# ── dim_fecha ─────────────────────────────────────────────────────────────────
DIM_FECHA_START = date(2020, 1, 1)
DIM_FECHA_END   = date(2027, 12, 31)

# Número de días esperados en dim_fecha; calculado dinámicamente para que
# cambie automáticamente si se ajustan las fechas de inicio/fin.
DIM_FECHA_EXPECTED_ROWS = (DIM_FECHA_END - DIM_FECHA_START).days + 1

# ── Orden de carga (topológico) ───────────────────────────────────────────────
# El orquestador hace TRUNCATE en orden inverso y carga en este orden.
LOAD_ORDER = [
    "dim_fecha",
    "dim_zona",
    "dim_oferta",
    "dim_motivo",
    "dim_producto",
    "dim_tienda",
    "dim_cliente",
    "fact_ventas",
    "fact_devoluciones",
]

TRUNCATE_ORDER = list(reversed(LOAD_ORDER))
