"""
clusters.py — Persiste cluster_id y cluster_label en marts.customer_360.

Llamada desde el notebook 06_clustering.ipynb (S6) con df_clusters explícito,
o desde run_etl.py (paso 11) sin df_clusters — en ese caso carga desde
data/processed/cluster_assignments.parquet generado por el notebook.
"""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

log = logging.getLogger(__name__)

ASSIGNMENTS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "processed" / "cluster_assignments.parquet"
)


def cargar(conn, df_clusters=None) -> int:
    """
    Actualiza cluster_id y cluster_label en marts.customer_360.

    Parámetros
    ----------
    conn        : SQLAlchemy Connection (dentro de begin())
    df_clusters : DataFrame con columnas [customer_id, cluster_id, cluster_label].
                  Si None, carga desde ASSIGNMENTS_PATH.

    Returns
    -------
    int : número de clientes actualizados
    """
    if df_clusters is None:
        if not ASSIGNMENTS_PATH.exists():
            raise FileNotFoundError(
                f"Assignments no encontrados: {ASSIGNMENTS_PATH}. "
                "Ejecuta el notebook 06_clustering.ipynb (S6) primero."
            )
        df_clusters = pd.read_parquet(ASSIGNMENTS_PATH)
        log.info(
            "clusters: assignments cargados desde %s (%d filas).",
            ASSIGNMENTS_PATH, len(df_clusters),
        )

    required = {"customer_id", "cluster_id", "cluster_label"}
    missing = required - set(df_clusters.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en df_clusters: {missing}")

    conn.execute(text("""
        ALTER TABLE marts.customer_360
            ADD COLUMN IF NOT EXISTS cluster_id    INT,
            ADD COLUMN IF NOT EXISTS cluster_label VARCHAR(50)
    """))

    rows = (
        df_clusters[["cluster_id", "cluster_label", "customer_id"]]
        .to_dict("records")
    )
    conn.execute(
        text("""
            UPDATE marts.customer_360
               SET cluster_id    = :cluster_id,
                   cluster_label = :cluster_label
             WHERE customer_id   = :customer_id
        """),
        rows,
    )

    n_ok = conn.execute(
        text("SELECT COUNT(*) FROM marts.customer_360 WHERE cluster_id IS NOT NULL")
    ).scalar()
    n_total = conn.execute(
        text("SELECT COUNT(*) FROM marts.customer_360")
    ).scalar()
    assert n_ok == n_total, (
        f"clusters: {n_total - n_ok} clientes sin cluster_id tras UPDATE."
    )

    log.info(
        "clusters: %d clientes actualizados con cluster_id y cluster_label.", n_ok
    )
    return n_ok
