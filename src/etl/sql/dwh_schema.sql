-- =============================================================================
-- dwh_schema.sql — Esquema estrella saleshealth (Kimball, SCD tipo 1)
-- Fase 3 — Modelo Dimensional
--
-- Uso (desde GD_proyecto_final/):
--   psql -U <user> -d <db> -f src/etl/sql/dwh_schema.sql
--
-- Idempotente: DROP IF EXISTS en orden inverso + ON CONFLICT en sentinels.
-- NO ejecutar con datos cargados: DROP borra todo el contenido del DWH.
-- =============================================================================

\set ON_ERROR_STOP on

-- ── Schema ────────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS dwh;

-- ── Drop en orden inverso de dependencias (hechos → dims con FK → dims base) ─
DROP TABLE IF EXISTS dwh.fact_devoluciones CASCADE;
DROP TABLE IF EXISTS dwh.fact_ventas        CASCADE;
DROP TABLE IF EXISTS dwh.dim_cliente        CASCADE;
DROP TABLE IF EXISTS dwh.dim_tienda         CASCADE;
DROP TABLE IF EXISTS dwh.dim_producto       CASCADE;
DROP TABLE IF EXISTS dwh.dim_motivo         CASCADE;
DROP TABLE IF EXISTS dwh.dim_oferta         CASCADE;
DROP TABLE IF EXISTS dwh.dim_zona           CASCADE;
DROP TABLE IF EXISTS dwh.dim_fecha          CASCADE;

-- =============================================================================
-- DIMENSIONES
-- Surrogate keys:
--   dim_fecha       → INT YYYYMMDD (smart key Kimball, legible sin JOIN)
--   resto de dims   → BIGINT GENERATED ALWAYS AS IDENTITY
-- =============================================================================

-- ── dim_fecha ─────────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_fecha (
    date_id          INT         NOT NULL,
    fecha            DATE        NOT NULL,
    anio             INT         NOT NULL,
    semestre         INT         NOT NULL,
    trimestre        INT         NOT NULL,
    mes              INT         NOT NULL,
    nombre_mes       VARCHAR(20) NOT NULL,
    semana_anio      INT         NOT NULL,
    dia_semana       INT         NOT NULL,  -- 1=lunes, 7=domingo (ISO 8601)
    nombre_dia       VARCHAR(15) NOT NULL,
    es_fin_de_semana BOOLEAN     NOT NULL,
    es_dia_habil     BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_fecha           PRIMARY KEY (date_id),
    CONSTRAINT ck_dim_fecha_semestre  CHECK (semestre    IN (1, 2)),
    CONSTRAINT ck_dim_fecha_trimestre CHECK (trimestre   BETWEEN 1 AND 4),
    CONSTRAINT ck_dim_fecha_mes       CHECK (mes         BETWEEN 1 AND 12),
    CONSTRAINT ck_dim_fecha_semana    CHECK (semana_anio BETWEEN 1 AND 53),
    CONSTRAINT ck_dim_fecha_dia       CHECK (dia_semana  BETWEEN 1 AND 7)
);

COMMENT ON TABLE  dwh.dim_fecha IS
    'Dimension temporal; rango 2020-01-01 a 2027-12-31; generada sinteticamente en ETL';
COMMENT ON COLUMN dwh.dim_fecha.date_id IS
    'Smart key YYYYMMDD: 20240315 = 15 mar 2024; INT por convencion Kimball; FK en hechos es INT';
COMMENT ON COLUMN dwh.dim_fecha.dia_semana IS
    '1 = lunes ... 7 = domingo (ISO 8601)';
COMMENT ON COLUMN dwh.dim_fecha.es_dia_habil IS
    'TRUE si lunes-viernes; complementario a es_fin_de_semana; sin festivos (no modelados)';

-- ── dim_zona ──────────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_zona (
    zona_id      BIGINT GENERATED ALWAYS AS IDENTITY,
    postal_code  VARCHAR(10)  NOT NULL,
    distrito     VARCHAR(100) NOT NULL,
    tipo_area    VARCHAR(50),
    orientacion  VARCHAR(50),
    ciudad       VARCHAR(100) NOT NULL DEFAULT 'Madrid',
    CONSTRAINT pk_dim_zona             PRIMARY KEY (zona_id),
    CONSTRAINT uq_dim_zona_postal_code UNIQUE      (postal_code)
);

COMMENT ON TABLE dwh.dim_zona IS
    'Dimension geografica; 42 zonas postales de Madrid; '
    'referenciada por dim_tienda (zona_tienda) y dim_cliente (zona_predominante)';

-- ── dim_oferta ────────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_oferta (
    oferta_id     BIGINT GENERATED ALWAYS AS IDENTITY,
    offer_id      INT,                        -- NK; -1 en sentinel
    nombre        VARCHAR(200) NOT NULL,
    descuento_pct NUMERIC(5,2),
    fecha_inicio  DATE,
    fecha_fin     DATE,
    CONSTRAINT pk_dim_oferta            PRIMARY KEY (oferta_id),
    CONSTRAINT uq_dim_oferta_offer_id  UNIQUE      (offer_id),
    CONSTRAINT ck_dim_oferta_descuento CHECK (descuento_pct IS NULL
                                           OR descuento_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_dim_oferta_fechas    CHECK (fecha_fin IS NULL
                                           OR fecha_fin >= fecha_inicio)
);

COMMENT ON TABLE  dwh.dim_oferta IS
    'Dimension oferta; 1 oferta real + sentinel oferta_id=0; FK NOT NULL en hechos';
COMMENT ON COLUMN dwh.dim_oferta.oferta_id IS
    'oferta_id=0 = sentinel "Sin oferta"; permite FK NOT NULL en fact_ventas y fact_devoluciones';

-- ── dim_motivo ────────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_motivo (
    motivo_id   BIGINT GENERATED ALWAYS AS IDENTITY,
    reason_id   INT,                           -- NK; -1 en sentinel
    descripcion TEXT,
    es_activo   BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_dim_motivo              PRIMARY KEY (motivo_id),
    CONSTRAINT uq_dim_motivo_reason_id    UNIQUE      (reason_id)
);

COMMENT ON TABLE  dwh.dim_motivo IS
    'Dimension motivo de devolucion; 6 motivos reales + sentinel motivo_id=0';
COMMENT ON COLUMN dwh.dim_motivo.motivo_id IS
    'motivo_id=0 = sentinel "Motivo no registrado"; permite FK NOT NULL en fact_devoluciones';

-- ── dim_producto ──────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_producto (
    producto_id    BIGINT GENERATED ALWAYS AS IDENTITY,
    product_id     INT          NOT NULL,      -- NK
    nombre         VARCHAR(200) NOT NULL,
    categoria      VARCHAR(100),
    marca          VARCHAR(100),
    sku            VARCHAR(100),
    precio_lista   NUMERIC(10,2),
    costo_unitario NUMERIC(10,2),
    CONSTRAINT pk_dim_producto            PRIMARY KEY (producto_id),
    CONSTRAINT uq_dim_producto_product_id UNIQUE      (product_id)
);

COMMENT ON TABLE  dwh.dim_producto IS
    'Dimension producto; desnormalizada (estrella): '
    'une public.product + central_product + brand + category';
COMMENT ON COLUMN dwh.dim_producto.costo_unitario IS
    'De central_product.unit_cost; cobertura 100% tras correccion D05 (Fase 1)';

-- ── dim_tienda ────────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_tienda (
    tienda_id      BIGINT GENERATED ALWAYS AS IDENTITY,
    store_id       INT          NOT NULL,      -- NK
    nombre         VARCHAR(200) NOT NULL,
    ciudad         VARCHAR(100),
    fecha_apertura DATE,
    latitud        NUMERIC(9,6),
    longitud       NUMERIC(9,6),
    zona_id        BIGINT       NOT NULL,
    CONSTRAINT pk_dim_tienda           PRIMARY KEY (tienda_id),
    CONSTRAINT uq_dim_tienda_store_id  UNIQUE      (store_id),
    CONSTRAINT fk_dim_tienda_zona      FOREIGN KEY (zona_id)
                                       REFERENCES  dwh.dim_zona (zona_id)
);

COMMENT ON TABLE  dwh.dim_tienda IS
    'Dimension tienda; SCD tipo 1; zona_id = FK a dim_zona via postal_code (ETL)';

-- ── dim_cliente ───────────────────────────────────────────────────────────────
CREATE TABLE dwh.dim_cliente (
    cliente_id          BIGINT GENERATED ALWAYS AS IDENTITY,
    customer_id         INT          NOT NULL,  -- NK
    nombre_completo     VARCHAR(300),
    email               VARCHAR(200),
    telefono            VARCHAR(50),
    fecha_alta_efectiva DATE,
    zona_id             BIGINT       NOT NULL,
    CONSTRAINT pk_dim_cliente             PRIMARY KEY (cliente_id),
    CONSTRAINT uq_dim_cliente_customer_id UNIQUE      (customer_id),
    CONSTRAINT fk_dim_cliente_zona        FOREIGN KEY (zona_id)
                                          REFERENCES  dwh.dim_zona (zona_id)
);

COMMENT ON TABLE  dwh.dim_cliente IS
    'Dimension cliente; SCD tipo 1; 5750 clientes; zona_predominante calculada en ETL';
COMMENT ON COLUMN dwh.dim_cliente.fecha_alta_efectiva IS
    'MIN(sale.sale_date) por cliente; customer.created_at no es fiable (timestamp de carga, D06)';
COMMENT ON COLUMN dwh.dim_cliente.zona_id IS
    'Zona predominante: moda de distrito por compras; '
    'desempate caso 2: primera compra; caso 3: menor postal_code (D-M03b)';

-- =============================================================================
-- HECHOS
-- =============================================================================

-- ── fact_ventas ───────────────────────────────────────────────────────────────
CREATE TABLE dwh.fact_ventas (
    venta_id     BIGINT GENERATED ALWAYS AS IDENTITY,
    date_id      INT           NOT NULL,
    cliente_id   BIGINT        NOT NULL,
    producto_id  BIGINT        NOT NULL,
    tienda_id    BIGINT        NOT NULL,
    oferta_id    BIGINT        NOT NULL,       -- NOT NULL: sentinel oferta_id=0
    sale_id      INT           NOT NULL,       -- DD: rastro al pedido operacional
    sale_item_id INT           NOT NULL,       -- DD: rastro a la linea operacional
    quantity     INT           NOT NULL,
    unit_price   NUMERIC(10,2) NOT NULL,
    unit_cost    NUMERIC(10,2),
    subtotal     NUMERIC(12,2) NOT NULL,
    margen_bruto NUMERIC(12,2),
    CONSTRAINT pk_fact_ventas          PRIMARY KEY (venta_id),
    CONSTRAINT fk_fact_ventas_fecha    FOREIGN KEY (date_id)    REFERENCES dwh.dim_fecha   (date_id),
    CONSTRAINT fk_fact_ventas_cliente  FOREIGN KEY (cliente_id) REFERENCES dwh.dim_cliente (cliente_id),
    CONSTRAINT fk_fact_ventas_producto FOREIGN KEY (producto_id)REFERENCES dwh.dim_producto(producto_id),
    CONSTRAINT fk_fact_ventas_tienda   FOREIGN KEY (tienda_id)  REFERENCES dwh.dim_tienda  (tienda_id),
    CONSTRAINT fk_fact_ventas_oferta   FOREIGN KEY (oferta_id)  REFERENCES dwh.dim_oferta  (oferta_id),
    CONSTRAINT ck_fact_ventas_quantity CHECK (quantity  > 0),
    CONSTRAINT ck_fact_ventas_subtotal CHECK (subtotal >= 0)
);

COMMENT ON TABLE  dwh.fact_ventas IS
    'Hecho ventas; grano: linea de sale_item (42313 filas tras limpieza); '
    'medidas aditivas: quantity, subtotal, margen_bruto';
COMMENT ON COLUMN dwh.fact_ventas.sale_id IS
    'DD: rastro al pedido en public.sale; no es FK del DWH';
COMMENT ON COLUMN dwh.fact_ventas.sale_item_id IS
    'DD: rastro a la linea en public.sale_item; no es FK del DWH';
COMMENT ON COLUMN dwh.fact_ventas.unit_cost IS
    'Coste unitario de central_product en el momento de carga ETL; NULL si no habia entrada';
COMMENT ON COLUMN dwh.fact_ventas.margen_bruto IS
    'subtotal - (quantity * unit_cost); aditiva: SUM() valido en cualquier nivel';

-- Indices en FKs de fact_ventas (PostgreSQL no los crea automaticamente)
CREATE INDEX idx_fv_date_id      ON dwh.fact_ventas (date_id);
CREATE INDEX idx_fv_cliente_id   ON dwh.fact_ventas (cliente_id);
CREATE INDEX idx_fv_producto_id  ON dwh.fact_ventas (producto_id);
CREATE INDEX idx_fv_tienda_id    ON dwh.fact_ventas (tienda_id);
CREATE INDEX idx_fv_oferta_id    ON dwh.fact_ventas (oferta_id);
-- Indices en DDs para joins de trazabilidad operacional
CREATE INDEX idx_fv_sale_id      ON dwh.fact_ventas (sale_id);
CREATE INDEX idx_fv_sale_item_id ON dwh.fact_ventas (sale_item_id);

-- ── fact_devoluciones ─────────────────────────────────────────────────────────
CREATE TABLE dwh.fact_devoluciones (
    devolucion_id     BIGINT GENERATED ALWAYS AS IDENTITY,
    return_date_id    INT           NOT NULL,  -- role: fecha de devolucion
    venta_date_id     INT           NOT NULL,  -- role: fecha de la venta original
    cliente_id        BIGINT        NOT NULL,
    producto_id       BIGINT        NOT NULL,
    tienda_id         BIGINT        NOT NULL,
    oferta_id         BIGINT        NOT NULL,  -- NOT NULL: sentinel oferta_id=0
    motivo_id         BIGINT        NOT NULL,  -- NOT NULL: sentinel motivo_id=0
    sale_item_id      INT           NOT NULL,  -- DD: rastro al item devuelto
    return_id         INT           NOT NULL,  -- DD: rastro a la devolucion
    quantity_devuelta INT           NOT NULL,
    importe_devuelto  NUMERIC(12,2) NOT NULL,
    costo_devuelto    NUMERIC(12,2),
    CONSTRAINT pk_fact_devoluciones          PRIMARY KEY (devolucion_id),
    CONSTRAINT fk_fact_dev_fecha_return      FOREIGN KEY (return_date_id) REFERENCES dwh.dim_fecha   (date_id),
    CONSTRAINT fk_fact_dev_fecha_venta       FOREIGN KEY (venta_date_id)  REFERENCES dwh.dim_fecha   (date_id),
    CONSTRAINT fk_fact_dev_cliente           FOREIGN KEY (cliente_id)     REFERENCES dwh.dim_cliente (cliente_id),
    CONSTRAINT fk_fact_dev_producto          FOREIGN KEY (producto_id)    REFERENCES dwh.dim_producto(producto_id),
    CONSTRAINT fk_fact_dev_tienda            FOREIGN KEY (tienda_id)      REFERENCES dwh.dim_tienda  (tienda_id),
    CONSTRAINT fk_fact_dev_oferta            FOREIGN KEY (oferta_id)      REFERENCES dwh.dim_oferta  (oferta_id),
    CONSTRAINT fk_fact_dev_motivo            FOREIGN KEY (motivo_id)      REFERENCES dwh.dim_motivo  (motivo_id),
    CONSTRAINT ck_fact_dev_qty               CHECK (quantity_devuelta > 0),
    CONSTRAINT ck_fact_dev_importe           CHECK (importe_devuelto  >= 0)
);

COMMENT ON TABLE  dwh.fact_devoluciones IS
    'Hecho devoluciones; grano: linea de return_item (2330 filas); '
    'role-playing de dim_fecha: return_date_id + venta_date_id';
COMMENT ON COLUMN dwh.fact_devoluciones.return_date_id IS
    'Role-playing dim_fecha: fecha en que se proceso la devolucion (return_item.return_date)';
COMMENT ON COLUMN dwh.fact_devoluciones.venta_date_id IS
    'Role-playing dim_fecha: fecha de la venta original del item (sale.sale_date via sale_item)';
COMMENT ON COLUMN dwh.fact_devoluciones.sale_item_id IS
    'DD: rastro al item original en public.sale_item; permite JOIN operacional ad-hoc';
COMMENT ON COLUMN dwh.fact_devoluciones.return_id IS
    'DD: rastro a la devolucion en public.return_item';
COMMENT ON COLUMN dwh.fact_devoluciones.costo_devuelto IS
    'quantity_devuelta * unit_cost del item original; NULL si unit_cost era NULL';

-- Indices en FKs de fact_devoluciones
CREATE INDEX idx_fd_return_date_id ON dwh.fact_devoluciones (return_date_id);
CREATE INDEX idx_fd_venta_date_id  ON dwh.fact_devoluciones (venta_date_id);
CREATE INDEX idx_fd_cliente_id     ON dwh.fact_devoluciones (cliente_id);
CREATE INDEX idx_fd_producto_id    ON dwh.fact_devoluciones (producto_id);
CREATE INDEX idx_fd_tienda_id      ON dwh.fact_devoluciones (tienda_id);
CREATE INDEX idx_fd_oferta_id      ON dwh.fact_devoluciones (oferta_id);
CREATE INDEX idx_fd_motivo_id      ON dwh.fact_devoluciones (motivo_id);
-- Indices en DDs para joins de trazabilidad operacional
CREATE INDEX idx_fd_sale_item_id   ON dwh.fact_devoluciones (sale_item_id);
CREATE INDEX idx_fd_return_id      ON dwh.fact_devoluciones (return_id);

-- =============================================================================
-- SENTINEL ROWS
-- OVERRIDING SYSTEM VALUE permite insertar id=0 con GENERATED ALWAYS AS IDENTITY.
-- ON CONFLICT DO NOTHING garantiza idempotencia si el script se re-ejecuta
-- sin DROP (no es el caso normal, pero protege ejecuciones parciales).
-- =============================================================================

INSERT INTO dwh.dim_oferta
    (oferta_id, offer_id, nombre, descuento_pct, fecha_inicio, fecha_fin)
OVERRIDING SYSTEM VALUE
VALUES (0, -1, 'Sin oferta', NULL, NULL, NULL)
ON CONFLICT (oferta_id) DO NOTHING;

INSERT INTO dwh.dim_motivo
    (motivo_id, reason_id, descripcion, es_activo)
OVERRIDING SYSTEM VALUE
VALUES (0, -1, 'Motivo no registrado', FALSE)
ON CONFLICT (motivo_id) DO NOTHING;
