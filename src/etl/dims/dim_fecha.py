"""
dim_fecha.py — Carga de dwh.dim_fecha mediante generate_series de PostgreSQL.

Todo en SQL puro: sin pandas, sin dependencia de locale del sistema.
Los nombres de mes y día están en español en el propio SQL.

Assert: COUNT(dwh.dim_fecha) == config.DIM_FECHA_EXPECTED_ROWS.
"""

import logging

from sqlalchemy import text

from etl.config import DIM_FECHA_END, DIM_FECHA_EXPECTED_ROWS, DIM_FECHA_START

log = logging.getLogger(__name__)


def cargar(conn) -> int:
    conn.execute(text("""
        INSERT INTO dwh.dim_fecha (
            date_id, fecha, anio, semestre, trimestre, mes, nombre_mes,
            semana_anio, dia_semana, nombre_dia, es_fin_de_semana, es_dia_habil
        )
        WITH calendario AS (
            SELECT d::date AS fecha
            FROM generate_series(:inicio, :fin, '1 day'::interval) d
        ),
        meses (num, nombre) AS (VALUES
            (1,'Enero'),(2,'Febrero'),(3,'Marzo'),(4,'Abril'),
            (5,'Mayo'),(6,'Junio'),(7,'Julio'),(8,'Agosto'),
            (9,'Septiembre'),(10,'Octubre'),(11,'Noviembre'),(12,'Diciembre')
        ),
        dias (num, nombre) AS (VALUES
            (1,'Lunes'),(2,'Martes'),(3,'Miércoles'),(4,'Jueves'),
            (5,'Viernes'),(6,'Sábado'),(7,'Domingo')
        )
        SELECT
            TO_CHAR(c.fecha, 'YYYYMMDD')::INT,
            c.fecha,
            EXTRACT(YEAR    FROM c.fecha)::INT,
            CASE WHEN EXTRACT(MONTH FROM c.fecha) <= 6 THEN 1 ELSE 2 END,
            EXTRACT(QUARTER FROM c.fecha)::INT,
            EXTRACT(MONTH   FROM c.fecha)::INT,
            m.nombre,
            EXTRACT(WEEK    FROM c.fecha)::INT,
            EXTRACT(ISODOW  FROM c.fecha)::INT,
            d.nombre,
            EXTRACT(ISODOW  FROM c.fecha) >= 6,
            EXTRACT(ISODOW  FROM c.fecha) <  6
        FROM calendario c
        JOIN meses m ON m.num = EXTRACT(MONTH  FROM c.fecha)::INT
        JOIN dias  d ON d.num = EXTRACT(ISODOW FROM c.fecha)::INT
    """), {"inicio": DIM_FECHA_START, "fin": DIM_FECHA_END})

    n = conn.execute(text("SELECT COUNT(*) FROM dwh.dim_fecha")).scalar()

    assert n == DIM_FECHA_EXPECTED_ROWS, (
        f"dim_fecha — cuadre fallido: esperadas={DIM_FECHA_EXPECTED_ROWS}, cargadas={n}"
    )

    log.info("dim_fecha: %d filas cargadas (%s → %s).", n, DIM_FECHA_START, DIM_FECHA_END)
    return n
