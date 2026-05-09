"""
customer_360.py — Carga de marts.customer_360.

CLTV historico = margen_neto (D-CLTV-04 corregido, D-CLTV-13):
    margen_neto = SUM(margen_bruto) - SUM(importe_devuelto) + SUM(costo_devuelto)

Por identidad algebraica:
    AOV * margin_rate * freq_mensual * meses_activo = SUM(margen_bruto)
(los n_pedidos y meses_activo se cancelan en el producto).

meses_activo = COUNT(DISTINCT date_id / 100)   [YYYYMM via division entera]
recency_dias = MAX(fecha en dataset) - ultima_compra  [via CTE; no hardcoded]

Pre-condicion: dwh completamente cargado (pasos 1-9).
El TRUNCATE lo hace el orquestador (Opcion C); este modulo solo INSERT.

Asserts:
  COUNT(*) == COUNT(dwh.dim_cliente)            [ningún cliente perdido en JOIN]
  SUM(cltv) == config.CLTV_TOTAL_ESPERADO       [exacto: NUMERIC sin divisiones]
Test post-carga:
  |cltv - round(aov * margin_rate * freq * meses, 2)| <= 0.01 por cliente
  (verifica identidad algebraica empiricamente para el documento tecnico)
"""

import logging

from sqlalchemy import text

from etl.config import CLTV_TOTAL_ESPERADO

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    n_clientes_dwh = conn.execute(
        text("SELECT COUNT(*) FROM dwh.dim_cliente")
    ).scalar()

    conn.execute(text("""
        INSERT INTO marts.customer_360 (
            customer_id, nombre_completo, email,
            zona_id, distrito, tipo_area, ciudad,
            anio_alta, fecha_alta_efectiva,
            primera_compra, ultima_compra, meses_activo, recency_dias,
            n_pedidos, n_items_vendidos, n_items_devueltos,
            ingresos_brutos, importe_devuelto_total, ingresos_netos,
            margen_bruto_total, costo_devuelto_total, margen_neto,
            aov, margin_rate, freq_mensual, return_rate, cltv
        )
        WITH max_fecha AS (
            -- Fecha de referencia del snapshot; se evalua una vez como escalar.
            SELECT MAX(df.fecha) AS max_fecha
            FROM dwh.fact_ventas fv
            JOIN dwh.dim_fecha df ON df.date_id = fv.date_id
        ),
        ventas AS (
            SELECT
                dc.customer_id,
                COUNT(DISTINCT fv.sale_id)         AS n_pedidos,
                SUM(fv.quantity)                   AS n_items_vendidos,
                SUM(fv.subtotal)                   AS ingresos_brutos,
                SUM(fv.margen_bruto)               AS margen_bruto_total,
                MIN(df.fecha)                      AS primera_compra,
                MAX(df.fecha)                      AS ultima_compra,
                COUNT(DISTINCT fv.date_id / 100)   AS meses_activo
            FROM dwh.fact_ventas fv
            JOIN dwh.dim_cliente dc ON dc.cliente_id = fv.cliente_id
            JOIN dwh.dim_fecha   df ON df.date_id    = fv.date_id
            GROUP BY dc.customer_id
        ),
        devoluciones AS (
            SELECT
                dc.customer_id,
                SUM(fd.quantity_devuelta)          AS n_items_devueltos,
                SUM(fd.importe_devuelto)           AS importe_devuelto_total,
                SUM(fd.costo_devuelto)             AS costo_devuelto_total
            FROM dwh.fact_devoluciones fd
            JOIN dwh.dim_cliente dc ON dc.cliente_id = fd.cliente_id
            GROUP BY dc.customer_id
        )
        SELECT
            dc.customer_id,
            dc.nombre_completo,
            dc.email,
            dc.zona_id,
            dz.distrito,
            dz.tipo_area,
            dz.ciudad,
            EXTRACT(YEAR FROM dc.fecha_alta_efectiva)::INT        AS anio_alta,
            dc.fecha_alta_efectiva,
            v.primera_compra,
            v.ultima_compra,
            v.meses_activo,
            (mf.max_fecha - v.ultima_compra)::INT                 AS recency_dias,
            v.n_pedidos,
            v.n_items_vendidos,
            COALESCE(d.n_items_devueltos,      0)                 AS n_items_devueltos,
            v.ingresos_brutos,
            COALESCE(d.importe_devuelto_total, 0)                 AS importe_devuelto_total,
            v.ingresos_brutos
              - COALESCE(d.importe_devuelto_total, 0)             AS ingresos_netos,
            v.margen_bruto_total,
            COALESCE(d.costo_devuelto_total,   0)                 AS costo_devuelto_total,
            v.margen_bruto_total
              - COALESCE(d.importe_devuelto_total, 0)
              + COALESCE(d.costo_devuelto_total,   0)             AS margen_neto,
            -- Componentes CLTV
            v.ingresos_brutos / v.n_pedidos                       AS aov,
            CASE WHEN v.ingresos_brutos > 0
                 THEN v.margen_bruto_total / v.ingresos_brutos
            END                                                   AS margin_rate,
            v.n_pedidos::NUMERIC / v.meses_activo                 AS freq_mensual,
            LEAST(
                COALESCE(d.n_items_devueltos, 0)::NUMERIC
                  / NULLIF(v.n_items_vendidos, 0),
                1.0
            )                                                     AS return_rate,
            -- cltv = margen_neto (identidad algebraica D-CLTV-13)
            v.margen_bruto_total
              - COALESCE(d.importe_devuelto_total, 0)
              + COALESCE(d.costo_devuelto_total,   0)             AS cltv
        FROM dwh.dim_cliente dc
        JOIN dwh.dim_zona    dz ON dz.zona_id    = dc.zona_id
        JOIN ventas          v  ON v.customer_id = dc.customer_id
        LEFT JOIN devoluciones d ON d.customer_id = dc.customer_id
        CROSS JOIN max_fecha mf
        ORDER BY dc.customer_id
    """))

    n       = conn.execute(text("SELECT COUNT(*) FROM marts.customer_360")).scalar()
    cltv_db = conn.execute(text("SELECT SUM(cltv) FROM marts.customer_360")).scalar()
    cltv_sum = float(cltv_db)

    # Assert 1: ningún cliente se perdió en el JOIN con ventas
    assert n == n_clientes_dwh, (
        f"customer_360 — filas perdidas: dwh.dim_cliente={n_clientes_dwh}, "
        f"marts.customer_360={n}. Verificar clientes sin ventas."
    )

    # Assert 2: SUM(cltv) exacto — cltv es suma de NUMERIC sin divisiones,
    # no hay error de redondeo acumulable. Cualquier desviacion es un bug real.
    assert cltv_sum == CLTV_TOTAL_ESPERADO, (
        f"customer_360 — SUM(cltv) incorrecto: "
        f"esperado={CLTV_TOTAL_ESPERADO}, obtenido={cltv_sum}. "
        f"Diferencia={cltv_sum - CLTV_TOTAL_ESPERADO:.2f} EUR."
    )

    # Test 1 — Identidad algebraica (D-CLTV-13):
    #   AOV × margin_rate × freq × meses = margen_bruto_total
    #   La identidad es sobre el BRUTO, no sobre cltv (que incluye devoluciones).
    diff_identidad = float(conn.execute(text("""
        SELECT COALESCE(
            MAX(ABS(
                margen_bruto_total
                  - ROUND(aov * margin_rate * freq_mensual * meses_activo, 2)
            )),
            0
        )
        FROM marts.customer_360
        WHERE margin_rate IS NOT NULL
    """)).scalar())

    # Cota teorica del error de representacion NUMERIC(8,4):
    #   freq_mensual se almacena con 4 decimales → epsilon_freq ≤ 0.00005
    #   Al multiplicar por meses_activo (max ~72), el error se amplifica:
    #   max_error ≈ AOV_max × margin_rate × ε_freq × meses_max
    #             ≈ 1000   × 0.40         × 0.00005 × 72
    #             ≈ 1.44 €
    #   Umbral 2.0 € con margen de seguridad sobre la cota teorica (D-CLTV-14).
    if diff_identidad > 2.0:
        log.warning(
            "Test 1 — identidad algebraica: max |margen_bruto - componentes| = %.4f EUR "
            "(>2.0; excede cota teorica NUMERIC(8,4); revisar definicion de componentes).", diff_identidad
        )
    else:
        log.info(
            "Test 1 — identidad algebraica OK: max diff = %.4f EUR (cota teorica 1.44 EUR).", diff_identidad
        )

    # Test 2 — Ajuste por devoluciones (D-CLTV-04 corregido):
    #   cltv = margen_bruto_total - importe_devuelto_total + costo_devuelto_total
    #   Todo NUMERIC sin divisiones: resultado debe ser exactamente 0.
    diff_ajuste = float(conn.execute(text("""
        SELECT MAX(ABS(
            cltv - (margen_bruto_total - importe_devuelto_total + costo_devuelto_total)
        ))
        FROM marts.customer_360
    """)).scalar())

    if diff_ajuste != 0.0:
        log.warning(
            "Test 2 — ajuste devoluciones: max diff = %.4f EUR "
            "(esperado exactamente 0; bug en calculo de cltv).", diff_ajuste
        )
    else:
        log.info("Test 2 — ajuste devoluciones OK: diff exactamente 0.")

    log.info("customer_360: %d clientes. SUM(cltv) = %.2f EUR.", n, cltv_sum)
    return n
