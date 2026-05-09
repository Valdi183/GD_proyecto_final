-- marts_schema.sql — DDL del schema de data marts.
--
-- Schema marts: tablas derivadas pre-agregadas orientadas a análisis y ML.
-- Doctrina Kimball: dwh contiene hechos/dimensiones atómicos;
-- marts contiene vistas materializadas para consumo (BI, clustering, reportes).
--
-- Uso:
--   psql -U postgres -d saleshealth -f src/etl/sql/marts_schema.sql

CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS marts.customer_360;

CREATE TABLE marts.customer_360 (

    -- ── Identidad ─────────────────────────────────────────────────────────
    customer_id              INT           NOT NULL,
    nombre_completo          VARCHAR(300),
    email                    VARCHAR(200),

    -- ── Dimensión geográfica (desnormalizada de dwh.dim_zona) ─────────────
    zona_id                  BIGINT        NOT NULL,
    distrito                 VARCHAR(100),
    tipo_area                VARCHAR(50),
    ciudad                   VARCHAR(100),

    -- ── Cohorte ───────────────────────────────────────────────────────────
    anio_alta                INT           NOT NULL,
    fecha_alta_efectiva      DATE          NOT NULL,

    -- ── Métricas temporales ───────────────────────────────────────────────
    primera_compra           DATE          NOT NULL,
    ultima_compra            DATE          NOT NULL,
    -- meses_activo = COUNT(DISTINCT YYYYMM de pedidos); mínimo 1 (D-CLTV-10).
    -- Se calcula como COUNT(DISTINCT date_id / 100): división entera da YYYYMM.
    meses_activo             INT           NOT NULL,
    -- recency_dias = MAX(fecha en el dataset) - ultima_compra.
    -- Referencia fija al snapshot: no varía al re-ejecutar en fechas futuras.
    recency_dias             INT           NOT NULL,

    -- ── Volúmenes ─────────────────────────────────────────────────────────
    n_pedidos                INT           NOT NULL,
    n_items_vendidos         INT           NOT NULL,
    n_items_devueltos        INT           NOT NULL,

    -- ── Económicas ────────────────────────────────────────────────────────
    ingresos_brutos          NUMERIC(14,2) NOT NULL,
    importe_devuelto_total   NUMERIC(14,2) NOT NULL,
    ingresos_netos           NUMERIC(14,2) NOT NULL,
    margen_bruto_total       NUMERIC(14,2) NOT NULL,
    costo_devuelto_total     NUMERIC(14,2) NOT NULL,
    -- margen_neto = margen_bruto_total - importe_devuelto_total + costo_devuelto_total
    -- (D-CLTV-04 corregido: sustrae el margen perdido en devoluciones,
    --  no el coste; verificado con ejemplo unitario precio=100/costo=60/dev total)
    margen_neto              NUMERIC(14,2) NOT NULL,

    -- ── Componentes CLTV (D-CLTV-06 a D-CLTV-09) ────────────────────────
    -- aov = ingresos_brutos / n_pedidos (bruto; returns ajustados en margen_neto)
    aov                      NUMERIC(10,2) NOT NULL,
    -- margin_rate = margen_bruto_total / ingresos_brutos (ratio SUM/SUM, ponderado)
    -- NULL teóricamente si ingresos_brutos = 0; imposible en este dataset porque
    -- todo sale_item tiene subtotal > 0 por constraint CHECK. Nullable por defensa.
    margin_rate              NUMERIC(7,4),
    -- freq_mensual = n_pedidos / meses_activo
    freq_mensual             NUMERIC(8,4)  NOT NULL,
    -- return_rate = LEAST(n_items_devueltos / n_items_vendidos, 1.0) (D-CLTV-11)
    return_rate              NUMERIC(7,4)  NOT NULL,

    -- ── CLTV (D-CLTV-13) ─────────────────────────────────────────────────
    -- cltv = margen_neto (identidad algebraica: AOV × margin_rate × freq × meses
    --        simplifica a SUM(margen_bruto) tras cancelación de n y meses_activo)
    -- Se calcula directamente como diferencia de sumas NUMERIC para evitar
    -- acumulación de errores de redondeo en divisiones intermedias.
    cltv                     NUMERIC(14,2) NOT NULL,

    -- ── Clustering — Fase 6 (D-CLU-08) ─────────────────────────────
    -- Asignados por 06_clustering.ipynb; NULL hasta que se ejecute S6.
    cluster_id               INT,
    cluster_label            VARCHAR(50),

    -- ── Control ───────────────────────────────────────────────────────────
    calculado_en             TIMESTAMP     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_customer_360 PRIMARY KEY (customer_id)
);

COMMENT ON TABLE marts.customer_360 IS
    'Una fila por cliente (5750). CLTV historico = margen_neto (D-CLTV-13). '
    'Componentes AOV/freq_mensual/meses_activo/margin_rate son features para Fase 6 (PCA + clustering). '
    'No tiene FK formales al DWH (tabla desnormalizada de analisis).';

COMMENT ON COLUMN marts.customer_360.margin_rate IS
    'Nullable por diseno defensivo; en este dataset nunca es NULL porque '
    'ingresos_brutos > 0 para todo cliente (todos tienen al menos un sale_item con subtotal > 0).';

COMMENT ON COLUMN marts.customer_360.meses_activo IS
    'COUNT(DISTINCT date_id / 100): cuenta meses calendario distintos con compras. '
    'Un cliente con compras en 31-ene y 1-feb tiene meses_activo=2. Minimo 1 (D-CLTV-10).';

COMMENT ON COLUMN marts.customer_360.cltv IS
    'CLTV historico ajustado por devoluciones (D-CLTV-04). '
    'El componente margen_bruto_total satisface la identidad algebraica: '
    'AOV * margin_rate * freq_mensual * meses_activo = margen_bruto_total. '
    'Ajuste por devoluciones: cltv = margen_bruto_total - importe_devuelto_total + costo_devuelto_total.';
