"""
dim_cliente.py — Carga de dwh.dim_cliente desde public.customer.

zona_id = zona predominante del cliente, calculada como la moda del
postal_code de sus compras (sale → store → city_zone). Desempates:
  Caso 2: primera compra en la zona candidata (MIN sale_date por zona)
  Caso 3: menor postal_code lexicográfico

Pre-condiciones: dim_zona ya está cargada; 0 clientes sin compras (D-M07).

Assert: COUNT(dwh.dim_cliente) == COUNT(public.customer).
"""

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_origen = conn.execute(text("SELECT COUNT(*) FROM public.customer")).scalar()

    conn.execute(text("""
        INSERT INTO dwh.dim_cliente (
            customer_id, nombre_completo, email, telefono,
            fecha_alta_efectiva, zona_id
        )
        WITH compras_por_zona AS (
            -- Compras agrupadas por (cliente, zona postal)
            SELECT
                s.customer_id,
                st.postal_code,
                COUNT(*)         AS n_compras,
                MIN(s.sale_date) AS primera_en_zona
            FROM public.sale s
            JOIN public.store st ON st.store_id = s.store_id
            GROUP BY s.customer_id, st.postal_code
        ),
        max_por_cliente AS (
            -- Máximo de compras por cliente (para detectar moda)
            SELECT customer_id, MAX(n_compras) AS max_compras
            FROM compras_por_zona
            GROUP BY customer_id
        ),
        candidatos AS (
            -- Zonas que alcanzan el máximo (puede haber empate)
            SELECT cpz.customer_id, cpz.postal_code, cpz.primera_en_zona
            FROM compras_por_zona cpz
            JOIN max_por_cliente mpc
              ON mpc.customer_id = cpz.customer_id
             AND cpz.n_compras   = mpc.max_compras
        ),
        zona_elegida AS (
            -- Desempate: primera visita a esa zona; si igual → menor postal_code
            SELECT DISTINCT ON (customer_id)
                customer_id,
                postal_code
            FROM candidatos
            ORDER BY customer_id, primera_en_zona, postal_code
        ),
        primera_compra AS (
            SELECT customer_id, MIN(sale_date)::date AS fecha_alta
            FROM public.sale
            GROUP BY customer_id
        )
        SELECT
            c.customer_id,
            CONCAT_WS(' ', c.first_name, c.last_name, c.last_name2) AS nombre_completo,
            c.email,
            c.phone    AS telefono,
            pc.fecha_alta AS fecha_alta_efectiva,
            dz.zona_id
        FROM public.customer c
        JOIN zona_elegida   ze ON ze.customer_id  = c.customer_id
        JOIN dwh.dim_zona   dz ON dz.postal_code  = ze.postal_code
        JOIN primera_compra pc ON pc.customer_id  = c.customer_id
        ORDER BY c.customer_id
    """))

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_cliente")).scalar()

    assert n == n_origen, (
        f"dim_cliente — cuadre fallido: origen={n_origen}, destino={n}. "
        "Verificar clientes sin compras o sin zona resuelta."
    )

    log.info("dim_cliente: %d filas cargadas.", n)
    return n
