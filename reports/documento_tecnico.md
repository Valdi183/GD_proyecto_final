# saleshealth — Análisis de Valor de Vida del Cliente (CLTV)
## Documento Técnico

**Asignatura:** Gestión de Datos · UAX  
**Fecha:** 11 de mayo de 2026  
**Repositorio:** `GD_proyecto_final/`

---

## 1. Introducción y Contexto

### Resumen ejecutivo

El proyecto construye un sistema analítico end-to-end sobre datos transaccionales de una cadena de venta de productos de salud en Madrid. A partir de 17 tablas operacionales (3 esquemas PostgreSQL, 71.934 filas en origen), se implementa un pipeline ETL que genera un modelo dimensional Kimball con 2 tablas de hechos y 7 dimensiones, seguido de una mart `customer_360` con 26 indicadores por cliente. Sobre esa base se realizan análisis de distribución CLTV, clustering no supervisado y un dashboard interactivo de 5 páginas.

**Números clave:** 5.750 clientes activos · 42.313 líneas de venta · 9.341.505,20 € ingresos netos · 3.670.369,64 € de valor de vida total (CLTV) · K=4 segmentos con silhouette=0,696.

**Hallazgos principales:**

> 1. La distribución del CLTV es **bimodal**, no Pareto continua: dos poblaciones casi disjuntas separadas por un valle vacío entre 500 € y 2.000 €.
> 2. **Concentración extrema**: el 13 % de clientes (recurrentes) genera el 91,5 % del CLTV positivo (Gini=0,830).
> 3. **Hallazgo contraintuitivo**: `margin_rate` correlaciona negativamente con CLTV (ρ=−0,67): mayor margen porcentual por unidad no implica mayor valor total.
> 4. **Sub-cluster anómalo** de 7 clientes con CLTV negativo detectado automáticamente por K-Means, replicando el hallazgo manual previo (validación de robustez).

### Fuente de datos

Sistema operacional saleshealth organizado en **4 subsistemas**:

| Subsistema | Tablas principales | Función |
|:-----------|:------------------|:--------|
| ERP — Transaccional | `sale`, `sale_item`, `store`, `product` | Ventas, tiendas, catálogo operacional |
| ERP — Catálogo maestro | `central_product`, `brand`, `category`, `offer`, `product_offer` | Costes, SKUs, promociones |
| CRM | `customer` | Maestro de clientes (5.750 registros) |
| Logística / Postventa | `warehouse`, `warehouse_location`, `central_inventory`, `city_zone`, `return_item`, `return_reason`, `inventory` | WMS, geodatos, devoluciones |

Total: **17 tablas**, **71.934 filas** en origen, **3 columnas con nulos** (brand.website, city_zone.zone_orientation, sale_item.offer_id).

### Arquitectura del sistema — 3 capas

| Capa | Schema | Contenido | Propósito analítico |
|:-----|:-------|:----------|:--------------------|
| **Operacional** | `public` | 17 tablas originales sin transformar | Fuente de verdad transaccional |
| **Analítica** | `dwh` | 7 dimensiones + 2 tablas de hechos | Consultas OLAP optimizadas, modelo Kimball SCD tipo 1 |
| **Negocio** | `marts` | `customer_360` (1 fila / cliente, 26 columnas) | Features para ML, alimenta dashboard |

### Stack tecnológico

| Componente | Tecnología | Propósito |
|:-----------|:-----------|:----------|
| Base de datos | PostgreSQL 18 | Almacenamiento operacional + DWH + marts |
| ETL / análisis | Python 3.12, pandas, NumPy | Pipeline de carga y transformación |
| ML | scikit-learn 1.4 | StandardScaler, PCA, KMeans, silhouette |
| ORM / conexión | SQLAlchemy 2.0, psycopg2 | Acceso tipado a PostgreSQL |
| Dashboard | Streamlit, Plotly | Visualización interactiva (5 páginas) |
| Entorno | python-dotenv, Jupyter | Configuración segura, notebooks reproducibles |

---

## 2. Modelo Dimensional

### Esquema estrella

El DWH implementa un **esquema estrella Kimball** con 2 tablas de hechos y 7 dimensiones compartidas:

```
                  dim_fecha ──────────────────────────────────┐
                     │                                         │
dim_zona ── dim_tienda ── fact_ventas ─── dim_cliente ── dim_zona
                │              │
           dim_producto    dim_oferta
                │
         dim_motivo ─── fact_devoluciones ─── dim_cliente
                              │
                  dim_fecha (role-playing: return_date / venta_date)
```

`dim_zona` se referencia desde `dim_tienda` (zona de la tienda) y `dim_cliente` (zona predominante del cliente, calculada como moda del distrito de compras).

### Tabla de hechos principal — `fact_ventas`

| Columna | Tipo | Descripción |
|:--------|:-----|:------------|
| `venta_id` | BIGINT PK | Surrogate key generada |
| `date_id` | INT FK | Smart key YYYYMMDD → `dim_fecha` |
| `cliente_id` | BIGINT FK | → `dim_cliente` |
| `producto_id` | BIGINT FK | → `dim_producto` |
| `tienda_id` | BIGINT FK | → `dim_tienda` |
| `oferta_id` | BIGINT FK | → `dim_oferta` (sentinel=0 si sin oferta) |
| `sale_id` / `sale_item_id` | INT | Drill-down al operacional |
| `quantity` | INT | Unidades vendidas (≥1, CHECK) |
| `unit_price`, `unit_cost` | NUMERIC(10,2) | Precio y coste unitario |
| `subtotal` | NUMERIC(12,2) | Ingreso bruto de la línea (≥0, CHECK) |
| `margen_bruto` | NUMERIC(12,2) | `subtotal − quantity×unit_cost`; aditiva en cualquier nivel |

**Ground truth:** 42.313 filas, 9.617.816,01 € brutos.

### Decisiones de diseño relevantes

- **Surrogate keys:** `dim_fecha` usa INT YYYYMMDD (smart key legible en fact sin JOIN); resto de dimensiones usan BIGINT IDENTITY.
- **Sentinel rows:** `dim_oferta` (oferta_id=0) y `dim_motivo` (motivo_id=0) permiten FK NOT NULL en todas las tablas de hechos. El 99,98 % de las líneas de venta no tienen oferta; el sentinel elimina NULLs sin coste semántico.
- **SCD Tipo 1:** todas las dimensiones. Cambios en atributos sobreescriben el valor anterior (no se guarda histórico de cambios).
- **Idempotencia ETL:** el orquestador ejecuta TRUNCATE antes de cada INSERT por lote; el script puede lanzarse N veces sin duplicar datos.
- **`fact_devoluciones` independiente de `fact_ventas`** (Opción A Kimball): no hay FK entre hechos; la trazabilidad se mantiene vía `sale_item_id` como degenerate dimension.

---

## 3. ETL y Calidad de Datos

### Pipeline ETL — orden topológico

| Paso | Tabla destino | Depende de | Nota |
|:-----|:-------------|:-----------|:-----|
| 1 | `dim_fecha` | — | Generada sintéticamente; 2020-01-01 a 2027-12-31 |
| 2 | `dim_zona` | `public.city_zone` | 42 zonas postales de Madrid |
| 3 | `dim_oferta` | `public.offer` | Sentinel oferta_id=0 al inicio |
| 4 | `dim_motivo` | `public.return_reason` | Sentinel motivo_id=0 al inicio |
| 5 | `dim_producto` | `central_product`, `brand`, `category` | Desnormaliza en un solo JOIN (estrella, no snowflake) |
| 6 | `dim_tienda` | `public.store` + paso 2 | Resuelve zona_id por postal_code |
| 7 | `dim_cliente` | `public.customer` + `sale→store→city_zone` + paso 2 | Calcula zona predominante (D-M03b) |
| 8 | `fact_ventas` | Pasos 1–7 | Carga principal; 42.313 filas tras D02 |
| 9 | `fact_devoluciones` | Pasos 1–7 | Paralelizable con paso 8 |

**Tiempo total de ejecución:** 12,2 segundos (PostgreSQL 18, hardware estándar).

### Decisiones de limpieza — D01 a D07

| ID | Hallazgo | Volumen | Decisión | Impacto |
|:---|:---------|:--------|:---------|:--------|
| D01 | Múltiples CPs por distrito en Madrid | 15 grupos (21 pares) | Sin acción | Comportamiento geográfico correcto |
| D02 | Líneas de venta con contenido económico idéntico en el mismo pedido | 240 grupos, 242 filas | Deduplicar: conservar MIN(sale_item_id) | −242 filas en fact_ventas |
| D03 | `sale.total` ≠ SUM(sale_item.subtotal) | 1 venta | Recalcular total desde ítems | 1 pedido corregido |
| D04 | `subtotal` ≠ `quantity × unit_price` en ítems sin oferta | 0 filas | Sin acción | Todos los subtotales correctos |
| D05 | product_id=29 ausente en `central_product` | 1 producto, 711 líneas, 28.505,74 € | Insertar con unit_cost = mediana categoría | Cobertura unit_cost → 100 % |
| D06 | `customer.created_at` = timestamp de volcado del sistema | Todos los clientes | `fecha_alta_efectiva = MIN(sale_date)` en ETL | Sin corrección en origen |
| D07 | Clientes sin ventas | 0 clientes | Sin acción | Todos los 5.750 tienen ventas |

### Verificación de cuadres financieros

| Concepto | Importe |
|:---------|--------:|
| Ingresos brutos (SUM subtotal en DWH) | 9.617.816,01 € |
| Importe devuelto | 276.310,81 € |
| **Ingresos netos** | **9.341.505,20 €** |
| **Margen bruto** | **3.779.316,80 €** |
| Diferencia máxima origen→DWH | **0,00 €** (cuadre exacto) |

---

## 4. CLTV: Definición y Cálculo

### Definición adoptada (D-CLTV-01)

**CLTV histórico = valor real generado**, no proyección futura. Permite segmentación y sirve de variable objetivo para modelos predictivos en fases posteriores.

### Fórmula y componentes

```
CLTV = margen_neto = SUM(margen_bruto) − SUM(importe_devuelto) + SUM(costo_devuelto)
```

La corrección por `costo_devuelto` es crítica (D-CLTV-04): sin ella, una devolución completa produciría margen neto negativo en lugar de cero.

**Verificación unitaria:**
- Venta: precio=100 €, costo=60 €, margen_bruto=40 €
- Devolución completa: importe_devuelto=100 €, costo_devuelto=60 €
- Fórmula corregida: 40−100+60 = **0 €** ✓ | Fórmula incorrecta: 40−60 = −20 € ✗

### Identidad algebraica de los componentes (D-CLTV-13)

Los cuatro componentes descriptivos del CLTV satisfacen:

```
AOV × margin_rate × freq_mensual × meses_activo = margen_bruto_total
```

**Demostración algebraica:**

| Componente | Definición | Cancelación |
|:-----------|:-----------|:-----------|
| AOV | ingresos_brutos / n_pedidos | n_pedidos se cancela |
| margin_rate | margen_bruto / ingresos_brutos | ingresos_brutos se cancela |
| freq_mensual | n_pedidos / meses_activo | meses_activo se cancela |
| × meses_activo | — | — |
| **= margen_bruto_total** | | ✓ |

**Verificación empírica (D-CLTV-14):** max|margen_bruto − ROUND(producto, 2)| = **1,41 €** sobre 3.670.369,64 € → error relativo 3,8×10⁻⁷ (< 1 ppm).

**Cota teórica del error de representación NUMERIC(8,4):** ε_freq ≤ 0,00005 → max_error ≈ AOV_max × margin_rate × ε_freq × meses_max ≈ 1.000 × 0,40 × 0,00005 × 72 ≈ **1,44 €**. El resultado empírico (1,41 €) cae dentro de la cota teórica; el umbral de alerta se fija en 2,00 € (margen del 39 %).

### Resultados del CLTV

| Estadístico | Valor |
|:------------|------:|
| CLTV total | 3.670.369,64 € |
| Media | 638,33 € |
| Mediana | 52,00 € |
| Desv. estándar | 1.555,44 € |
| Máximo | 9.429,44 € |
| Mínimo | −80,00 € |
| Clientes con CLTV ≤ 0 | 306 (5,3 %) |

---

## 5. Distribución y Concentración

### Distribución del CLTV

> La distribución del CLTV **no sigue una ley de potencias (Pareto) continua**. Presenta **bimodalidad estructural**: dos poblaciones casi disjuntas separadas por un valle vacío entre 500 € y 2.000 €.

Estadísticos de forma:
- **Skewness (Fisher):** 2,57 — asimetría positiva moderada para retail (la bimodalidad, no la cola larga, explica el valor; la cola sería >4 en distribución Pareto pura)
- **Exceso de curtosis:** 5,37 — colas más pesadas de lo normal

El boxplot Tukey clasifica el 13 % superior como *outliers*, pero son una **población estructural** (recurrentes premium), no anomalías estadísticas. Decisión metodológica: no eliminar, segmentar.

**Percentiles clave:**

| Percentil | Valor |
|:---------:|------:|
| p50 (mediana) | 52 € |
| p75 | 120 € |
| p90 | 3.555 € |
| p95 | 4.787 € |
| p99 | 6.317 € |
| máx | 9.429 € |

El salto entre p75 (120 €) y p90 (3.555 €) confirma el valle vacío y la bimodalidad.

### Concentración — Curva de Lorenz

> **Gini = 0,830** sobre CLTV positivo (n=5.444). Alta concentración estructural.

| Punto Pareto | % clientes (top) | % CLTV |
|:-------------|:----------------:|:------:|
| Punto 1 | 6 % | 50 % |
| Punto 2 | 11 % | 80 % |
| Recurrentes premium | 13 % | 91,5 % |

### Correlaciones Spearman con CLTV

Se utiliza Spearman (no Pearson) por skewness=2,57, exceso de curtosis=5,37 y bimodalidad visual, que invalidan el supuesto de normalidad marginal de Pearson.

| Variable | ρ con CLTV | Interpretación |
|:---------|:----------:|:---------------|
| `aov` | **+0,94** | AOV ≈ proxy del CLTV cuando n_pedidos=1 (75 % del dataset) |
| `margin_rate` | **−0,67** | Hallazgo contraintuitivo: mayor margen relativo → menor CLTV total |
| `meses_activo` / `n_pedidos` | +0,58 | ρ=1,00 entre sí (identidad algebraica) |
| `return_rate` | +0,15 | Bajo poder discriminatorio |

La correlación negativa de `margin_rate` tiene explicación de negocio: los clientes recurrentes compran productos de mayor volumen y precio pero menor margen porcentual; los transaccionales compran artículos sueltos con mayor margen relativo.

---

## 6. PCA y Clustering

### Selección de variables (features)

| Variable | Transformación | Justificación de inclusión |
|:---------|:--------------|:--------------------------|
| `aov` | `log1p` | Skewness > 2; log-transformación normaliza |
| `margin_rate` | ninguna | Ya en [0, 1]; alta varianza independiente |
| `meses_activo` | ninguna | Proxy de fidelidad; sin correlación con margin_rate |
| `return_rate` | ninguna | Ya en [0, 1]; discrimina devolvedores |

**Variables descartadas:**

| Variable | Motivo |
|:---------|:-------|
| `n_pedidos` | ρ=1,00 con `meses_activo` (identidad algebraica) |
| `cltv` | Variable objetivo — incluirla crea sesgo circular |
| `recency_dias` | ρ=−0,22 con CLTV; bajo aporte, alta correlación con meses_activo |

### PCA — análisis de varianza

StandardScaler aplicado a las 4 features post-transformación. PCA sobre `X_scaled` para análisis de varianza:

| PC | Varianza individual | Acumulada |
|:---|:-------------------:|:---------:|
| PC1 | ~41 % | ~41 % |
| PC2 | ~23 % | ~64 % |
| PC3 | ~21 % | ~85 % |
| PC4 | ~15 % | 100 % |

**Decisión (D-CLU-05/06):** K-Means y Silhouette operan sobre `X_scaled` (espacio original de 4 variables). `X_pca[PC1, PC2]` se reserva exclusivamente para visualización. Con 4 variables sin ruido, reducir a PCA no aporta separación adicional.

**Validación ARI:** clustering sobre `X_scaled` vs clustering sobre `X_pca[PC1, PC2]` → ARI=0,358. Interpretación: proyectar a 2 dimensiones descarta el 35,7 % de varianza relevante, alterando significativamente las asignaciones. Justifica el uso del espacio original.

### Selección de K — método Silhouette

| K | Silhouette score | Seleccionado |
|:-:|:----------------:|:------------:|
| 2 | 0,6123 | |
| 3 | 0,6228 | |
| **4** | **0,6963** | **✓** |
| 5 | 0,5952 | |
| 6 | 0,5976 | |

K=4 maximiza el Silhouette score (rango 0–1; >0,5 indica segmentos bien diferenciados). La bimodalidad observada en Fase 5 (87 % transaccionales + 13 % recurrentes) predecía K≥2; K=4 añade la detección de devolvedores y el sub-cluster anómalo.

---

## 7. Los 4 Segmentos

### Tabla resumen de segmentos

| Segmento | n | % | AOV med. | Margen med. | Meses act. med. | Return rate med. | CLTV medio | CLTV total |
|:---------|:-:|:-:|:--------:|:-----------:|:---------------:|:----------------:|:----------:|:----------:|
| Recurrentes premium | 750 | 13,0 % | 580,72 € | 0,39 | 18 | 0,02 | 4.480 € | 3.359.998 € |
| Compradores únicos | 4.573 | 79,5 % | 129,90 € | 0,40 | 1 | 0,00 | 67 € | 305.529 € |
| Devolvedores | 420 | 7,3 % | 104,90 € | 0,40 | 1 | 1,00 | 12 € | 5.242 € |
| Productos a pérdida | 7 | 0,1 % | 19,99 € | −2,00 | 1 | 0,00 | −57 € | −400 € |

*Medianas por cluster excepto CLTV medio (media) y CLTV total (suma). Datos exactos del notebook 06_clustering.ipynb.*

### Descripción y recomendación por segmento

**Recurrentes premium (13 % de clientes, 91,5 % del CLTV positivo)**  
Compran con alta frecuencia (18 meses activos de media), ticket elevado (580 €) y tasa de devolución mínima (2 %). Son el núcleo generador de valor. **Acción:** retener a toda costa; programa de fidelización, atención prioritaria, ofertas exclusivas anticipadas.

**Compradores únicos (79,5 % de clientes, 8,3 % del CLTV)**  
Un solo pedido o frecuencia muy baja. CLTV modesto pero masa crítica enorme (4.573 clientes). **Acción:** campaña de segunda compra personalizada en los 30–60 días post-venta; el coste de activación es bajo comparado con el potencial de conversión al segmento premium.

**Devolvedores (7,3 % de clientes, 0,1 % del CLTV)**  
Frecuencia normal pero return_rate=1,00 (prácticamente todo lo comprado se devuelve). Generan coste operativo elevado con retorno mínimo (12 € de CLTV medio). **Acción:** revisión individualizada; restricciones en política de devoluciones; análisis de si el problema es el producto o el perfil del cliente.

**Productos a pérdida (0,1 % de clientes, CLTV negativo)**  
7 clientes con margen_bruto negativo y sin devoluciones registradas: el coste del producto supera el precio de venta. margin_rate mediana = −2,00 (pérdida del 200 %). **Acción:** investigación caso a caso; posible error de precio en catálogo o fraude en devoluciones no registradas.

> **Hallazgo de validación:** El sub-cluster "Productos a pérdida" fue detectado automáticamente por K-Means. El análisis manual previo (Fase 5, Sección 0) había identificado estos 7 clientes como anomalía. La coincidencia exacta valida la robustez del modelo de clustering.

---

## 8. Dashboard y Visualización

### Arquitectura del dashboard — 5 páginas Streamlit

| Página | Título | Contenido principal |
|:-------|:-------|:--------------------|
| 1 | Panel Ejecutivo | 8 KPIs globales (CLTV, clientes, ticket, márgenes), donut de segmentos, barras de aportación, top distritos, estado del negocio |
| 2 | Modelo de Datos | Flujo operacional→analítico→cliente (3 cajas), cobertura temporal, tabla D01-D07 en expander |
| 3 | Análisis CLTV | Histograma en escala log, curva de Lorenz con Gini y puntos Pareto, tabla por distrito, características de segmentos |
| 4 | Segmentación | 4 tarjetas de segmento, barras comparativas (clientes y CLTV total), radars 2×2 por segmento, validación técnica en expander |
| 5 | Customer 360 | Búsqueda por ID/email + botón aleatorio, KPIs individuales, barplot vs media del segmento con percentiles, histograma de posición global |

### Decisiones de diseño UX

- **Regla de negocio vs técnico:** tecnicismos (silhouette, ARI, PCA, surrogate key) exclusivamente en expanders colapsables `🔍 Detalles técnicos`. La pantalla principal usa únicamente lenguaje de negocio.
- **Colores por segmento:** consistentes en todas las páginas (`#2ECC71` premium, `#3498DB` únicos, `#E67E22` devolvedores, `#95A5A6` pérdida).
- **Caché:** `@st.cache_data(ttl=600)` para queries frecuentes, `ttl=3600` para metadatos (volúmenes, rango de fechas).
- **Visualización:** Plotly Express y Graph Objects para toda representación gráfica. `go.Scatterpolar` para radar charts 2×2. `go.Histogram` con escala log pre-computada en NumPy para evitar bugs de Plotly con NUMERIC PostgreSQL en eje logarítmico.

### Stack de visualización y arquitectura

```
app.py (Página 1) ─── utils.py (engine, cache, formatters)
pages/
  2_Modelo_de_Datos.py    ← get_rango_fechas(), get_ventas_por_anio()
  3_Analisis_CLTV.py      ← load_data() → customer_360
  4_Segmentacion.py       ← load_data(sql) + radar charts
  5_Customer_360.py       ← load_data() + session_state + percentiles
```

Arranque: `streamlit run src/dashboard/app.py` desde la raíz del proyecto.

---

## 9. Conclusiones y Limitaciones

### Conclusiones

**1. Bimodalidad estructural, no distribución Pareto**  
La distribución del CLTV presenta dos poblaciones casi disjuntas separadas por un valle vacío (500 €–2.000 €). Skewness=2,57 y Gini=0,830. El análisis de clustering confirma la estructura bimodal: K=4 identifica dos clusters claramente diferenciados antes de llegar a la cola alta.

**2. Identidad algebraica verificada con análisis de error de representación**  
AOV × margin_rate × freq_mensual × meses_activo = margen_bruto_total con error máximo empírico de 1,41 € sobre 3,67 M€ (3,8×10⁻⁷). La cota teórica (NUMERIC(8,4), 1,44 €) explica el error completamente, confirmando que no hay bug de implementación.

**3. Concentración extrema: top 13 % genera 91,5 % del valor**  
El coeficiente de Gini (0,830) es elevado incluso para retail. El segmento Recurrentes premium (750 clientes) concentra 3.359.998 € de los 3.670.370 € totales. La dependencia de un grupo tan pequeño constituye el principal riesgo de negocio identificado.

**4. `margin_rate` negativamente correlado con CLTV (ρ=−0,67)**  
Los clientes de mayor valor compran productos de mayor volumen/precio pero menor margen porcentual; los transaccionales compran productos sueltos con mayor margen unitario. Implicación: maximizar margen porcentual en la oferta puede ser contraproducente para capturar clientes de alto valor.

**5. Sub-cluster anómalo detectado automáticamente — validación de robustez**  
Los 7 clientes con CLTV negativo (detectados manualmente en Fase 5) fueron recuperados exactamente por K-Means como cuarto cluster. La concordancia exacta valida que el modelo no es sensible a la inicialización aleatoria ni a los hiperparámetros elegidos.

**6. ARI=0,358 cuantifica pérdida de información al reducir dimensionalidad**  
La diferencia entre asignaciones en espacio original (X_scaled) y en espacio reducido (PC1+PC2, 64,3 % de varianza) es significativa: ARI=0,358 implica que el 35,7 % de varianza descartada contiene información discriminativa real. Justifica el uso del espacio original para clustering, reservando PCA para visualización únicamente.

### Limitaciones

| Limitación | Impacto |
|:-----------|:--------|
| Dataset de una sola empresa (Madrid, sector salud) | Resultados no generalizables sin validación externa |
| Periodo 2020–2025 incluye distorsión COVID | Los patrones de compra de 2020–2021 pueden no ser representativos |
| CLTV histórico, no predictivo | No hay modelo de churn ni estimación de valor futuro |
| 79,5 % compradores únicos | Alta incertidumbre en proyecciones de retención para la mayoría del catálogo |
| Snapshots de inventario no modelados | `inventory` y `central_inventory` quedan fuera del DWH por ausencia de histórico |

### Trabajo futuro

1. **Modelo predictivo de churn** para recurrentes premium: regresión logística o supervivencia (Cox) con las features de `customer_360`.
2. **Segmentación dinámica con actualización mensual** vía pipeline programado: `run_etl.py` + re-clustering sobre ventana deslizante.
3. **Análisis de cesta de la compra** por segmento: reglas de asociación (Apriori) sobre `fact_ventas` para identificar patrones de co-compra entre productos de salud.
4. **Incorporación de variables geográficas** (`zona_id`, `tipo_area`) como features en el modelo de clustering para detectar heterogeneidad espacial.

---

## 10. Detalles Técnicos del ETL

### Scripts principales y transformaciones

El ETL se ejecuta vía `python src/etl/run_etl.py`, que orquesta 9 pasos secuenciales usando SQLAlchemy para conexiones tipadas.

**Ejemplo de transformación en `dim_cliente` (paso 7):**

```sql
INSERT INTO dwh.dim_cliente (
    cliente_id, nombre, email, fecha_alta, zona_predominante_id,
    aov, margin_rate, meses_activo, n_pedidos, return_rate, cltv
)
SELECT
    c.customer_id,
    c.name,
    c.email,
    MIN(s.sale_date) AS fecha_alta,
    MODE() WITHIN GROUP (ORDER BY z.zone_id) AS zona_predominante_id,
    AVG(s.total / si.quantity) AS aov,
    SUM(si.subtotal - si.quantity * cp.unit_cost) / SUM(si.subtotal) AS margin_rate,
    EXTRACT(EPOCH FROM MAX(s.sale_date) - MIN(s.sale_date)) / 2592000 AS meses_activo,
    COUNT(DISTINCT s.sale_id) AS n_pedidos,
    COALESCE(SUM(CASE WHEN r.return_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(DISTINCT s.sale_id), 0) AS return_rate,
    SUM(si.subtotal - si.quantity * cp.unit_cost) - COALESCE(SUM(r.quantity * cp.unit_cost), 0) AS cltv
FROM public.customer c
JOIN public.sale s ON c.customer_id = s.customer_id
JOIN public.sale_item si ON s.sale_id = si.sale_id
JOIN central_product cp ON si.product_id = cp.product_id
LEFT JOIN public.return_item r ON si.sale_item_id = r.sale_item_id
LEFT JOIN public.store st ON s.store_id = st.store_id
LEFT JOIN public.city_zone z ON st.postal_code = z.postal_code
GROUP BY c.customer_id, c.name, c.email;
```

**Optimizaciones implementadas:**
- **Batching:** Procesamiento en lotes de 1.000 filas para evitar memory overflow.
- **Índices temporales:** Creación de índices en tablas staging durante carga.
- **Validaciones:** CHECK constraints en tablas de hechos para integridad (e.g., quantity > 0).

### Manejo de errores y logging

- **Try-except blocks:** Captura de excepciones SQL con rollback automático.
- **Logging:** Uso de `logging` module con niveles INFO/ERROR; salida a `etl.log`.
- **Idempotencia:** Scripts verifican existencia previa antes de INSERT para evitar duplicados.

---

## 11. Esquemas de Base de Datos y Consultas

### Esquema DWH (PostgreSQL)

**Tabla `fact_ventas`:**

```sql
CREATE TABLE dwh.fact_ventas (
    venta_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    date_id INT NOT NULL REFERENCES dwh.dim_fecha(date_id),
    cliente_id BIGINT NOT NULL REFERENCES dwh.dim_cliente(cliente_id),
    producto_id BIGINT NOT NULL REFERENCES dwh.dim_producto(producto_id),
    tienda_id BIGINT NOT NULL REFERENCES dwh.dim_tienda(tienda_id),
    oferta_id BIGINT NOT NULL REFERENCES dwh.dim_oferta(oferta_id),
    sale_id INT NOT NULL,
    sale_item_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL,
    unit_cost NUMERIC(10,2) NOT NULL,
    subtotal NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    margen_bruto NUMERIC(12,2) NOT NULL
);
```

**Consulta ejemplo: CLTV por zona**

```sql
SELECT
    z.nombre_zona,
    COUNT(DISTINCT c.cliente_id) AS n_clientes,
    SUM(c.cltv) AS cltv_total,
    AVG(c.cltv) AS cltv_medio
FROM dwh.dim_cliente c
JOIN dwh.dim_zona z ON c.zona_predominante_id = z.zona_id
GROUP BY z.nombre_zona
ORDER BY cltv_total DESC;
```

### Rendimiento y optimización

- **Particionamiento:** `fact_ventas` particionada por `date_id` (mensual) para queries temporales.
- **Materialized views:** `customer_360` como MV para acelerar dashboard.
- **Vacuum y analyze:** Automático post-ETL para mantener estadísticas actualizadas.
