"""
dim_zona.py — Carga de dwh.dim_zona desde public.city_zone.

Pre-condición: el orquestador ya ejecutó TRUNCATE RESTART IDENTITY en orden
inverso; este módulo solo hace INSERT.

Assert de cuadre: COUNT(public.city_zone) == COUNT(dwh.dim_zona).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    """Carga dim_zona y retorna el número de filas insertadas."""

    n_origen = conn.execute(
        text("SELECT COUNT(*) FROM public.city_zone")
    ).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_zona (postal_code, distrito, tipo_area, orientacion, ciudad)
        SELECT
            postal_code,
            district         AS distrito,
            area_type        AS tipo_area,
            zone_orientation AS orientacion,
            city             AS ciudad
        FROM public.city_zone
        ORDER BY postal_code
    """))

    n_cargado = conn.execute(
        text("SELECT COUNT(*) FROM dwh.dim_zona")
    ).scalar()

    assert n_cargado == n_origen, (
        f"dim_zona — cuadre fallido: origen={n_origen}, destino={n_cargado}"
    )

    log.info("dim_zona: %d filas cargadas.", n_cargado)
    return n_cargado
