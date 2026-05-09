
# INFORME DE EXPLORACIÓN — saleshealth
================================================================================
Generado: 2026-05-07 11:54:44

Tablas en schema `public`: 17
`brand`, `category`, `central_inventory`, `central_product`, `city_zone`, `customer`, `inventory`, `offer`, `product`, `product_offer`, `return_item`, `return_reason`, `sale`, `sale_item`, `store`, `warehouse`, `warehouse_location`

# PASADA 1 — ESTRUCTURA DEL SCHEMA PUBLIC
================================================================================
Ejecutada: 2026-05-07 11:54:44

## 1.1 Columnas, tipos y nulabilidad
------------------------------------------------------------

### brand
| column_name   | data_type         | is_nullable   | column_default                          |   ordinal_position |
|:--------------|:------------------|:--------------|:----------------------------------------|-------------------:|
| brand_id      | integer           | NO            | nextval('brand_brand_id_seq'::regclass) |                  1 |
| name          | character varying | NO            |                                         |                  2 |
| country       | character varying | YES           |                                         |                  3 |
| website       | character varying | YES           |                                         |                  4 |

### category
| column_name   | data_type         | is_nullable   | column_default                                |   ordinal_position |
|:--------------|:------------------|:--------------|:----------------------------------------------|-------------------:|
| category_id   | integer           | NO            | nextval('category_category_id_seq'::regclass) |                  1 |
| name          | character varying | NO            |                                               |                  2 |
| description   | text              | YES           |                                               |                  3 |

### central_inventory
| column_name   | data_type                   | is_nullable   | column_default                                          |   ordinal_position |
|:--------------|:----------------------------|:--------------|:--------------------------------------------------------|-------------------:|
| inventory_id  | integer                     | NO            | nextval('central_inventory_inventory_id_seq'::regclass) |                  1 |
| warehouse_id  | integer                     | YES           |                                                         |                  2 |
| location_id   | integer                     | YES           |                                                         |                  3 |
| product_id    | integer                     | YES           |                                                         |                  4 |
| quantity      | integer                     | NO            | 0                                                       |                  5 |
| min_stock     | integer                     | YES           | 0                                                       |                  6 |
| max_stock     | integer                     | YES           | 0                                                       |                  7 |
| last_update   | timestamp without time zone | YES           | CURRENT_TIMESTAMP                                       |                  8 |

### central_product
| column_name   | data_type         | is_nullable   | column_default   |   ordinal_position |
|:--------------|:------------------|:--------------|:-----------------|-------------------:|
| product_id    | integer           | NO            |                  |                  1 |
| name          | character varying | NO            |                  |                  2 |
| category_id   | integer           | YES           |                  |                  3 |
| brand_id      | integer           | YES           |                  |                  4 |
| sku           | character varying | YES           |                  |                  5 |
| barcode       | character varying | YES           |                  |                  6 |
| unit_cost     | numeric           | YES           |                  |                  7 |
| unit_price    | numeric           | YES           |                  |                  8 |

### city_zone
| column_name      | data_type         | is_nullable   | column_default              |   ordinal_position |
|:-----------------|:------------------|:--------------|:----------------------------|-------------------:|
| postal_code      | character varying | NO            |                             |                  1 |
| district         | character varying | NO            |                             |                  2 |
| area_type        | character varying | YES           |                             |                  3 |
| zone_orientation | character varying | YES           |                             |                  4 |
| city_code        | character varying | YES           | 28                          |                  5 |
| city             | character varying | YES           | 'Madrid'::character varying |                  6 |

### customer
| column_name   | data_type                   | is_nullable   | column_default                                 |   ordinal_position |
|:--------------|:----------------------------|:--------------|:-----------------------------------------------|-------------------:|
| customer_id   | integer                     | NO            | nextval('customer_customer_id_seq1'::regclass) |                  1 |
| first_name    | character varying           | YES           |                                                |                  2 |
| last_name     | character varying           | YES           |                                                |                  3 |
| last_name2    | character varying           | YES           |                                                |                  4 |
| email         | character varying           | YES           |                                                |                  5 |
| phone         | character varying           | YES           |                                                |                  6 |
| created_at    | timestamp without time zone | YES           | CURRENT_TIMESTAMP                              |                  7 |

### inventory
| column_name   | data_type                   | is_nullable   | column_default                                  |   ordinal_position |
|:--------------|:----------------------------|:--------------|:------------------------------------------------|-------------------:|
| inventory_id  | integer                     | NO            | nextval('inventory_inventory_id_seq'::regclass) |                  1 |
| store_id      | integer                     | YES           |                                                 |                  2 |
| product_id    | integer                     | YES           |                                                 |                  3 |
| stock         | integer                     | YES           |                                                 |                  4 |
| last_update   | timestamp without time zone | YES           | CURRENT_TIMESTAMP                               |                  5 |

### offer
| column_name      | data_type         | is_nullable   | column_default                          |   ordinal_position |
|:-----------------|:------------------|:--------------|:----------------------------------------|-------------------:|
| offer_id         | integer           | NO            | nextval('offer_offer_id_seq'::regclass) |                  1 |
| name             | character varying | YES           |                                         |                  2 |
| description      | text              | YES           |                                         |                  3 |
| discount_percent | numeric           | YES           |                                         |                  4 |
| start_date       | date              | NO            |                                         |                  5 |
| end_date         | date              | NO            |                                         |                  6 |

### product
| column_name   | data_type                   | is_nullable   | column_default                              |   ordinal_position |
|:--------------|:----------------------------|:--------------|:--------------------------------------------|-------------------:|
| product_id    | integer                     | NO            | nextval('product_product_id_seq'::regclass) |                  1 |
| name          | character varying           | NO            |                                             |                  2 |
| category      | character varying           | YES           |                                             |                  3 |
| manufacturer  | character varying           | YES           |                                             |                  4 |
| price         | numeric                     | NO            |                                             |                  5 |
| created_at    | timestamp without time zone | YES           | CURRENT_TIMESTAMP                           |                  6 |

### product_offer
| column_name   | data_type   | is_nullable   | column_default   |   ordinal_position |
|:--------------|:------------|:--------------|:-----------------|-------------------:|
| product_id    | integer     | NO            |                  |                  1 |
| offer_id      | integer     | NO            |                  |                  2 |

### return_item
| column_name   | data_type                   | is_nullable   | column_default                                 |   ordinal_position |
|:--------------|:----------------------------|:--------------|:-----------------------------------------------|-------------------:|
| return_id     | integer                     | NO            | nextval('return_item_return_id_seq'::regclass) |                  1 |
| sale_item_id  | integer                     | YES           |                                                |                  2 |
| return_date   | timestamp without time zone | NO            |                                                |                  3 |
| quantity      | integer                     | NO            |                                                |                  4 |
| reason_id     | integer                     | YES           |                                                |                  5 |

### return_reason
| column_name   | data_type   | is_nullable   | column_default                                   |   ordinal_position |
|:--------------|:------------|:--------------|:-------------------------------------------------|-------------------:|
| reason_id     | integer     | NO            | nextval('return_reason_reason_id_seq'::regclass) |                  1 |
| reason        | text        | YES           |                                                  |                  2 |
| active        | boolean     | YES           | true                                             |                  3 |

### sale
| column_name   | data_type                   | is_nullable   | column_default                        |   ordinal_position |
|:--------------|:----------------------------|:--------------|:--------------------------------------|-------------------:|
| sale_id       | integer                     | NO            | nextval('sale_sale_id_seq'::regclass) |                  1 |
| customer_id   | integer                     | YES           |                                       |                  2 |
| store_id      | integer                     | YES           |                                       |                  3 |
| sale_date     | timestamp without time zone | NO            |                                       |                  4 |
| total         | numeric                     | YES           |                                       |                  5 |

### sale_item
| column_name   | data_type   | is_nullable   | column_default                                  |   ordinal_position |
|:--------------|:------------|:--------------|:------------------------------------------------|-------------------:|
| sale_item_id  | integer     | NO            | nextval('sale_item_sale_item_id_seq'::regclass) |                  1 |
| sale_id       | integer     | YES           |                                                 |                  2 |
| product_id    | integer     | YES           |                                                 |                  3 |
| quantity      | integer     | NO            |                                                 |                  4 |
| unit_price    | numeric     | NO            |                                                 |                  5 |
| offer_id      | integer     | YES           |                                                 |                  6 |
| subtotal      | numeric     | NO            |                                                 |                  7 |

### store
| column_name   | data_type         | is_nullable   | column_default                          |   ordinal_position |
|:--------------|:------------------|:--------------|:----------------------------------------|-------------------:|
| store_id      | integer           | NO            | nextval('store_store_id_seq'::regclass) |                  1 |
| name          | character varying | NO            |                                         |                  2 |
| address       | character varying | YES           |                                         |                  3 |
| city          | character varying | YES           | 'Madrid'::character varying             |                  4 |
| postal_code   | character varying | YES           |                                         |                  5 |
| latitude      | numeric           | YES           |                                         |                  6 |
| longitude     | numeric           | YES           |                                         |                  7 |
| opened_date   | date              | YES           | CURRENT_DATE                            |                  8 |

### warehouse
| column_name   | data_type         | is_nullable   | column_default                                  |   ordinal_position |
|:--------------|:------------------|:--------------|:------------------------------------------------|-------------------:|
| warehouse_id  | integer           | NO            | nextval('warehouse_warehouse_id_seq'::regclass) |                  1 |
| name          | character varying | NO            |                                                 |                  2 |
| address       | character varying | YES           |                                                 |                  3 |
| city          | character varying | YES           |                                                 |                  4 |
| postal_code   | character varying | YES           |                                                 |                  5 |
| latitude      | numeric           | YES           |                                                 |                  6 |
| longitude     | numeric           | YES           |                                                 |                  7 |

### warehouse_location
| column_name   | data_type         | is_nullable   | column_default                                          |   ordinal_position |
|:--------------|:------------------|:--------------|:--------------------------------------------------------|-------------------:|
| location_id   | integer           | NO            | nextval('warehouse_location_location_id_seq'::regclass) |                  1 |
| warehouse_id  | integer           | YES           |                                                         |                  2 |
| zone          | character varying | YES           |                                                         |                  3 |
| aisle         | character varying | YES           |                                                         |                  4 |
| shelf         | character varying | YES           |                                                         |                  5 |
| bin_code      | character varying | YES           |                                                         |                  6 |

## 1.2 Claves primarias declaradas
------------------------------------------------------------
| table_name         | pk_columns           |
|:-------------------|:---------------------|
| brand              | brand_id             |
| category           | category_id          |
| central_inventory  | inventory_id         |
| central_product    | product_id           |
| city_zone          | postal_code          |
| customer           | customer_id          |
| inventory          | inventory_id         |
| offer              | offer_id             |
| product            | product_id           |
| product_offer      | product_id, offer_id |
| return_item        | return_id            |
| return_reason      | reason_id            |
| sale               | sale_id              |
| sale_item          | sale_item_id         |
| store              | store_id             |
| warehouse          | warehouse_id         |
| warehouse_location | location_id          |

## 1.3 Claves foráneas declaradas
------------------------------------------------------------
| tabla_origen       | columna_origen   | tabla_destino      | columna_destino   | constraint_name                      |
|:-------------------|:-----------------|:-------------------|:------------------|:-------------------------------------|
| central_inventory  | location_id      | warehouse_location | location_id       | central_inventory_location_id_fkey   |
| central_inventory  | product_id       | central_product    | product_id        | central_inventory_product_id_fkey    |
| central_inventory  | warehouse_id     | warehouse          | warehouse_id      | central_inventory_warehouse_id_fkey  |
| central_product    | brand_id         | brand              | brand_id          | central_product_brand_id_fkey        |
| central_product    | category_id      | category           | category_id       | central_product_category_id_fkey     |
| inventory          | product_id       | product            | product_id        | inventory_product_id_fkey            |
| inventory          | store_id         | store              | store_id          | inventory_store_id_fkey              |
| product_offer      | offer_id         | offer              | offer_id          | product_offer_offer_id_fkey          |
| product_offer      | product_id       | product            | product_id        | product_offer_product_id_fkey        |
| return_item        | sale_item_id     | sale_item          | sale_item_id      | return_item_sale_item_id_fkey        |
| sale               | customer_id      | customer           | customer_id       | sale_customer_id_fkey                |
| sale               | store_id         | store              | store_id          | sale_store_id_fkey                   |
| sale_item          | offer_id         | offer              | offer_id          | sale_item_offer_id_fkey              |
| sale_item          | product_id       | product            | product_id        | sale_item_product_id_fkey            |
| sale_item          | sale_id          | sale               | sale_id           | sale_item_sale_id_fkey               |
| warehouse_location | warehouse_id     | warehouse          | warehouse_id      | warehouse_location_warehouse_id_fkey |

## 1.4 Índices declarados (todos, incluyendo no-PK)
------------------------------------------------------------
| tablename          | indexname                  | indexdef                                                                                           |
|:-------------------|:---------------------------|:---------------------------------------------------------------------------------------------------|
| brand              | brand_pkey                 | CREATE UNIQUE INDEX brand_pkey ON public.brand USING btree (brand_id)                              |
| category           | category_pkey              | CREATE UNIQUE INDEX category_pkey ON public.category USING btree (category_id)                     |
| central_inventory  | central_inventory_pkey     | CREATE UNIQUE INDEX central_inventory_pkey ON public.central_inventory USING btree (inventory_id)  |
| central_product    | central_product_pkey       | CREATE UNIQUE INDEX central_product_pkey ON public.central_product USING btree (product_id)        |
| central_product    | central_product_sku_key    | CREATE UNIQUE INDEX central_product_sku_key ON public.central_product USING btree (sku)            |
| city_zone          | city_zone_pkey             | CREATE UNIQUE INDEX city_zone_pkey ON public.city_zone USING btree (postal_code)                   |
| customer           | customer_email_key1        | CREATE UNIQUE INDEX customer_email_key1 ON public.customer USING btree (email)                     |
| customer           | customer_pkey1             | CREATE UNIQUE INDEX customer_pkey1 ON public.customer USING btree (customer_id)                    |
| inventory          | inventory_pkey             | CREATE UNIQUE INDEX inventory_pkey ON public.inventory USING btree (inventory_id)                  |
| offer              | offer_pkey                 | CREATE UNIQUE INDEX offer_pkey ON public.offer USING btree (offer_id)                              |
| product            | product_pkey               | CREATE UNIQUE INDEX product_pkey ON public.product USING btree (product_id)                        |
| product_offer      | product_offer_pkey         | CREATE UNIQUE INDEX product_offer_pkey ON public.product_offer USING btree (product_id, offer_id)  |
| return_item        | return_item_pkey           | CREATE UNIQUE INDEX return_item_pkey ON public.return_item USING btree (return_id)                 |
| return_reason      | return_reason_pkey         | CREATE UNIQUE INDEX return_reason_pkey ON public.return_reason USING btree (reason_id)             |
| sale               | fki_sale_customer_id_fkeya | CREATE INDEX fki_sale_customer_id_fkeya ON public.sale USING btree (customer_id)                   |
| sale               | sale_pkey                  | CREATE UNIQUE INDEX sale_pkey ON public.sale USING btree (sale_id)                                 |
| sale_item          | sale_item_pkey             | CREATE UNIQUE INDEX sale_item_pkey ON public.sale_item USING btree (sale_item_id)                  |
| store              | store_pkey                 | CREATE UNIQUE INDEX store_pkey ON public.store USING btree (store_id)                              |
| warehouse          | warehouse_pkey             | CREATE UNIQUE INDEX warehouse_pkey ON public.warehouse USING btree (warehouse_id)                  |
| warehouse_location | warehouse_location_pkey    | CREATE UNIQUE INDEX warehouse_location_pkey ON public.warehouse_location USING btree (location_id) |

# PASADA 2 — VOLÚMENES, NULOS, FECHAS, ESTADÍSTICAS Y DUPLICADOS
================================================================================

## 2.1 Conteo de filas por tabla
------------------------------------------------------------
| tabla              |   filas |
|:-------------------|--------:|
| sale_item          |   42313 |
| sale               |   20000 |
| customer           |    5750 |
| return_item        |    2330 |
| inventory          |    1000 |
| product            |      50 |
| central_product    |      50 |
| central_inventory  |      49 |
| city_zone          |      42 |
| warehouse_location |      40 |
| brand              |      29 |
| store              |      20 |
| category           |       6 |
| return_reason      |       6 |
| product_offer      |       6 |
| offer              |       1 |
| warehouse          |       1 |

Total tablas: 17 — Total filas: 71,693

## 2.2 Columnas con valores nulos
------------------------------------------------------------
| tabla           | columna          |   nulos |
|:----------------|:-----------------|--------:|
| brand           | website          |       8 |
| central_product | sku              |       1 |
| central_product | barcode          |       1 |
| city_zone       | zone_orientation |       1 |
| sale_item       | offer_id         |   42305 |

**Total columnas con al menos un nulo: 5**

## 2.3 Rangos de fechas — detección de valores absurdos
------------------------------------------------------------
*(Fechas < 2010 o > 2030 merecen investigación)*

| tabla             | columna     | min                        | max                        | alerta   |
|:------------------|:------------|:---------------------------|:---------------------------|:---------|
| central_inventory | last_update | 2026-04-04 20:30:50.917115 | 2026-04-04 20:30:50.917115 | ok       |
| customer          | created_at  | 2018-01-01 03:38:29.909295 | 2026-04-06 14:05:51.530479 | ok       |
| inventory         | last_update | 2026-04-04 12:31:02.168721 | 2026-04-04 12:31:02.168721 | ok       |
| offer             | start_date  | 2024-05-01                 | 2024-05-01                 | ok       |
| offer             | end_date    | 2024-05-07                 | 2024-05-07                 | ok       |
| product           | created_at  | 2026-04-04 11:23:48.591695 | 2026-04-04 11:23:48.591695 | ok       |
| return_item       | return_date | 2020-01-09 15:12:41.444797 | 2026-02-07 02:02:05.028517 | ok       |
| sale              | sale_date   | 2020-01-01 03:41:35.198837 | 2025-12-30 23:52:53.702142 | ok       |
| store             | opened_date | 2026-04-04                 | 2026-04-04                 | ok       |

## 2.4 Estadísticas básicas — columnas numéricas
------------------------------------------------------------
*(min < 0 en cantidades/precios, stddev muy alta o avg muy alejado del max son señales de alerta)*

| tabla              | columna          |   no_nulos |      min |        max |        avg |     stddev |
|:-------------------|:-----------------|-----------:|---------:|-----------:|-----------:|-----------:|
| brand              | brand_id         |         29 |   1      |    29      |    15      |     8.5147 |
| category           | category_id      |          6 |   1      |     6      |     3.5    |     1.8708 |
| central_inventory  | inventory_id     |         49 |   1      |    49      |    25      |    14.2887 |
| central_inventory  | warehouse_id     |         49 |   1      |     1      |     1      |     0      |
| central_inventory  | location_id      |         49 |   1      |    40      |    19.8163 |    11.1984 |
| central_inventory  | product_id       |         49 |   1      |    50      |    25.4286 |    14.7196 |
| central_inventory  | quantity         |         49 |   1      |   100      |    53.8163 |    27.9514 |
| central_inventory  | min_stock        |         49 |   5      |     5      |     5      |     0      |
| central_inventory  | max_stock        |         49 | 200      |   200      |   200      |     0      |
| central_product    | product_id       |         50 |   1      |    50      |    25.5    |    14.5774 |
| central_product    | category_id      |         50 |   1      |     6      |     2.72   |     1.6787 |
| central_product    | brand_id         |         50 |   1      |    29      |    11.52   |     8.3842 |
| central_product    | unit_cost        |         50 |  11.99   |   239.99   |    72.048  |    52.3629 |
| central_product    | unit_price       |         50 |  19.99   |   399.99   |   118.485  |    88.3743 |
| customer           | customer_id      |       5750 |   1      |  5752      |  2877.24   |  1660.42   |
| inventory          | inventory_id     |       1000 |   1      |  1000      |   500.5    |   288.819  |
| inventory          | store_id         |       1000 |   1      |    20      |    10.5    |     5.7692 |
| inventory          | product_id       |       1000 |   1      |    50      |    25.5    |    14.4381 |
| inventory          | stock            |       1000 |   0      |     4      |     1.915  |     1.3899 |
| offer              | offer_id         |          1 |   1      |     1      |     1      |   nan      |
| offer              | discount_percent |          1 |  10      |    10      |    10      |   nan      |
| product            | product_id       |         50 |   1      |    50      |    25.5    |    14.5774 |
| product            | price            |         50 |  19.99   |   399.99   |   118.485  |    88.3743 |
| product_offer      | product_id       |          6 |   1      |    30      |     9.3333 |    11.3255 |
| product_offer      | offer_id         |          6 |   1      |     1      |     1      |     0      |
| return_item        | return_id        |       2330 |   1      |  2330      |  1165.5    |   672.757  |
| return_item        | sale_item_id     |       2330 |  12      | 43554      | 23155.2    | 13211.6    |
| return_item        | quantity         |       2330 |   1      |     1      |     1      |     0      |
| return_item        | reason_id        |       2330 |   1      |     5      |     3.0176 |     1.4194 |
| return_reason      | reason_id        |          6 |   1      |     6      |     3.5    |     1.8708 |
| sale               | sale_id          |      20000 |   3      | 21004      | 10253      |  6105.81   |
| sale               | customer_id      |      20000 |   1      |  5752      |  1092.93   |  1452.82   |
| sale               | store_id         |      20000 |   1      |    20      |     9.9639 |     5.9246 |
| sale               | total            |      20000 |  19.99   |  3019.89   |   480.891  |   416.079  |
| sale_item          | sale_item_id     |      42313 |   1      | 43557      | 21411.5    | 12473.6    |
| sale_item          | sale_id          |      42313 |   3      | 21004      |  8804.36   |  5426.12   |
| sale_item          | product_id       |      42313 |   1      |    50      |    25.4857 |    14.4278 |
| sale_item          | quantity         |      42313 |   1      |     3      |     1.9216 |     0.8169 |
| sale_item          | unit_price       |      42313 |  19.99   |   399.99   |   118.448  |    87.7264 |
| sale_item          | offer_id         |          8 |   1      |     1      |     1      |     0      |
| sale_item          | subtotal         |      42313 |  19.99   |  1199.97   |   227.302  |   206.314  |
| store              | store_id         |         20 |   1      |    20      |    10.5    |     5.9161 |
| store              | latitude         |         20 |  40.3818 |    40.4772 |    40.4254 |     0.0278 |
| store              | longitude        |         20 |  -3.7232 |    -3.5778 |    -3.6751 |     0.0417 |
| warehouse          | warehouse_id     |          1 |   1      |     1      |     1      |   nan      |
| warehouse          | latitude         |          1 |  40.3679 |    40.3679 |    40.3679 |   nan      |
| warehouse          | longitude        |          1 |  -3.7473 |    -3.7473 |    -3.7473 |   nan      |
| warehouse_location | location_id      |         40 |   1      |    40      |    20.5    |    11.6905 |
| warehouse_location | warehouse_id     |         40 |   1      |     1      |     1      |     0      |

## 2.5 Duplicados exactos por tabla (filas no-PK idénticas)
------------------------------------------------------------
*(Si una tabla sin PK tiene filas_extra > 0, hay duplicados reales)*

| tabla              |   grupos_dup |   filas_extra | nota            |
|:-------------------|-------------:|--------------:|:----------------|
| brand              |            0 |             0 |                 |
| category           |            0 |             0 |                 |
| central_inventory  |            0 |             0 |                 |
| central_product    |            0 |             0 |                 |
| city_zone          |           15 |            21 |                 |
| customer           |            0 |             0 |                 |
| inventory          |            0 |             0 |                 |
| offer              |            0 |             0 |                 |
| product            |            0 |             0 |                 |
| product_offer      |            0 |             0 | solo columna PK |
| return_item        |            0 |             0 |                 |
| return_reason      |            0 |             0 |                 |
| sale               |            0 |             0 |                 |
| sale_item          |            0 |             0 |                 |
| store              |            0 |             0 |                 |
| warehouse          |            0 |             0 |                 |
| warehouse_location |            0 |             0 |                 |

**Tablas con al menos un duplicado: 1 de 17**

## 2.6 Coherencia temporal: fecha de alta del cliente vs primera venta
------------------------------------------------------------
Columnas de fecha en `customer`: ['created_at']
Columnas de fecha en `sale`:     ['sale_date']

Comparando `customer.created_at` (fecha de alta) con MIN(`sale.sale_date`) (primera venta).

**30 clientes con primera venta ANTERIOR a su fecha de alta (muestra de hasta 30):**
|   customer_id | fecha_alta                 | primera_venta              | dias_diferencia             |
|--------------:|:---------------------------|:---------------------------|:----------------------------|
|          5078 | 2026-04-06 14:05:51.530479 | 2021-01-01 02:48:13.286766 | -1922 days +12:42:21.756287 |
|          3544 | 2026-04-06 14:05:51.530479 | 2021-01-01 04:58:51.410471 | -1922 days +14:52:59.879992 |
|          4988 | 2026-04-06 14:05:51.530479 | 2021-01-01 05:54:50.334252 | -1922 days +15:48:58.803773 |
|          3617 | 2026-04-06 14:05:51.530479 | 2021-01-01 07:11:50.532137 | -1922 days +17:05:59.001658 |
|          5477 | 2026-04-06 14:05:51.530479 | 2021-01-01 13:48:56.691327 | -1922 days +23:43:05.160848 |
|          3605 | 2026-04-06 14:05:51.530479 | 2021-01-01 19:24:35.483381 | -1921 days +05:18:43.952902 |
|          5522 | 2026-04-06 14:05:51.530479 | 2021-01-01 20:59:29.978499 | -1921 days +06:53:38.448020 |
|          2939 | 2026-04-06 14:05:51.530479 | 2021-01-01 21:46:40.803078 | -1921 days +07:40:49.272599 |
|          5290 | 2026-04-06 14:05:51.530479 | 2021-01-01 22:08:15.025371 | -1921 days +08:02:23.494892 |
|          5323 | 2026-04-06 14:05:51.530479 | 2021-01-01 22:19:10.746598 | -1921 days +08:13:19.216119 |
|          5012 | 2026-04-06 14:05:51.530479 | 2021-01-02 03:47:23.828060 | -1921 days +13:41:32.297581 |
|          3715 | 2026-04-06 14:05:51.530479 | 2021-01-02 05:07:12.282384 | -1921 days +15:01:20.751905 |
|          5471 | 2026-04-06 14:05:51.530479 | 2021-01-02 05:21:45.669331 | -1921 days +15:15:54.138852 |
|          3714 | 2026-04-06 14:05:51.530479 | 2021-01-02 09:16:54.244780 | -1921 days +19:11:02.714301 |
|          4240 | 2026-04-06 14:05:51.530479 | 2021-01-02 10:51:57.128630 | -1921 days +20:46:05.598151 |
|          5320 | 2026-04-06 14:05:51.530479 | 2021-01-02 20:18:37.435749 | -1920 days +06:12:45.905270 |
|          5577 | 2026-04-06 14:05:51.530479 | 2021-01-02 21:43:14.281330 | -1920 days +07:37:22.750851 |
|          4914 | 2026-04-06 14:05:51.530479 | 2021-01-03 02:08:25.604467 | -1920 days +12:02:34.073988 |
|          5543 | 2026-04-06 14:05:51.530479 | 2021-01-03 07:08:17.263583 | -1920 days +17:02:25.733104 |
|          4761 | 2026-04-06 14:05:51.530479 | 2021-01-03 16:29:40.317199 | -1919 days +02:23:48.786720 |
|          3586 | 2026-04-06 14:05:51.530479 | 2021-01-03 16:53:54.235684 | -1919 days +02:48:02.705205 |
|          5257 | 2026-04-06 14:05:51.530479 | 2021-01-03 17:06:59.755943 | -1919 days +03:01:08.225464 |
|          4744 | 2026-04-06 14:05:51.530479 | 2021-01-03 18:52:21.809353 | -1919 days +04:46:30.278874 |
|          3662 | 2026-04-06 14:05:51.530479 | 2021-01-03 20:05:02.815154 | -1919 days +05:59:11.284675 |
|          5473 | 2026-04-06 14:05:51.530479 | 2021-01-04 00:14:17.927952 | -1919 days +10:08:26.397473 |
|          4681 | 2026-04-06 14:05:51.530479 | 2021-01-04 00:31:30.637726 | -1919 days +10:25:39.107247 |
|          5440 | 2026-04-06 14:05:51.530479 | 2021-01-04 02:11:34.405971 | -1919 days +12:05:42.875492 |
|          5731 | 2026-04-06 14:05:51.530479 | 2021-01-04 02:54:34.171461 | -1919 days +12:48:42.640982 |
|          4133 | 2026-04-06 14:05:51.530479 | 2021-01-04 03:20:06.297454 | -1919 days +13:14:14.766975 |
|          5580 | 2026-04-06 14:05:51.530479 | 2021-01-04 10:32:01.327213 | -1919 days +20:26:09.796734 |