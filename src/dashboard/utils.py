"""
utils.py — Utilidades compartidas del dashboard saleshealth.

Importar desde app.py y páginas:
    from utils import CLUSTER_COLORS, CLUSTER_ORDER, fmt_eur, fmt_eur_corto, fmt_pct, load_data
"""

import os
import sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# ── Constantes visuales ───────────────────────────────────────────────────────

CLUSTER_COLORS = {
    "Recurrentes premium": "#2ECC71",
    "Compradores únicos":  "#3498DB",
    "Devolvedores":        "#E67E22",
    "Productos a pérdida": "#95A5A6",
}

CLUSTER_ORDER = [
    "Recurrentes premium",
    "Compradores únicos",
    "Devolvedores",
    "Productos a pérdida",
]

# ── Formatters ────────────────────────────────────────────────────────────────

def fmt_eur(valor: float) -> str:
    """Formato europeo completo: '1.234.567,89 €'"""
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_eur_corto(valor: float) -> str:
    """Formato corto para etiquetas de gráficas: '1,02 M€' / '305 k€' / '52 €'."""
    v = abs(valor)
    sign = "-" if valor < 0 else ""
    if v >= 1_000_000:
        return f"{sign}{v / 1_000_000:.2f} M€".replace(".", ",")
    if v >= 1_000:
        return f"{sign}{v / 1_000:.0f} k€"
    return f"{sign}{v:.0f} €"


def fmt_pct(valor: float, decimales: int = 1) -> str:
    return f"{valor:.{decimales}f}%"


# ── Conexión BD ───────────────────────────────────────────────────────────────

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    load_dotenv()
    required = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"[ERROR] Variables de entorno faltantes: {', '.join(missing)}")
    url = (
        f"postgresql+psycopg2://"
        f"{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    _engine = create_engine(url, pool_pre_ping=True)
    return _engine


# ── Datos ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    """Carga marts.customer_360 completo. Cacheado 10 min por sesión."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM marts.customer_360", conn)
    return df
