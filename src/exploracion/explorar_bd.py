#!/usr/bin/env python3
"""
Fase 1 — Pasadas 1 y 2: estructura, volúmenes, nulos, fechas, estadísticas y duplicados.

Uso:
    cd GD_proyecto_final
    python src/exploracion/explorar_bd.py
    python src/exploracion/explorar_bd.py --output reports/exploracion.md

Requiere: .env en GD_proyecto_final/ con DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────────────────────────────────────

def get_engine():
    # Carga .env buscando desde el directorio actual hacia arriba
    load_dotenv()

    required = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(
            f"[ERROR] Variables de entorno faltantes: {', '.join(missing)}\n"
            f"Asegúrate de tener un .env en GD_proyecto_final/ con esas claves."
        )

    url = (
        f"postgresql+psycopg2://"
        f"{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    return create_engine(url)


# ─────────────────────────────────────────────────────────────────────────────
# REPORTER — acumula líneas y las vuelca en consola + fichero markdown
# ─────────────────────────────────────────────────────────────────────────────

class Reporter:
    def __init__(self, output_path: str | None = None):
        self.lines: list[str] = []
        self.output_path = output_path

    def h1(self, titulo: str):
        self.lines += ["", f"# {titulo}", "=" * 80]

    def h2(self, titulo: str):
        self.lines += ["", f"## {titulo}", "-" * 60]

    def h3(self, titulo: str):
        self.lines += ["", f"### {titulo}"]

    def write(self, s: str = ""):
        self.lines.append(str(s))

    def dataframe(self, df: pd.DataFrame, max_filas: int = 300):
        if df is None or df.empty:
            self.lines.append("*(sin datos)*")
            return
        self.lines.append(df.head(max_filas).to_markdown(index=False))
        if len(df) > max_filas:
            self.lines.append(f"*... y {len(df) - max_filas} filas más (omitidas)*")

    def flush(self):
        salida = "\n".join(self.lines)
        print(salida)
        if self.output_path:
            Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self.output_path).write_text(salida, encoding="utf-8")
            print(f"\n[Informe guardado → {self.output_path}]")


# ─────────────────────────────────────────────────────────────────────────────
# TIPOS PostgreSQL que nos interesan para los chequeos
# ─────────────────────────────────────────────────────────────────────────────

TIPOS_NUMERICOS = {
    "integer", "bigint", "smallint", "numeric", "decimal",
    "real", "double precision", "money",
}
TIPOS_FECHA = {
    "date",
    "timestamp without time zone",
    "timestamp with time zone",
    "time without time zone",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — datos compartidos entre funciones
# ─────────────────────────────────────────────────────────────────────────────

def obtener_tablas(engine) -> list[str]:
    sql = text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(sql)]


def obtener_columnas(engine) -> pd.DataFrame:
    sql = """
        SELECT table_name, column_name, data_type,
               is_nullable, column_default, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """
    return pd.read_sql(sql, engine)


def obtener_pks(engine) -> dict[str, list[str]]:
    """Devuelve {tabla: [col_pk, ...]} para todas las tablas del schema public."""
    sql = """
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON  tc.constraint_name = kcu.constraint_name
            AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = 'public'
        ORDER BY tc.table_name, kcu.ordinal_position
    """
    df = pd.read_sql(sql, engine)
    return df.groupby("table_name")["column_name"].apply(list).to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# PASADA 1 — ESTRUCTURA
# ─────────────────────────────────────────────────────────────────────────────

def pasada_1_estructura(engine, rep: Reporter):
    rep.h1("PASADA 1 — ESTRUCTURA DEL SCHEMA PUBLIC")
    rep.write(f"Ejecutada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1.1 Columnas, tipos y nulabilidad — tabla por tabla
    rep.h2("1.1 Columnas, tipos y nulabilidad")
    cols_df = obtener_columnas(engine)
    for tabla, grp in cols_df.groupby("table_name"):
        rep.h3(tabla)
        rep.dataframe(grp.drop(columns="table_name").reset_index(drop=True))

    # 1.2 Claves primarias declaradas
    rep.h2("1.2 Claves primarias declaradas")
    sql_pk = """
        SELECT tc.table_name,
               STRING_AGG(kcu.column_name, ', '
                          ORDER BY kcu.ordinal_position) AS pk_columns
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON  tc.constraint_name = kcu.constraint_name
            AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = 'public'
        GROUP BY tc.table_name
        ORDER BY tc.table_name
    """
    rep.dataframe(pd.read_sql(sql_pk, engine))

    # 1.3 Claves foráneas declaradas
    rep.h2("1.3 Claves foráneas declaradas")
    sql_fk = """
        SELECT
            tc.table_name    AS tabla_origen,
            kcu.column_name  AS columna_origen,
            ccu.table_name   AS tabla_destino,
            ccu.column_name  AS columna_destino,
            tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON  tc.constraint_name = kcu.constraint_name
            AND tc.table_schema    = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON  ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema    = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema    = 'public'
        ORDER BY tc.table_name, kcu.column_name
    """
    rep.dataframe(pd.read_sql(sql_fk, engine))

    # 1.4 Índices (incluidos los no-PK — revelan FKs implícitas y accesos frecuentes)
    rep.h2("1.4 Índices declarados (todos, incluyendo no-PK)")
    sql_idx = """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """
    rep.dataframe(pd.read_sql(sql_idx, engine))


# ─────────────────────────────────────────────────────────────────────────────
# PASADA 2 — VOLÚMENES, NULOS, FECHAS, ESTADÍSTICAS Y DUPLICADOS
# ─────────────────────────────────────────────────────────────────────────────

def pasada_2_volumenes(engine, rep: Reporter, tablas: list[str]):
    rep.h1("PASADA 2 — VOLÚMENES, NULOS, FECHAS, ESTADÍSTICAS Y DUPLICADOS")
    rep.h2("2.1 Conteo de filas por tabla")

    filas = []
    with engine.connect() as conn:
        for tabla in tablas:
            cnt = conn.execute(text(f'SELECT COUNT(*) FROM public."{tabla}"')).scalar()
            filas.append({"tabla": tabla, "filas": cnt})

    df = pd.DataFrame(filas, columns=["tabla", "filas"]).sort_values("filas", ascending=False)
    rep.dataframe(df)
    rep.write(f"\nTotal tablas: {len(df)} — Total filas: {df['filas'].sum():,}")


def pasada_2_nulos(engine, rep: Reporter, cols_df: pd.DataFrame):
    rep.h2("2.2 Columnas con valores nulos")

    resultados = []
    with engine.connect() as conn:
        for tabla, grp in cols_df.groupby("table_name"):
            cols = grp["column_name"].tolist()
            # Un solo SELECT por tabla — una pasada en lugar de N
            partes = [
                f'SUM(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) AS "{c}"'
                for c in cols
            ]
            sql = f'SELECT {", ".join(partes)} FROM public."{tabla}"'
            fila = conn.execute(text(sql)).fetchone()
            for col, n_nulos in zip(cols, fila):
                if n_nulos and n_nulos > 0:
                    resultados.append({"tabla": tabla, "columna": col, "nulos": n_nulos})

    if resultados:
        df = pd.DataFrame(resultados).sort_values(["tabla", "nulos"], ascending=[True, False])
        rep.dataframe(df)
        rep.write(f"\n**Total columnas con al menos un nulo: {len(resultados)}**")
    else:
        rep.write("Sin valores nulos en ninguna columna del schema.")


def pasada_2_fechas(engine, rep: Reporter, cols_df: pd.DataFrame):
    rep.h2("2.3 Rangos de fechas — detección de valores absurdos")
    rep.write("*(Fechas < 2010 o > 2030 merecen investigación)*\n")

    date_cols = cols_df[cols_df["data_type"].isin(TIPOS_FECHA)]
    if date_cols.empty:
        rep.write("No hay columnas de tipo fecha en el schema.")
        return

    resultados = []
    with engine.connect() as conn:
        for tabla, grp in date_cols.groupby("table_name"):
            for col in grp["column_name"]:
                sql = f'SELECT MIN("{col}"), MAX("{col}") FROM public."{tabla}"'
                mn, mx = conn.execute(text(sql)).fetchone()
                alerta = ""
                if mn and (mn.year < 2010 if hasattr(mn, "year") else False):
                    alerta += "MIN_SOSPECHOSO "
                if mx and (mx.year > 2030 if hasattr(mx, "year") else False):
                    alerta += "MAX_SOSPECHOSO"
                resultados.append({
                    "tabla": tabla, "columna": col,
                    "min": mn, "max": mx,
                    "alerta": alerta.strip() or "ok",
                })

    rep.dataframe(pd.DataFrame(resultados))


def pasada_2_stats_numericas(engine, rep: Reporter, cols_df: pd.DataFrame):
    rep.h2("2.4 Estadísticas básicas — columnas numéricas")
    rep.write("*(min < 0 en cantidades/precios, stddev muy alta o avg muy alejado del max son señales de alerta)*\n")

    num_cols = cols_df[cols_df["data_type"].isin(TIPOS_NUMERICOS)]
    if num_cols.empty:
        rep.write("No hay columnas numéricas en el schema.")
        return

    resultados = []
    with engine.connect() as conn:
        for tabla, grp in num_cols.groupby("table_name"):
            for col in grp["column_name"]:
                sql = f"""
                    SELECT
                        COUNT("{col}")           AS no_nulos,
                        MIN("{col}")::numeric    AS min,
                        MAX("{col}")::numeric    AS max,
                        AVG("{col}")::numeric    AS avg,
                        STDDEV("{col}")::numeric AS stddev
                    FROM public."{tabla}"
                """
                try:
                    r = conn.execute(text(sql)).fetchone()
                    resultados.append({
                        "tabla":    tabla,
                        "columna":  col,
                        "no_nulos": int(r[0]) if r[0] is not None else 0,
                        "min":      round(float(r[1]), 4) if r[1] is not None else None,
                        "max":      round(float(r[2]), 4) if r[2] is not None else None,
                        "avg":      round(float(r[3]), 4) if r[3] is not None else None,
                        "stddev":   round(float(r[4]), 4) if r[4] is not None else None,
                    })
                except Exception as e:
                    resultados.append({
                        "tabla": tabla, "columna": col,
                        "no_nulos": None, "min": None, "max": None,
                        "avg": None, "stddev": f"ERROR: {e}",
                    })

    rep.dataframe(pd.DataFrame(resultados))


def pasada_2_duplicados(engine, rep: Reporter, cols_df: pd.DataFrame, pk_cols: dict):
    rep.h2("2.5 Duplicados exactos por tabla (filas no-PK idénticas)")
    rep.write("*(Si una tabla sin PK tiene filas_extra > 0, hay duplicados reales)*\n")

    resultados = []
    with engine.connect() as conn:
        for tabla, grp in cols_df.groupby("table_name"):
            pks      = pk_cols.get(tabla, [])
            non_pk   = [c for c in grp["column_name"].tolist() if c not in pks]

            if not non_pk:
                resultados.append({
                    "tabla": tabla, "grupos_dup": 0,
                    "filas_extra": 0, "nota": "solo columna PK",
                })
                continue

            cols_q = ", ".join(f'"{c}"' for c in non_pk)
            sql = f"""
                SELECT
                    COALESCE(SUM(cnt - 1), 0) AS filas_extra,
                    COUNT(*)                   AS grupos_dup
                FROM (
                    SELECT {cols_q}, COUNT(*) AS cnt
                    FROM public."{tabla}"
                    GROUP BY {cols_q}
                    HAVING COUNT(*) > 1
                ) sub
            """
            try:
                r = conn.execute(text(sql)).fetchone()
                resultados.append({
                    "tabla":       tabla,
                    "grupos_dup":  int(r[1]),
                    "filas_extra": int(r[0]),
                    "nota":        "",
                })
            except Exception as e:
                resultados.append({
                    "tabla": tabla, "grupos_dup": None,
                    "filas_extra": None, "nota": f"ERROR: {e}",
                })

    df = pd.DataFrame(resultados)
    rep.dataframe(df)
    n_con = (df["filas_extra"].fillna(0) > 0).sum()
    rep.write(f"\n**Tablas con al menos un duplicado: {n_con} de {len(df)}**")


def pasada_2_coherencia_temporal(engine, rep: Reporter, cols_df: pd.DataFrame):
    rep.h2("2.6 Coherencia temporal: fecha de alta del cliente vs primera venta")

    # Detectamos qué columnas de fecha tiene customer
    customer_dates = cols_df[
        (cols_df["table_name"] == "customer") &
        (cols_df["data_type"].isin(TIPOS_FECHA))
    ]["column_name"].tolist()

    # Detectamos qué columna de fecha tiene sale
    sale_dates = cols_df[
        (cols_df["table_name"] == "sale") &
        (cols_df["data_type"].isin(TIPOS_FECHA))
    ]["column_name"].tolist()

    rep.write(f"Columnas de fecha en `customer`: {customer_dates or '(ninguna)'}")
    rep.write(f"Columnas de fecha en `sale`:     {sale_dates or '(ninguna)'}")

    if not customer_dates:
        rep.write("\n`customer` no tiene columnas de fecha — check no aplica.")
        return
    if not sale_dates:
        rep.write("\n`sale` no tiene columnas de fecha — check no aplica.")
        return

    col_alta  = customer_dates[0]   # usamos la primera que encontremos
    col_venta = sale_dates[0]

    rep.write(
        f"\nComparando `customer.{col_alta}` (fecha de alta) "
        f"con MIN(`sale.{col_venta}`) (primera venta).\n"
    )

    sql = f"""
        SELECT
            c.customer_id,
            c."{col_alta}"          AS fecha_alta,
            MIN(s."{col_venta}")    AS primera_venta,
            MIN(s."{col_venta}") - c."{col_alta}" AS dias_diferencia
        FROM public.customer c
        JOIN public.sale s ON s.customer_id = c.customer_id
        GROUP BY c.customer_id, c."{col_alta}"
        HAVING MIN(s."{col_venta}") < c."{col_alta}"
        ORDER BY dias_diferencia
        LIMIT 30
    """
    try:
        df = pd.read_sql(sql, engine)
        if df.empty:
            rep.write("OK — ningún cliente tiene primera venta anterior a su fecha de alta.")
        else:
            rep.write(
                f"**{len(df)} clientes con primera venta ANTERIOR a su fecha de alta "
                f"(muestra de hasta 30):**"
            )
            rep.dataframe(df)
    except Exception as e:
        rep.write(f"Error al ejecutar el check: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Exploración Fase 1 — BD saleshealth (Pasadas 1 y 2)"
    )
    parser.add_argument(
        "--output",
        default="reports/exploracion.md",
        help="Ruta del fichero de salida (default: reports/exploracion.md)",
    )
    args = parser.parse_args()

    print("[INFO] Conectando a la base de datos...")
    engine = get_engine()

    rep = Reporter(output_path=args.output)
    rep.h1("INFORME DE EXPLORACIÓN — saleshealth")
    rep.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Cargamos metadatos una sola vez y los compartimos entre funciones
    print("[INFO] Cargando metadatos del schema...")
    tablas   = obtener_tablas(engine)
    cols_df  = obtener_columnas(engine)
    pk_cols  = obtener_pks(engine)

    if not tablas:
        sys.exit(
            "\n[ERROR] No se encontraron tablas en el schema 'public'.\n"
            "Posibles causas:\n"
            "  1) El dump no se restauró correctamente (revisa los errores de pg_restore).\n"
            "  2) Las tablas están en otro schema (comprueba en DBeaver con:\n"
            "     SELECT table_schema, COUNT(*) FROM information_schema.tables\n"
            "     WHERE table_type='BASE TABLE' GROUP BY table_schema;)\n"
            "  3) DB_NAME en .env no apunta a la BD restaurada.\n"
            f"  4) BD actual: ejecuta SELECT current_database(); en DBeaver.\n"
        )

    rep.write(f"\nTablas en schema `public`: {len(tablas)}")
    rep.write(f"`{'`, `'.join(tablas)}`")

    # ── Pasada 1 ──────────────────────────────────────────────────────────────
    print("[INFO] Pasada 1: estructura...")
    pasada_1_estructura(engine, rep)

    # ── Pasada 2 ──────────────────────────────────────────────────────────────
    print("[INFO] Pasada 2.1: volúmenes...")
    pasada_2_volumenes(engine, rep, tablas)

    print("[INFO] Pasada 2.2: nulos...")
    pasada_2_nulos(engine, rep, cols_df)

    print("[INFO] Pasada 2.3: rangos de fechas...")
    pasada_2_fechas(engine, rep, cols_df)

    print("[INFO] Pasada 2.4: estadísticas numéricas...")
    pasada_2_stats_numericas(engine, rep, cols_df)

    print("[INFO] Pasada 2.5: duplicados (puede tardar un momento)...")
    pasada_2_duplicados(engine, rep, cols_df, pk_cols)

    print("[INFO] Pasada 2.6: coherencia temporal cliente-ventas...")
    pasada_2_coherencia_temporal(engine, rep, cols_df)

    # ── Volcado final ──────────────────────────────────────────────────────────
    rep.flush()
    print("\n[OK] Exploración completada.")


if __name__ == "__main__":
    main()
