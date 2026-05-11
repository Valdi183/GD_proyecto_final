# Diagrama ER — saleshealth (schema public) — Vista ASCII

> Representación simplificada de las 17 tablas y sus relaciones principales.
> El diagrama Mermaid completo (con todas las columnas) está en `er_diagrama.md`.

---

## Subsistema ERP — Transaccional + Catálogo maestro

```
┌─────────────┐     1:N    ┌──────────────┐     1:N    ┌──────────────────┐
│  customer   │──────────▶│     sale     │──────────▶│    sale_item     │
│─────────────│            │──────────────│            │──────────────────│
│ customer_id │PK          │ sale_id      │PK          │ sale_item_id     │PK
│ first_name  │            │ customer_id  │FK          │ sale_id          │FK
│ last_name   │            │ store_id     │FK          │ product_id       │FK
│ email       │UK          │ sale_date    │            │ quantity         │
│ phone       │            │ total        │            │ unit_price       │
│ created_at  │            └──────────────┘            │ offer_id         │FK (nullable)
└─────────────┘                                        │ subtotal         │
                                                       └──────────┬───────┘
                                                                  │1:N
                                                       ┌──────────▼───────┐
                                                       │  return_item     │
┌─────────────┐     1:N    ┌──────────────┐            │──────────────────│
│    store    │──────────▶│     sale     │            │ return_id        │PK
│─────────────│            └──────────────┘            │ sale_item_id     │FK
│ store_id    │PK                                      │ return_date      │
│ name        │                                        │ quantity         │
│ postal_code │──────────▶ city_zone (implícita)       │ reason_id        │FK (implícita)
│ latitude    │                                        └──────────────────┘
│ longitude   │
│ opened_date │                                        ┌──────────────────┐
└─────────────┘                                        │  return_reason   │
                                                       │──────────────────│
                                                       │ reason_id        │PK
                                                       │ reason           │
                                                       └──────────────────┘

┌──────────────────┐            ┌──────────────────┐     N:M    ┌──────────────┐
│    product       │──────────▶│  product_offer   │◀──────────│    offer     │
│──────────────────│            │──────────────────│            │──────────────│
│ product_id       │PK          │ product_id       │PK+FK       │ offer_id     │PK
│ name             │            │ offer_id         │PK+FK       │ name         │
│ category         │            └──────────────────┘            │ discount_pct │
│ manufacturer     │                                            │ start_date   │
│ price            │                                            │ end_date     │
└──────────────────┘                                            └──────────────┘
        │ (mismos product_id, FK implícita)
        ▼
┌──────────────────┐     FK     ┌──────────────┐     FK     ┌──────────────┐
│  central_product │──────────▶│   category   │            │    brand     │
│──────────────────│            │──────────────│            │──────────────│
│ product_id       │PK          │ category_id  │PK          │ brand_id     │PK
│ name             │            │ name         │            │ name         │
│ category_id      │FK          └──────────────┘            │ country      │
│ brand_id         │FK──────────────────────────────────────▶│ website      │
│ sku              │UK                                       └──────────────┘
│ unit_cost        │
│ unit_price       │
└──────────────────┘
```

## Subsistema Logística — WMS

```
┌──────────────┐     1:N    ┌──────────────────────┐     1:N    ┌───────────────────┐
│  warehouse   │──────────▶│  warehouse_location  │──────────▶│ central_inventory │
│──────────────│            │──────────────────────│            │───────────────────│
│ warehouse_id │PK          │ location_id          │PK          │ inventory_id      │PK
│ name         │            │ warehouse_id         │FK          │ warehouse_id      │FK
│ city         │            │ zone / aisle         │            │ location_id       │FK
│ postal_code  │            │ shelf / bin_code     │            │ product_id        │FK → central_product
└──────────────┘            └──────────────────────┘            │ quantity          │
                                                                 └───────────────────┘
```

## Subsistema Geodatos

```
┌──────────────────┐
│    city_zone     │
│──────────────────│
│ postal_code      │PK
│ district         │
│ area_type        │          Referenciada por:
│ zone_orientation │  ─────▶  store.postal_code (FK implícita)
│ city             │
└──────────────────┘
```

---

## Cardinalidades clave

| Relación | Tipo | Constraint |
|:---------|:----:|:----------:|
| customer → sale | 1:N | FK declarada |
| store → sale | 1:N | FK declarada |
| sale → sale_item | 1:N | FK declarada |
| product → sale_item | 1:N | FK declarada |
| offer → sale_item | 0..1:N | FK declarada, nullable |
| sale_item → return_item | 1:N | FK declarada |
| product ↔ central_product | 1:0..1 | **Sin FK** — mismo product_id por convención |
| store → city_zone | N:1 | **Sin FK** — vía postal_code |
| return_item → return_reason | N:1 | **Sin FK** — vía reason_id |
| product_offer (pivote) | N:M product↔offer | PK compuesta |
