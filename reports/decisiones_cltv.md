# Decisiones de diseño — CLTV histórico (Fase 5)

Registro de decisiones técnicas adoptadas durante la implementación de
`marts.customer_360`. Cada entrada tiene un identificador D-CLTV-XX para
facilitar la trazabilidad entre código, tests y documentación.

---

## D-CLTV-01 — Definición de CLTV histórico

**Decisión:** CLTV = valor histórico real (suma de margen neto generado), no
proyección futura ni modelo predictivo.

**Justificación:** El dataset es un periodo cerrado; no existe información
suficiente para calibrar una tasa de churn o un horizonte temporal futuro.
El CLTV histórico es ground truth para segmentación y sirve de variable
objetivo en modelos posteriores (Fase 6).

---

## D-CLTV-02 — Granularidad: una fila por cliente

**Decisión:** `customer_360` contiene exactamente una fila por `customer_id`.
Sin agrupación por periodo ni por canal.

**Justificación:** El análisis de Fase 5 (distribuciones, Lorenz, cohortes)
opera a nivel cliente. Granularidades más finas se resuelven en notebooks
con consultas ad-hoc sobre `dwh.fact_ventas`.

---

## D-CLTV-03 — Ingresos brutos como base de AOV

**Decisión:** `aov = ingresos_brutos / n_pedidos` (sin deducir devoluciones).

**Justificación:** AOV mide el ticket medio de compra en el momento de la
transacción. El ajuste por devoluciones se aplica en `margen_neto` / `cltv`,
no en el ticket de compra.

---

## D-CLTV-04 — Fórmula de margen neto (corregida)

**Decisión:**
```
margen_neto = SUM(margen_bruto) − SUM(importe_devuelto) + SUM(costo_devuelto)
```

**Corrección respecto a versión original:** La versión inicial restaba
`costo_devuelto`, lo que producía resultados incorrectos.

**Ejemplo de verificación unitaria:**
- Venta: precio = 100 €, costo = 60 €, margen_bruto = 40 €
- Devolución completa: importe_devuelto = 100 €, costo_devuelto = 60 €
- Resultado esperado: margen_neto = 0 €
- Fórmula corregida: 40 − 100 + 60 = 0 € ✓
- Fórmula incorrecta: 40 − 60 = −20 € ✗

---

## D-CLTV-05 — CLTV = margen_neto (identidad)

**Decisión:** `cltv = margen_neto` (calculado directamente como diferencia de
sumas NUMERIC, no como producto de componentes).

**Justificación:** Evita acumulación de errores de redondeo en divisiones
intermedias. Los componentes AOV, margin_rate, freq_mensual se calculan como
métricas descriptivas / features para ML, no como ruta de cálculo de cltv.

---

## D-CLTV-06 — AOV: bruto, no neto

Ver D-CLTV-03.

---

## D-CLTV-07 — margin_rate nullable por diseño defensivo

**Decisión:** `margin_rate NUMERIC(7,4)` es nullable; se calcula con CASE WHEN.

**Justificación:** Si `ingresos_brutos = 0`, la división sería indefinida.
En este dataset nunca ocurre (todo cliente tiene al menos un `sale_item` con
`subtotal > 0` por CHECK constraint), pero la columna admite NULL para
proteger ejecuciones futuras con datos distintos.

---

## D-CLTV-08 — freq_mensual = n_pedidos / meses_activo

**Decisión:** Frecuencia media de compra mensual, calculada sobre los meses
en los que el cliente estuvo activo (no sobre el total de meses del periodo).

**Alternativa descartada:** Dividir por la duración total del ciclo de vida
(última − primera compra en meses). Se descarta porque infla la frecuencia
de clientes con pocas compras muy concentradas y castiga a clientes con
actividad discontinua larga.

---

## D-CLTV-09 — return_rate = LEAST(items_devueltos / items_vendidos, 1.0)

**Decisión:** Tasa de devolución a nivel item, acotada a [0, 1] con LEAST.

**Justificación del LEAST:** Por como se registran las devoluciones, puede
ocurrir que `n_items_devueltos > n_items_vendidos` si se aplican correcciones
manuales. LEAST previene tasas > 100 % que distorsionarían el análisis.

---

## D-CLTV-10 — meses_activo: mínimo 1

**Decisión:** `meses_activo = COUNT(DISTINCT date_id / 100)` (división entera
da YYYYMM). Mínimo 1 por construcción (todo cliente tiene al menos una venta).

**Ventaja sobre alternativas:** Cuenta meses calendario con actividad, no
duración del ciclo de vida. Un cliente con compras el 31-ene y el 1-feb tiene
`meses_activo = 2`, no 1.

---

## D-CLTV-11 — recency_dias relativo al snapshot

**Decisión:**
```sql
recency_dias = MAX(fecha en dwh.fact_ventas) − ultima_compra
```
La fecha de referencia se calcula como MAX del dataset (CTE `max_fecha`),
no como `CURRENT_DATE` ni como fecha hardcodeada.

**Justificación:** Garantiza reproducibilidad: re-ejecutar el ETL sobre el
mismo dataset produce el mismo resultado independientemente de cuándo se
ejecute.

---

## D-CLTV-12 — JOIN dim_cliente como tabla conductora

**Decisión:** El SELECT final arranca de `dwh.dim_cliente` con `JOIN ventas`
(no `LEFT JOIN`), lo que garantiza que sólo se incluyen clientes con ventas.

**Implicación:** `COUNT(customer_360) == COUNT(dim_cliente)` es un assert
válido: si falla, hay clientes en dim_cliente sin ventas, lo que indica un
bug en el ETL de dim_cliente o fact_ventas.

---

## D-CLTV-13 — Identidad algebraica de los componentes

**Enunciado:**
```
AOV × margin_rate × freq_mensual × meses_activo = margen_bruto_total
```

**Demostración:**
```
AOV            = ingresos_brutos / n_pedidos
margin_rate    = margen_bruto_total / ingresos_brutos
freq_mensual   = n_pedidos / meses_activo

Producto:
  (ingresos_brutos / n_pedidos)
× (margen_bruto_total / ingresos_brutos)
× (n_pedidos / meses_activo)
× meses_activo
= margen_bruto_total  ✓  (n_pedidos, ingresos_brutos, meses_activo se cancelan)
```

La identidad vincula los componentes descriptivos con el total. Se verifica
empíricamente en Test 1 de `customer_360.py` (ver D-CLTV-14).

---

## D-CLTV-14 — Tolerancia numérica en Test 1 (identidad algebraica)

**Observación:** La identidad algebraica de D-CLTV-13 es exacta en matemáticas
reales, pero introduce error de representación por el almacenamiento de
`freq_mensual` como `NUMERIC(8,4)` (4 decimales).

**Cota teórica del error:**
```
ε_freq        ≤ 0.00005            (máximo error de redondeo a 4 decimales)
max_error     ≈ AOV_max × margin_rate × ε_freq × meses_activo_max
              ≈ 1000    × 0.40       × 0.00005 × 72
              ≈ 1.44 €
```

**Resultado empírico (run 2026-05-08):**
```
max |margen_bruto_total − ROUND(aov × margin_rate × freq_mensual × meses_activo, 2)| = 1.41 €
```

Diferencia relativa: 1.41 / 3.670.369,64 ≈ 3.8 × 10⁻⁷ (< 1 ppm).

**Decisión:** Umbral del WARNING en Test 1 fijado a 2.0 € (margen de seguridad
del 39 % sobre la cota teórica de 1.44 €). Si el test supera 2.0 €, indica
un cambio en la definición de componentes, no un error numérico tolerable.

**Alternativas descartadas:**
- **Opción B (sustituir freq_mensual por n_pedidos/meses_activo en el test):**
  el test dejaría de verificar los valores almacenados en la tabla; no
  documenta la precisión real de los features que consumirá Fase 6.
- **Opción C (test exacto con 0.01 €):** fallaría en producción por el error
  de representación demostrado; umbral inválido para esta arquitectura.
