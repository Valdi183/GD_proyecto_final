
# Decisiones de limpieza — Fase 1

Generado: 2026-05-06  
Fuente: exploración Pasadas 1–2 + 13 queries de verificación sobre schema `public`.

| ID  | Hallazgo | Volumen | Decisión | Justificación |
|:----|:---------|:--------|:---------|:--------------|
| D01 | `city_zone`: múltiples códigos postales comparten el mismo distrito, `area_type` y `zone_orientation` | 15 grupos (21 pares de CPs) | **Sin acción** | Comportamiento geográfico correcto. Madrid tiene varios CPs por distrito; compartir atributos de área no es un error |
| D02 | `sale_item`: filas con contenido económico idéntico dentro de la misma venta (`sale_id`, `product_id`, `quantity`, `unit_price`, `offer_id`, `subtotal`) | 240 grupos, 242 filas extra (147 con IDs consecutivos, 93 no consecutivos) | **Deduplicar todas**: conservar `MIN(sale_item_id)`, eliminar el resto | Dos registros con idéntico contenido económico en la misma venta son semánticamente indistinguibles y doblan artificialmente ingresos y unidades. El gap entre IDs (consecutivo o no) refleja distintos momentos del batch de carga, no una diferencia de negocio |
| D03 | `sale.total` ≠ `SUM(sale_item.subtotal)` | 1 venta | **Recalcular** `total = SUM(subtotales)` de sus ítems | La cabecera de venta es un campo derivado; los ítems son la fuente de verdad (decisión acordada en diseño) |
| D04 | `sale_item.subtotal` ≠ `quantity × unit_price` (ítems sin oferta) | 0 filas | **Sin acción** | Todos los subtotales están correctamente calculados |
| D05 | `product_id = 29` ("Sensor temperatura inteligente", Xiaomi, 19,99 €) presente en `product` pero ausente en `central_product` | 1 producto — 711 líneas de venta, 1.426 unidades, 28.505,74 € de ingresos (2020–2025) | **Insertar** registro en `central_product` con `category_id = 1` (Diagnóstico) y `unit_cost` = mediana de los productos de esa categoría; `unit_price = 19,99` | Producto con impacto real que debe estar en el catálogo maestro para calcular márgenes. "Diagnóstico — Productos de medición y monitoreo" es la categoría semánticamente correcta para un sensor de temperatura |
| D06 | `customer.created_at` contiene la marca de tiempo del dump (`2026-04-06 14:05:51`), no la fecha real de alta del cliente | Todos los clientes con ventas anteriores a esa fecha (la mayoría) | **Sin corrección en origen**. En el ETL, `fecha_alta_efectiva = MIN(sale.sale_date)` por cliente | No es un error de datos sino una limitación semántica: el sistema fuente no registró la fecha de alta; la columna almacena el momento de carga |
| D07 | Clientes sin ninguna venta | 0 clientes | **Sin acción** | Todos los 5.750 clientes tienen al menos una compra; no hay casos edge para la derivación de `fecha_alta_efectiva` |

## Notas de implementación

- Las correcciones D02, D03 y D05 se aplican mediante el script `src/limpieza/limpieza.py`.
- El script es **idempotente**: puede ejecutarse múltiples veces sin efectos secundarios.
- Las decisiones D01, D04, D06 y D07 no requieren modificación de datos.
- Los datos de `inventory` y `central_inventory` quedan sin modelar en el DWH (snapshots sin histórico); se documentan como ampliación futura en el documento técnico.

## Preguntas abiertas para fases posteriores

| ID  | Pregunta | Fase | Contexto |
|:----|:---------|:-----|:---------|
| Q01 | ¿Los clientes sin ventas entran en la curva de Lorenz y en los percentiles de CLTV, o solo en el conteo total de clientes? | Fase 5 | En este dataset la respuesta es académica (n=0 clientes sin ventas, D07). Sin embargo, la decisión metodológica correcta es: CLTV=0 para clientes sin compras; incluirlos en Lorenz distorsiona la concentración hacia abajo artificialmente. Lo habitual es excluirlos de Lorenz y reportarlos aparte como "clientes inactivos". Confirmar en Fase 5. |
