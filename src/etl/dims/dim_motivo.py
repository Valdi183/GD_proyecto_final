"""
dim_motivo.py — Carga de dwh.dim_motivo desde public.return_reason.

El módulo inserta primero el sentinel (motivo_id=0, reason_id=-1)
y luego los datos reales.

Assert: COUNT(dwh.dim_motivo) == COUNT(public.return_reason) + 1.
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.return_reason")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_motivo (motivo_id, reason_id, descripcion, es_activo)
        OVERRIDING SYSTEM VALUE
        VALUES (0, -1, 'Motivo no registrado', FALSE)
        ON CONFLICT (motivo_id) DO NOTHING
    """))

    conn.execute(text("""
        INSERT INTO dwh.dim_motivo (reason_id, descripcion, es_activo)
        SELECT
            reason_id,
            reason AS descripcion,
            active AS es_activo
        FROM public.return_reason
        ORDER BY reason_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_motivo")).scalar()
    esperado = n_origen + 1

    assert n == esperado, (
        f"dim_motivo — cuadre fallido: esperadas={esperado} (origen={n_origen}+sentinel), cargadas={n}"
    )

    log.info("dim_motivo: %d filas cargadas (1 sentinel + %d reales).", n, n_origen)
    return n
