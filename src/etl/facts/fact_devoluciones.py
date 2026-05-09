"""
fact_devoluciones.py — Carga de dwh.fact_devoluciones desde public.return_item.

dim_fecha aparece con dos roles:
  return_date_id → return_item.return_date
  venta_date_id  → sale.sale_date del ítem devuelto

importe_devuelto = quantity * unit_price del ítem original (sale_item).
costo_devuelto   = quantity * unit_cost de central_product; NULL si no disponible.

Assert: COUNT(dwh.fact_devoluciones) == COUNT(public.return_item).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.return_item")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.fact_devoluciones (
            return_date_id, venta_date_id,
            cliente_id, producto_id, tienda_id, oferta_id, motivo_id,
            sale_item_id, return_id,
            quantity_devuelta, importe_devuelto, costo_devuelto
        )
        SELECT
            TO_CHAR(ri.return_date, 'YYYYMMDD')::INT  AS return_date_id,
            TO_CHAR(s.sale_date,    'YYYYMMDD')::INT  AS venta_date_id,
            dc.cliente_id,
            dp.producto_id,
            dt.tienda_id,
            do_.oferta_id,
            dm.motivo_id,
            ri.sale_item_id,
            ri.return_id,
            ri.quantity                               AS quantity_devuelta,
            ri.quantity * si.unit_price               AS importe_devuelto,
            CASE
                WHEN cp.unit_cost IS NOT NULL
                THEN ri.quantity * cp.unit_cost
            END                                       AS costo_devuelto
        FROM public.return_item ri
        JOIN public.sale_item        si   ON si.sale_item_id = ri.sale_item_id
        JOIN public.sale             s    ON s.sale_id       = si.sale_id
        JOIN dwh.dim_cliente         dc   ON dc.customer_id  = s.customer_id
        JOIN dwh.dim_producto        dp   ON dp.product_id   = si.product_id
        JOIN dwh.dim_tienda          dt   ON dt.store_id     = s.store_id
        JOIN dwh.dim_oferta          do_  ON do_.offer_id    = COALESCE(si.offer_id, -1)
        JOIN dwh.dim_motivo          dm   ON dm.reason_id    = COALESCE(ri.reason_id, -1)
        LEFT JOIN public.central_product cp ON cp.product_id = si.product_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.fact_devoluciones")).scalar()

    assert n == n_origen, (
        f"fact_devoluciones — cuadre fallido: origen={n_origen}, destino={n}."
    )

    log.info("fact_devoluciones: %d filas cargadas.", n)
    return n
