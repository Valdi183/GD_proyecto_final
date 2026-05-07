"""
dim_producto.py — Carga de dwh.dim_producto.

Desnormaliza product + central_product + category + brand en una sola fila.
Tras la corrección D05 la cobertura de central_product es 100 %, por lo que
unit_cost y categoria/marca no deberían quedar NULL.

Assert: COUNT(dwh.dim_producto) == COUNT(public.product).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.product")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_producto (
            product_id, nombre, categoria, marca, sku, precio_lista, costo_unitario
        )
        SELECT
            p.product_id,
            p.name            AS nombre,
            cat.name          AS categoria,
            b.name            AS marca,
            cp.sku,
            p.price           AS precio_lista,
            cp.unit_cost      AS costo_unitario
        FROM public.product p
        LEFT JOIN public.central_product cp  ON cp.product_id  = p.product_id
        LEFT JOIN public.category        cat ON cat.category_id = cp.category_id
        LEFT JOIN public.brand           b   ON b.brand_id      = cp.brand_id
        ORDER BY p.product_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_producto")).scalar()

    assert n == n_origen, (
        f"dim_producto — cuadre fallido: origen={n_origen}, destino={n}"
    )

    n_sin_costo = conn.execute(text(
        "SELECT COUNT(*) FROM dwh.dim_producto WHERE costo_unitario IS NULL"
    )).scalar()
    if n_sin_costo > 0:
        log.warning("dim_producto: %d producto(s) sin costo_unitario (margen_bruto será NULL).", n_sin_costo)

    log.info("dim_producto: %d filas cargadas.", n)
    return n
