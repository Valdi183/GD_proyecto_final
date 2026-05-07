# Proyecto Final — Gestión de Datos
**Ingeniería Matemática · UAX · Curso 2025/2026**

Entorno analítico completo sobre la BD operacional `saleshealth`
(empresa de venta de 50 productos de salud).

---

## Requisitos previos

- PostgreSQL 18 en `localhost:5432`
- Python 3.12
- Dependencias: `pip install -r requirements.txt`

---

## Configuración inicial

```bash
# 1. Crear la base de datos
createdb -U postgres -E UTF8 --lc-collate=C --lc-ctype=C -T template0 saleshealth

# 2. Restaurar el dump
pg_restore -U postgres -d saleshealth --no-owner --no-privileges -v saleshealthBackupGD.sql

# 3. Crear el archivo .env (ver .env.example)
# 4. Aplicar limpieza de datos
python src/limpieza/limpieza.py
```

---

## Estructura del proyecto

```
GD_proyecto_final/
├── src/
│   ├── exploracion/      # Fase 1 — exploración y auditoría de la BD
│   ├── limpieza/         # Fase 1 — correcciones sobre schema public
│   ├── etl/              # Fase 4 — pipeline public → dwh → marts
│   └── dashboard/        # Fase 7 — app Streamlit
├── notebooks/            # Fases 5-6 — análisis CLTV, PCA y clustering
├── reports/              # Informes generados (exploración, decisiones)
├── requirements.txt
├── saleshealthBackupGD.sql
└── .env                  # Credenciales locales (no versionado)
```

---

## Arquitectura de datos

```
public (operacional)
  └─ ETL ─► dwh (modelo dimensional estrella — Kimball)
              └─ ETL ─► marts (customer_360, métricas CLTV)
                          └─► notebooks / dashboard
```

---

## Fases del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Exploración, limpieza e integridad referencial | ✅ Completa |
| 2 | Diagrama Entidad-Relación (17 tablas operacionales) | 🔄 En curso |
| 3 | Modelo dimensional (estrella Kimball) | ⏳ Pendiente |
| 4 | Pipeline ETL Python + SQLAlchemy | ⏳ Pendiente |
| 5 | Métricas de cliente: CLTV, AOV, Return Rate | ⏳ Pendiente |
| 6 | PCA + clustering de clientes | ⏳ Pendiente |
| 7 | Dashboard Streamlit (extra) | ⏳ Pendiente |
| 8 | Documento técnico final | ⏳ Pendiente |

---

## Scripts principales

| Script | Descripción |
|--------|-------------|
| `src/exploracion/explorar_bd.py` | Auditoría completa de la BD (Pasadas 1 y 2) |
| `src/limpieza/limpieza.py` | Limpieza idempotente sobre schema `public` |
| `src/etl/run_etl.py` | *(Fase 4)* Punto de entrada del pipeline ETL |

---

## Decisiones de diseño

Ver [`reports/decisiones_limpieza.md`](reports/decisiones_limpieza.md)
para el registro de decisiones de limpieza (D01–D07).
