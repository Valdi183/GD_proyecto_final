"""
run_etl.py — Orquestador del ETL saleshealth → dwh + marts (Kimball).

Responsabilidades:
  1. TRUNCATE en orden inverso: marts primero (sin FK), luego DWH (Opcion C).
  2. Carga DWH en orden topologico (pasos 1-9).
  3. Carga MARTS en orden topologico (paso 10: customer_360).
  4. Cuadre final: ground truth de ingresos netos del periodo.

Uso:
    cd GD_proyecto_final
    python src/etl/run_etl.py
"""

import sys
from pathlib import Path

# Garantiza que 'src/' esté en el path para que los imports 'from etl.*'
# funcionen independientemente del directorio de trabajo del llamador.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Fuerza UTF-8 en stdout para que los mensajes de log con caracteres no-ASCII
# no fallen en terminales Windows (CP1252 por defecto).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import logging
import time

from sqlalchemy import text

from etl.config import LOAD_ORDER, TRUNCATE_ORDER, MARTS_TABLES
from etl.db import get_engine
from etl.dims import dim_fecha, dim_zona, dim_oferta, dim_motivo
from etl.dims import dim_producto, dim_tienda, dim_cliente
from etl.facts import fact_ventas, fact_devoluciones
from etl.marts import customer_360
from etl.marts import clusters as _clusters_mod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-35s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("etl")

MODULOS_DWH = {
    "dim_fecha":         dim_fecha,
    "dim_zona":          dim_zona,
    "dim_oferta":        dim_oferta,
    "dim_motivo":        dim_motivo,
    "dim_producto":      dim_producto,
    "dim_tienda":        dim_tienda,
    "dim_cliente":       dim_cliente,
    "fact_ventas":       fact_ventas,
    "fact_devoluciones": fact_devoluciones,
}

MODULOS_MARTS = {
    "customer_360": customer_360,
}


def truncar_todo(conn) -> None:
    """TRUNCATE en orden inverso.
    Marts primero (sin FK formales, no necesitan CASCADE),
    luego DWH en orden inverso topologico (facts → dims con FK → dims base).
    """
    for tabla in reversed(MARTS_TABLES):
        conn.execute(text(f"TRUNCATE marts.{tabla} RESTART IDENTITY"))
    for tabla in TRUNCATE_ORDER:
        conn.execute(text(f"TRUNCATE dwh.{tabla} RESTART IDENTITY CASCADE"))
    log.info("TRUNCATE completado (%d tablas: %d marts + %d dwh).",
             len(MARTS_TABLES) + len(TRUNCATE_ORDER), len(MARTS_TABLES), len(TRUNCATE_ORDER))


def cuadre_final(conn) -> None:
    """Calcula ingresos netos como ground truth para Fase 5 (CLTV)."""
    row = conn.execute(text("""
        WITH v AS (
            SELECT SUM(subtotal)     AS brutos,
                   SUM(margen_bruto) AS margen
            FROM dwh.fact_ventas
        ),
        d AS (
            SELECT SUM(importe_devuelto) AS devuelto
            FROM dwh.fact_devoluciones
        )
        SELECT
            v.brutos,
            d.devuelto,
            v.brutos - COALESCE(d.devuelto, 0) AS netos,
            v.margen
        FROM v, d
    """)).fetchone()

    log.info("─" * 55)
    log.info("CUADRE FINAL (ground truth Fase 5)")
    log.info("  Ingresos brutos:    %14.2f €", row[0] or 0)
    log.info("  Devoluciones:       %14.2f €", row[1] or 0)
    log.info("  Ingresos netos:     %14.2f €", row[2] or 0)
    log.info("  Margen bruto total: %14.2f €", row[3] or 0)
    log.info("─" * 55)


def main() -> None:
    log.info("=" * 55)
    log.info("INICIO ETL — saleshealth → dwh")
    log.info("=" * 55)

    engine = get_engine()
    t_total = time.perf_counter()

    with engine.begin() as conn:
        truncar_todo(conn)

    for tabla in LOAD_ORDER:
        modulo = MODULOS_DWH[tabla]
        t0 = time.perf_counter()
        with engine.begin() as conn:
            n = modulo.cargar(conn)
        log.info("%-25s  %6d filas  %4.1fs", tabla, n, time.perf_counter() - t0)

    with engine.connect() as conn:
        cuadre_final(conn)

    log.info("-" * 55)
    log.info("MARTS")
    log.info("-" * 55)

    for tabla in MARTS_TABLES:
        modulo = MODULOS_MARTS[tabla]
        t0 = time.perf_counter()
        with engine.begin() as conn:
            n = modulo.cargar(conn)
        log.info("%-25s  %6d filas  %4.1fs", tabla, n, time.perf_counter() - t0)

    # Paso 11 — clusters: actualizar cluster_id y cluster_label
    # Omite silenciosamente si el notebook 06_clustering.ipynb (S6) no se ha
    # ejecutado aún (parquet de asignaciones no existe).
    try:
        t0 = time.perf_counter()
        with engine.begin() as conn:
            n = _clusters_mod.cargar(conn)
        log.info("%-25s  %6d filas  %4.1fs", "clusters", n, time.perf_counter() - t0)
    except FileNotFoundError as exc:
        log.warning("clusters: omitido (paso 11) — %s", exc)

    log.info("ETL COMPLETADO en %.1fs", time.perf_counter() - t_total)


if __name__ == "__main__":
    main()
