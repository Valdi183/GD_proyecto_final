"""
fact_ventas.py — Carga de dwh.fact_ventas desde public.sale_item.

JOIN con dim_oferta usa COALESCE(si.offer_id, -1) sobre la natural key
para resolver el sentinel antes del JOIN (no después), evitando NULLs
en la FK oferta_id de la tabla destino.

margen_bruto = subtotal - (quantity × unit_cost); NULL si unit_cost es NULL.

Assert: COUNT(dwh.fact_ventas) == COUNT(public.sale_item).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.sale_item")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.fact_ventas (
            date_id, cliente_id, producto_id, tienda_id, oferta_id,
            sale_id, sale_item_id,
            quantity, unit_price, unit_cost, subtotal, margen_bruto
        )
        SELECT
            TO_CHAR(s.sale_date, 'YYYYMMDD')::INT  AS date_id,
            dc.cliente_id,
            dp.producto_id,
            dt.tienda_id,
            do_.oferta_id,
            s.sale_id,
            si.sale_item_id,
            si.quantity,
            si.unit_price,
            cp.unit_cost,
            si.subtotal,
            CASE
                WHEN cp.unit_cost IS NOT NULL
                THEN si.subtotal - si.quantity * cp.unit_cost
            END                                    AS margen_bruto
        FROM public.sale_item si
        JOIN public.sale          s   ON s.sale_id      = si.sale_id
        JOIN dwh.dim_cliente      dc  ON dc.customer_id = s.customer_id
        JOIN dwh.dim_producto     dp  ON dp.product_id  = si.product_id
        JOIN dwh.dim_tienda       dt  ON dt.store_id    = s.store_id
        JOIN dwh.dim_oferta       do_ ON do_.offer_id   = COALESCE(si.offer_id, -1)
        LEFT JOIN public.central_product cp ON cp.product_id = si.product_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.fact_ventas")).scalar()

    assert n == n_origen, (
        f"fact_ventas — cuadre fallido: origen={n_origen}, destino={n}. "
        "Verificar claves foráneas sin resolución en dimensiones."
    )

    log.info("fact_ventas: %d filas cargadas.", n)
    return n
