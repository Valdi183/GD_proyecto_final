# Esquema Estrella — dwh (Kimball) — Vista ASCII

> Representación visual del modelo dimensional.
> El diagrama Mermaid completo (con todas las columnas) está en `esquema_estrella.md`.

---

## Esquema estrella completo

```
                              ┌─────────────────────┐
                              │      dim_fecha       │
                              │─────────────────────│
                              │ date_id  INT  PK     │ ← smart key YYYYMMDD
                              │ fecha    DATE        │
                              │ anio, mes, trimestre │
                              │ nombre_mes           │
                              │ dia_semana           │
                              │ es_fin_de_semana     │
                              │ es_dia_habil         │
                              └──────────┬──────────┘
                                         │ date_id (FK)
                              ┌──────────┼──────────────────────────────────────┐
                              │          │                                        │
                     ┌────────▼──────┐   │   ┌─────────────────────────────────▼──────┐
                     │  fact_ventas  │   │   │          fact_devoluciones              │
                     │───────────────│   │   │────────────────────────────────────────│
                     │ venta_id   PK │   │   │ devolucion_id  PK                       │
                     │ date_id    FK │   │   │ return_date_id FK ──▶ dim_fecha (role)  │
                     │ cliente_id FK │   │   │ venta_date_id  FK ──▶ dim_fecha (role)  │
                     │ producto_id FK│   │   │ cliente_id     FK                       │
                     │ tienda_id  FK │   │   │ producto_id    FK                       │
                     │ oferta_id  FK │   │   │ tienda_id      FK                       │
                     │ sale_id   [DD]│   │   │ oferta_id      FK                       │
                     │ sale_item [DD]│   │   │ motivo_id      FK ──▶ dim_motivo        │
                     │ quantity      │   │   │ sale_item_id  [DD]                      │
                     │ unit_price    │   │   │ return_id     [DD]                      │
                     │ unit_cost     │   │   │ quantity_devuelta                       │
                     │ subtotal      │   │   │ importe_devuelto                        │
                     │ margen_bruto  │   │   │ costo_devuelto                          │
                     └───────┬───────┘   │   └──────────────┬──────────────────────────┘
                             │           │                   │
            ─────────────────┴───────────┴───────────────────┴───────────────────
            │                     │                 │                     │
   ┌────────▼──────┐   ┌──────────▼──────┐  ┌──────▼──────────┐  ┌──────▼────────┐
   │  dim_cliente  │   │  dim_producto   │  │   dim_tienda    │  │  dim_oferta   │
   │───────────────│   │─────────────────│  │─────────────────│  │───────────────│
   │ cliente_id PK │   │ producto_id  PK │  │ tienda_id    PK │  │ oferta_id  PK │
   │ customer_id   │   │ product_id      │  │ store_id        │  │ offer_id      │
   │ nombre_compl. │   │ nombre          │  │ nombre          │  │ nombre        │
   │ email         │   │ categoria       │  │ ciudad          │  │ descuento_pct │
   │ telefono      │   │ marca           │  │ fecha_apertura  │  │ fecha_inicio  │
   │ fecha_alta_ef.│   │ sku             │  │ latitud         │  │ fecha_fin     │
   │ zona_id    FK─┼──┐│ precio_lista    │  │ longitud        │  │ sentinel=0    │
   └───────────────┘  ││ costo_unitario  │  │ zona_id      FK─┼─┐└───────────────┘
                       │└─────────────────┘  └─────────────────┘ │
                       │                                           │
                       └──────────────┐                           │
                                      ▼                           │
                              ┌───────────────┐◀─────────────────┘
                              │   dim_zona    │
                              │───────────────│
                              │ zona_id    PK │
                              │ postal_code   │
                              │ distrito      │
                              │ tipo_area     │
                              │ orientacion   │
                              │ ciudad        │
                              └───────────────┘
```

**Nota:** `dim_zona` tiene **role-playing doble**: es FK de `dim_tienda` (zona de la tienda) y de `dim_cliente` (zona predominante del cliente). Las dos relaciones son semánticamente independientes.

---

## Sentinel rows

```
dim_oferta:  oferta_id=0 → "Sin oferta"         (99,98 % de sale_item no tiene oferta)
dim_motivo:  motivo_id=0 → "Motivo no registrado" (preventivo; 0 casos actuales)
```

Permiten FK NOT NULL en `fact_ventas.oferta_id` y `fact_devoluciones.motivo_id` sin excepciones.

---

## Orden de carga ETL

```
PASO 1: dim_fecha      ───────────────────────────────────── (sin dependencias)
PASO 2: dim_zona       ◀── public.city_zone
PASO 3: dim_oferta     ◀── public.offer            ┐ paralelo entre sí
PASO 4: dim_motivo     ◀── public.return_reason     ┘ y con paso 2
PASO 5: dim_producto   ◀── central_product + brand + category (desnormalizado)
PASO 6: dim_tienda     ◀── store + dim_zona (paso 2)
PASO 7: dim_cliente    ◀── customer + sale→store→city_zone + dim_zona (paso 2)
PASO 8: fact_ventas    ◀── Pasos 1–7            ┐ paralelo entre sí
PASO 9: fact_devoluc.  ◀── Pasos 1–7            ┘
```

---

## Volúmenes en DWH (post-ETL)

| Tabla | Filas | Tipo |
|:------|------:|:-----|
| `dim_fecha` | 2.922 | Dimensión (2020–2027) |
| `dim_zona` | 42 | Dimensión |
| `dim_oferta` | 2 (1 real + sentinel) | Dimensión |
| `dim_motivo` | 7 (6 reales + sentinel) | Dimensión |
| `dim_producto` | 50 | Dimensión |
| `dim_tienda` | 20 | Dimensión |
| `dim_cliente` | 5.750 | Dimensión |
| `fact_ventas` | **42.313** | Hecho principal |
| `fact_devoluciones` | **2.330** | Hecho secundario |
| `marts.customer_360` | **5.750** | Mart (1 fila/cliente) |
