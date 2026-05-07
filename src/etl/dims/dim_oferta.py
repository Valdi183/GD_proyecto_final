"""
dim_oferta.py — Carga de dwh.dim_oferta desde public.offer.

El módulo inserta primero el sentinel (oferta_id=0, offer_id=-1)
y luego los datos reales.

Assert: COUNT(dwh.dim_oferta) == COUNT(public.offer) + 1  (el +1 es el sentinel).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.offer")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_oferta (oferta_id, offer_id, nombre, descuento_pct, fecha_inicio, fecha_fin)
        OVERRIDING SYSTEM VALUE
        VALUES (0, -1, 'Sin oferta', NULL, NULL, NULL)
        ON CONFLICT (oferta_id) DO NOTHING
    """))

    conn.execute(text("""
        INSERT INTO dwh.dim_oferta (offer_id, nombre, descuento_pct, fecha_inicio, fecha_fin)
        SELECT
            offer_id,
            name             AS nombre,
            discount_percent AS descuento_pct,
            start_date       AS fecha_inicio,
            end_date         AS fecha_fin
        FROM public.offer
        ORDER BY offer_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_oferta")).scalar()
    esperado = n_origen + 1

    assert n == esperado, (
        f"dim_oferta — cuadre fallido: esperadas={esperado} (origen={n_origen}+sentinel), cargadas={n}"
    )

    log.info("dim_oferta: %d filas cargadas (1 sentinel + %d reales).", n, n_origen)
    return n
