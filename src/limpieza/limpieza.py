#!/usr/bin/env python3
"""
Fase 1 — Limpieza de datos operacionales (schema public).
Aplica las correcciones D02, D03 y D05 documentadas en reports/decisiones_limpieza.md.

Idempotente: puede ejecutarse múltiples veces sin efectos secundarios.
Cada corrección comprueba antes si hay trabajo que hacer y loguea cuántas filas afecta.

Uso:
    cd GD_proyecto_final
    python src/limpieza/limpieza.py
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ─────────────────────────────────────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────────────────────────────────────

def get_engine():
    load_dotenv()
    required = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"[ERROR] Variables de entorno faltantes: {', '.join(missing)}")
    url = (
        f"postgresql+psycopg2://"
        f"{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    return create_engine(url)


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# D02 — Deduplicar sale_item
# ─────────────────────────────────────────────────────────────────────────────

def d02_deduplicar_sale_item(conn):
    """
    Elimina filas duplicadas en sale_item, conservando la de menor sale_item_id
    para cada combinación (sale_id, product_id, quantity, unit_price, offer_id, subtotal).

    Decisión D02: dos registros con contenido económico idéntico en la misma
    venta son semánticamente indistinguibles. Se eliminan 242 filas extra
    (240 grupos; 147 con IDs consecutivos, 93 no consecutivos).

    Complicación: return_item tiene FK a sale_item. Si alguna copia tiene
    devoluciones asociadas, hay que redirigir esas devoluciones al sale_item_id
    superviviente (el mínimo) antes de poder borrar la copia.
    """
    log("D02 — Comprobando duplicados en sale_item...")

    n_antes = conn.execute(text("SELECT COUNT(*) FROM public.sale_item")).scalar()

    n_duplicadas = conn.execute(text("""
        SELECT COUNT(*) FROM public.sale_item
        WHERE sale_item_id NOT IN (
            SELECT MIN(sale_item_id)
            FROM public.sale_item
            GROUP BY sale_id, product_id, quantity, unit_price, offer_id, subtotal
        )
    """)).scalar()

    log(f"D02 — Filas totales: {n_antes:,}  |  Duplicadas a eliminar: {n_duplicadas}")

    if n_duplicadas == 0:
        log("D02 — Sin duplicados. Nada que hacer.")
        return

    # Paso 1: redirigir devoluciones que apuntan a copias → sale_item_id superviviente.
    # Usamos una window function para calcular el min_id de cada grupo sin un JOIN
    # adicional, de modo que la subquery se evalúa una sola vez.
    n_returns = conn.execute(text("""
        SELECT COUNT(*) FROM public.return_item ri
        WHERE ri.sale_item_id IN (
            SELECT sale_item_id FROM public.sale_item
            WHERE sale_item_id NOT IN (
                SELECT MIN(sale_item_id)
                FROM public.sale_item
                GROUP BY sale_id, product_id, quantity, unit_price, offer_id, subtotal
            )
        )
    """)).scalar()

    log(f"D02 — return_items que apuntan a copias: {n_returns}")

    if n_returns > 0:
        conn.execute(text("""
            UPDATE public.return_item ri
            SET sale_item_id = keeper.min_id
            FROM (
                SELECT
                    sale_item_id AS old_id,
                    MIN(sale_item_id) OVER (
                        PARTITION BY sale_id, product_id, quantity,
                                     unit_price, offer_id, subtotal
                    ) AS min_id
                FROM public.sale_item
            ) keeper
            WHERE ri.sale_item_id = keeper.old_id
              AND keeper.old_id  != keeper.min_id
        """))
        log(f"D02 — {n_returns} return_item(s) redirigidos al sale_item_id superviviente.")

    # Paso 2: eliminar las copias (la FK ya no bloquea).
    conn.execute(text("""
        DELETE FROM public.sale_item
        WHERE sale_item_id NOT IN (
            SELECT MIN(sale_item_id)
            FROM public.sale_item
            GROUP BY sale_id, product_id, quantity, unit_price, offer_id, subtotal
        )
    """))

    n_despues = conn.execute(text("SELECT COUNT(*) FROM public.sale_item")).scalar()
    log(f"D02 — Eliminadas {n_duplicadas} fila(s). Filas restantes: {n_despues:,}")


# ─────────────────────────────────────────────────────────────────────────────
# D03 — Recalcular sale.total
# ─────────────────────────────────────────────────────────────────────────────

def d03_recalcular_sale_total(conn):
    """
    Recalcula sale.total para las ventas donde difiere de SUM(sale_item.subtotal).

    Decisión D03: la cabecera de venta es un campo derivado; los ítems son
    la fuente de verdad. Se encontró 1 venta con total incorrecto.
    """
    log("D03 — Comprobando coherencia de sale.total vs SUM(subtotales)...")

    # Identificar las ventas afectadas para loguearlas antes de corregir
    ventas_mal = conn.execute(text("""
        SELECT s.sale_id,
               s.total                                        AS total_actual,
               COALESCE(SUM(si.subtotal), 0)                 AS total_correcto,
               s.total - COALESCE(SUM(si.subtotal), 0)       AS desviacion
        FROM public.sale s
        LEFT JOIN public.sale_item si ON si.sale_id = s.sale_id
        GROUP BY s.sale_id, s.total
        HAVING ABS(s.total - COALESCE(SUM(si.subtotal), 0)) > 0.01
        ORDER BY ABS(s.total - COALESCE(SUM(si.subtotal), 0)) DESC
    """)).fetchall()

    if not ventas_mal:
        log("D03 — Todos los totales son correctos. Nada que hacer.")
        return

    log(f"D03 — {len(ventas_mal)} venta(s) con total incorrecto:")
    for fila in ventas_mal:
        log(f"       sale_id={fila[0]}  total_actual={fila[1]:.2f}  "
            f"correcto={fila[2]:.2f}  desviación={fila[3]:+.2f}")

    conn.execute(text("""
        UPDATE public.sale s
        SET total = COALESCE(
            (SELECT SUM(si.subtotal) FROM public.sale_item si WHERE si.sale_id = s.sale_id),
            0
        )
        WHERE ABS(s.total - COALESCE(
            (SELECT SUM(si.subtotal) FROM public.sale_item si WHERE si.sale_id = s.sale_id),
            0
        )) > 0.01
    """))

    log(f"D03 — {len(ventas_mal)} venta(s) corregida(s).")


# ─────────────────────────────────────────────────────────────────────────────
# D05 — Insertar product_id=29 en central_product
# ─────────────────────────────────────────────────────────────────────────────

def d05_insertar_product29_central_product(conn):
    """
    Inserta product_id=29 ("Sensor temperatura inteligente", Xiaomi, 19,99€)
    en central_product si todavía no existe.

    Decisión D05:
    - category_id = 1 (Diagnóstico — "Productos de medición y monitoreo")
    - brand_id    = brand de Xiaomi si existe en la tabla brand, NULL si no
    - unit_cost   = mediana de los productos de category_id=1;
                    fallback: mediana global si la categoría tuviera < 1 producto
    - unit_price  = 19,99 (precio de la tabla product)
    """
    log("D05 — Comprobando si product_id=29 existe en central_product...")

    ya_existe = conn.execute(
        text("SELECT COUNT(*) FROM public.central_product WHERE product_id = 29")
    ).scalar()

    if ya_existe:
        log("D05 — product_id=29 ya está en central_product. Nada que hacer.")
        return

    # Mediana de unit_cost para category_id=1, con fallback a mediana global
    unit_cost = conn.execute(text("""
        SELECT COALESCE(
            (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unit_cost)
             FROM public.central_product
             WHERE category_id = 1),
            (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unit_cost)
             FROM public.central_product)
        )
    """)).scalar()

    # brand_id de Xiaomi (NULL si no existe en la tabla brand)
    brand_id = conn.execute(
        text("SELECT brand_id FROM public.brand WHERE LOWER(name) = 'xiaomi' LIMIT 1")
    ).scalar()

    log(f"D05 — unit_cost imputado (mediana categoría 1): {unit_cost:.4f}")
    log(f"D05 — brand_id Xiaomi: {brand_id if brand_id else 'NULL (no encontrado en brand)'}")

    conn.execute(text("""
        INSERT INTO public.central_product
            (product_id, name, category_id, brand_id, sku, barcode, unit_cost, unit_price)
        SELECT
            29,
            p.name,
            1,
            :brand_id,
            NULL,
            NULL,
            :unit_cost,
            p.price
        FROM public.product p
        WHERE p.product_id = 29
    """), {"brand_id": brand_id, "unit_cost": unit_cost})

    # Verificación
    insertado = conn.execute(text("""
        SELECT product_id, name, category_id, brand_id, unit_cost, unit_price
        FROM public.central_product WHERE product_id = 29
    """)).fetchone()

    log(f"D05 — Insertado: product_id={insertado[0]}, nombre='{insertado[1]}', "
        f"category_id={insertado[2]}, brand_id={insertado[3]}, "
        f"unit_cost={insertado[4]}, unit_price={insertado[5]}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("INICIO LIMPIEZA — saleshealth / schema public")
    log("=" * 60)

    engine = get_engine()

    # Cada corrección es una transacción independiente.
    # Si una falla, las anteriores ya están confirmadas y el re-run
    # las omite gracias a la idempotencia.

    with engine.begin() as conn:
        d02_deduplicar_sale_item(conn)

    with engine.begin() as conn:
        d03_recalcular_sale_total(conn)

    with engine.begin() as conn:
        d05_insertar_product29_central_product(conn)

    log("=" * 60)
    log("LIMPIEZA COMPLETADA")
    log("=" * 60)


if __name__ == "__main__":
    main()
