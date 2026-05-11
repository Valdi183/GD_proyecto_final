"""
app.py — Página 1: Panel Ejecutivo del dashboard saleshealth.

Lanzar desde GD_proyecto_final/:
    streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CLUSTER_COLORS, CLUSTER_ORDER, fmt_eur, fmt_eur_corto, load_data

st.set_page_config(
    page_title="saleshealth — Customer Analytics",
    page_icon="📊",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Panel Ejecutivo")
st.caption("saleshealth · 50 productos de salud · Análisis de 5.750 clientes activos")

df = load_data()

# ── KPIs ──────────────────────────────────────────────────────────────────────
cltv_total   = df["cltv"].sum()
n_clientes   = len(df)
cltv_medio   = df["cltv"].mean()
prem         = df[df["cluster_label"] == "Recurrentes premium"]
pct_valor    = prem["cltv"].sum() / cltv_total * 100
pct_clientes = len(prem) / n_clientes * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "CLTV Total",
    fmt_eur(cltv_total),
    help="Suma del margen neto histórico ajustado por devoluciones de todos los clientes.",
)
c2.metric(
    "Clientes Activos",
    f"{n_clientes:,}".replace(",", "."),
    help="Clientes con al menos una venta registrada en el periodo analizado.",
)
c3.metric(
    "CLTV Medio",
    fmt_eur(cltv_medio),
    help="Valor de vida medio por cliente (margen neto histórico).",
)
c4.metric(
    "Concentración",
    f"{pct_valor:.1f}% del valor",
    help=(
        f"El {pct_clientes:.1f}% de clientes (Recurrentes premium) "
        f"genera el {pct_valor:.1f}% del CLTV total."
    ),
)

st.divider()

# ── Segmentos: donut + tabla ──────────────────────────────────────────────────
st.subheader("Distribución de clientes por segmento")

cluster_stats = (
    df.groupby("cluster_label", observed=True)
    .agg(
        n_clientes=("customer_id", "count"),
        cltv_total=("cltv", "sum"),
        cltv_medio=("cltv", "mean"),
    )
    .reindex(CLUSTER_ORDER)
)
cluster_stats["pct_clientes"] = cluster_stats["n_clientes"] / n_clientes * 100

col_donut, col_tabla = st.columns([1.1, 1])

with col_donut:
    fig_donut = go.Figure(
        go.Pie(
            labels=cluster_stats.index.tolist(),
            values=cluster_stats["n_clientes"].tolist(),
            hole=0.4,
            marker_colors=[CLUSTER_COLORS[lbl] for lbl in cluster_stats.index],
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,} clientes<br>%{percent}<extra></extra>",
        )
    )
    fig_donut.update_layout(
        showlegend=False,
        margin=dict(t=30, b=10, l=10, r=10),
        height=320,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_tabla:
    tabla = cluster_stats.reset_index()[
        ["cluster_label", "n_clientes", "pct_clientes", "cltv_total", "cltv_medio"]
    ].copy()
    st.dataframe(
        tabla,
        column_config={
            "cluster_label": st.column_config.TextColumn("Segmento"),
            "n_clientes":    st.column_config.NumberColumn("Clientes",       format="%d"),
            "pct_clientes":  st.column_config.NumberColumn("% Clientes",     format="%.1f%%"),
            "cltv_total":    st.column_config.NumberColumn("CLTV Total (€)", format="%.0f"),
            "cltv_medio":    st.column_config.NumberColumn("CLTV Medio (€)", format="%.0f"),
        },
        hide_index=True,
        use_container_width=True,
        height=210,
    )
    st.info(
        f"💡 El **{pct_clientes:.1f}% de clientes** (Recurrentes premium) "
        f"genera el **{pct_valor:.1f}%** del valor del negocio."
    )

st.divider()

# ── Aportación por segmento ───────────────────────────────────────────────────
st.subheader("Aportación de cada segmento al CLTV total")

# Productos a pérdida (CLTV total ≈ -400€) tendrá barra invisible en escala
# lineal, pero el texto fuera de la barra mostrará el valor exacto (Opción B).
bar_seg = cluster_stats.reset_index().sort_values("cltv_total", ascending=True)
fig_seg = px.bar(
    bar_seg,
    x="cltv_total",
    y="cluster_label",
    orientation="h",
    color="cluster_label",
    color_discrete_map=CLUSTER_COLORS,
    labels={"cltv_total": "CLTV Total (€)", "cluster_label": ""},
    text=bar_seg["cltv_total"].apply(fmt_eur_corto),
)
fig_seg.update_layout(
    showlegend=False,
    height=280,
    margin=dict(t=10, b=10, l=10, r=200),
    xaxis_title="CLTV Total (€)",
)
fig_seg.update_traces(textposition="outside")
st.plotly_chart(fig_seg, use_container_width=True)

st.divider()

# ── Top 10 distritos ──────────────────────────────────────────────────────────
st.subheader("Top 10 distritos por CLTV")

top_dist = (
    df.groupby("distrito")["cltv"]
    .sum()
    .nlargest(10)
    .reset_index()
    .sort_values("cltv", ascending=True)
)
fig_dist = px.bar(
    top_dist,
    x="cltv",
    y="distrito",
    orientation="h",
    color_discrete_sequence=["#3498DB"],
    labels={"cltv": "CLTV Total (€)", "distrito": ""},
    text=top_dist["cltv"].apply(fmt_eur_corto),
)
fig_dist.update_layout(
    showlegend=False,
    height=370,
    margin=dict(t=10, b=10, l=10, r=120),
    xaxis_title="CLTV Total (€)",
)
fig_dist.update_traces(textposition="outside")
st.plotly_chart(fig_dist, use_container_width=True)

st.divider()

# ── Segunda fila de KPIs financieros ─────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ingresos totales",   "9.341.505,20 €")
col2.metric("Margen bruto",       "3.779.316,80 €")
col3.metric("Tasa de devolución", "2,9%")
col4.metric("Ticket medio",       "227,20 €")

st.divider()

# ── Estado del negocio ────────────────────────────────────────────────────────
st.subheader("Estado del negocio")
st.success(
    "✅ Base de clientes recurrentes sólida — "
    "el 13% de clientes genera el 91% del valor."
)
st.warning(
    "⚠️ Alta concentración en segmento premium — "
    "riesgo de dependencia en 750 clientes."
)
st.info(
    "ℹ️ Tasa de devolución del 2,9% — dentro de "
    "parámetros normales para retail de salud."
)

st.divider()
st.caption(
    "Análisis sobre 5.750 clientes activos · "
    "Periodo 2020-2026 · 50 productos · "
    "20 tiendas en Madrid"
)
