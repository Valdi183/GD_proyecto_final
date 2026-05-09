"""
config.py — Parámetros globales del ETL.
"""

from datetime import date

# ── Schemas ───────────────────────────────────────────────────────────────────
SCHEMA_SRC   = "public"   # tablas operacionales (origen)
SCHEMA_DWH   = "dwh"      # modelo dimensional Kimball (hechos + dimensiones)
SCHEMA_MARTS = "marts"    # tablas derivadas pre-agregadas (análisis / ML)

# ── dim_fecha ─────────────────────────────────────────────────────────────────
DIM_FECHA_START = date(2020, 1, 1)
DIM_FECHA_END   = date(2027, 12, 31)

# Número de días esperados en dim_fecha; calculado dinámicamente para que
# cambie automáticamente si se ajustan las fechas de inicio/fin.
DIM_FECHA_EXPECTED_ROWS = (DIM_FECHA_END - DIM_FECHA_START).days + 1

# ── Ground truths — Fase 5 ────────────────────────────────────────────────────
# Calculados al cierre de Fase 4; se usan como assert en customer_360.
MARGEN_BRUTO_TOTAL     = 3_779_316.80
IMPORTE_DEVUELTO_TOTAL =   276_310.81
COSTO_DEVUELTO_TOTAL   =   167_363.65
# margen_neto = MARGEN_BRUTO_TOTAL - IMPORTE_DEVUELTO_TOTAL + COSTO_DEVUELTO_TOTAL
CLTV_TOTAL_ESPERADO    = round(
    MARGEN_BRUTO_TOTAL - IMPORTE_DEVUELTO_TOTAL + COSTO_DEVUELTO_TOTAL, 2
)  # = 3_670_369.64 €

# ── Orden de carga DWH (topológico) ──────────────────────────────────────────
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

# ── Tablas MARTS (después del DWH completo) ───────────────────────────────────
# Lista única; el orquestador usa reversed() inline cuando necesita TRUNCATE.
# Dos listas separadas (LOAD / TRUNCATE) solo se justifican cuando haya
# dependencias entre tablas marts propias — no es el caso ahora.
MARTS_TABLES = ["customer_360"]
