"""
dim_tienda.py — Carga de dwh.dim_tienda desde public.store.

zona_id se resuelve haciendo JOIN con dwh.dim_zona por postal_code.
Pre-condición: dim_zona ya está cargada.

Assert: COUNT(dwh.dim_tienda) == COUNT(public.store).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.store")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_tienda (store_id, nombre, ciudad, fecha_apertura, latitud, longitud, zona_id)
        SELECT
            st.store_id,
            st.name        AS nombre,
            st.city        AS ciudad,
            st.opened_date AS fecha_apertura,
            st.latitude    AS latitud,
            st.longitude   AS longitud,
            dz.zona_id
        FROM public.store st
        JOIN dwh.dim_zona dz ON dz.postal_code = st.postal_code
        ORDER BY st.store_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_tienda")).scalar()

    assert n == n_origen, (
        f"dim_tienda — cuadre fallido: origen={n_origen}, destino={n}. "
        "Verificar que todos los postal_code de store existen en dim_zona."
    )

    log.info("dim_tienda: %d filas cargadas.", n)
    return n
