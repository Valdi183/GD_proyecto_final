"""
2_Analisis_CLTV.py — Página 2: Distribución y concentración del valor del cliente.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CLUSTER_COLORS, CLUSTER_ORDER, fmt_eur, fmt_pct, load_data

st.set_page_config(
    page_title="Análisis CLTV — saleshealth",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Análisis CLTV")
st.caption("Distribución del valor de vida del cliente · 5.750 clientes activos")

df = load_data()

# ── S1: Histograma + KPIs estadísticos ───────────────────────────────────────
st.subheader("Distribución del CLTV")

df_pos      = df[df["cltv"] > 0].copy()
n_excluidos = len(df) - len(df_pos)

col_hist, col_kpis = st.columns([2, 1])

with col_hist:
    fig_hist = px.histogram(
        df_pos,
        x="cltv",
        nbins=60,
        color_discrete_sequence=["#3498DB"],
        labels={"cltv": "CLTV (€)", "count": "Nº clientes"},
    )
    fig_hist.update_xaxes(type="log", title="CLTV (€) — escala logarítmica")
    fig_hist.update_yaxes(title="Nº clientes")
    fig_hist.update_layout(
        height=340, margin=dict(t=20, b=20, l=20, r=20), showlegend=False
    )
    st.plotly_chart(fig_hist, use_container_width=True)
    st.caption(
        f"Nota: se excluyen {n_excluidos} clientes con CLTV ≤ 0 "
        "(devoluciones superiores al margen bruto generado)."
    )

with col_kpis:
    st.metric(
        "Mediana",
        fmt_eur(df["cltv"].median()),
        help="El 50% de los clientes tiene un CLTV inferior a este valor.",
    )
    st.metric(
        "Media",
        fmt_eur(df["cltv"].mean()),
        help="Media aritmética incluyendo clientes con CLTV negativo.",
    )
    st.metric(
        "Máximo",
        fmt_eur(df["cltv"].max()),
        help="CLTV más alto registrado entre todos los clientes.",
    )
    st.metric(
        "Mínimo",
        fmt_eur(df["cltv"].min()),
        help="CLTV más bajo; negativo si las devoluciones superan el margen bruto.",
    )

st.divider()

# ── S2: Curva de Lorenz ───────────────────────────────────────────────────────
st.subheader("Concentración del valor — Curva de Lorenz")

# Lorenz se calcula sobre clientes con CLTV > 0 (negatives distorsionan la curva).
cltv_sorted = df_pos["cltv"].sort_values().values
n           = len(cltv_sorted)
cumsum      = np.cumsum(cltv_sorted)
total       = float(cumsum[-1])

lorenz_x = np.concatenate([[0.0], np.arange(1, n + 1) / n])
lorenz_y = np.concatenate([[0.0], cumsum / total])

area = 0.5 * np.sum(
    (lorenz_x[1:] - lorenz_x[:-1]) * (lorenz_y[1:] + lorenz_y[:-1])
)
gini = float(1 - 2 * area)

# Puntos Pareto: top X% genera target_pct% del CLTV.
# "Top X% genera Y%" ↔ "bottom (100-X)% tiene (100-Y)%"
# → buscar donde lorenz_y cruza (1 - Y/100).
pareto_targets = [(50, 0.50), (80, 0.20)]
pareto_points  = []
for value_pct, threshold in pareto_targets:
    idx = int(min(np.searchsorted(lorenz_y, threshold, side="left"), n))
    top_pct = (1 - lorenz_x[idx]) * 100
    pareto_points.append(
        dict(value_pct=value_pct, top_pct=top_pct, x=lorenz_x[idx] * 100, y=lorenz_y[idx] * 100)
    )

col_lorenz, col_gini = st.columns([2.5, 1])

with col_lorenz:
    fig_lorenz = go.Figure()

    fig_lorenz.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100],
        mode="lines",
        name="Igualdad perfecta",
        line=dict(color="#BDC3C7", width=1.5, dash="dash"),
        hoverinfo="skip",
    ))
    fig_lorenz.add_trace(go.Scatter(
        x=lorenz_x * 100,
        y=lorenz_y * 100,
        mode="lines",
        name="Lorenz (CLTV)",
        line=dict(color="#3498DB", width=2.5),
        hovertemplate="Bottom %{x:.1f}% de clientes<br>%{y:.1f}% del CLTV<extra></extra>",
    ))

    colors_pareto = ["#E67E22", "#E74C3C"]
    for pt, color in zip(pareto_points, colors_pareto):
        fig_lorenz.add_trace(go.Scatter(
            x=[pt["x"]], y=[pt["y"]],
            mode="markers+text",
            marker=dict(size=12, color=color),
            text=[f"Top {pt['top_pct']:.0f}% → {pt['value_pct']}% del CLTV"],
            textposition="top right",
            showlegend=False,
            hoverinfo="skip",
        ))

    fig_lorenz.update_layout(
        xaxis_title="% acumulado de clientes (de menor a mayor CLTV)",
        yaxis_title="% acumulado del CLTV total",
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
        margin=dict(t=20, b=30, l=20, r=20),
    )
    st.plotly_chart(fig_lorenz, use_container_width=True)

with col_gini:
    st.metric(
        "Coeficiente de Gini",
        f"{gini:.2f}",
        help="0 = distribución perfectamente igualitaria. 1 = un solo cliente tiene todo el valor.",
    )
    st.markdown("---")
    for pt in pareto_points:
        st.markdown(
            f"**Top {pt['top_pct']:.0f}%** de clientes genera "
            f"el **{pt['value_pct']}%** del CLTV total"
        )
        st.markdown("")
    with st.expander("¿Qué significa el Gini?"):
        st.write(
            f"Un Gini de {gini:.2f} indica concentración muy alta del valor "
            "en un pequeño grupo de clientes. En retail, valores por encima "
            "de 0,6 son habituales. El negocio depende críticamente de "
            "retener al segmento Recurrentes premium."
        )

st.divider()

# ── S3: Tabla interactiva de distritos ────────────────────────────────────────
st.subheader("Análisis por zona geográfica")
st.caption("Todos los distritos · ordenables por cualquier columna")

distritos = (
    df.groupby("distrito", observed=True)
    .agg(
        n_clientes        =("customer_id",   "count"),
        cltv_total        =("cltv",          "sum"),
        cltv_medio        =("cltv",          "mean"),
        return_rate_medio =("return_rate",   "mean"),
    )
    .reset_index()
    .sort_values("cltv_total", ascending=False)
)

st.dataframe(
    distritos,
    column_config={
        "distrito":           st.column_config.TextColumn("Distrito"),
        "n_clientes":         st.column_config.NumberColumn("Clientes",              format="%d"),
        "cltv_total":         st.column_config.NumberColumn("CLTV Total (€)",        format="%.0f"),
        "cltv_medio":         st.column_config.NumberColumn("CLTV Medio (€)",        format="%.0f"),
        "return_rate_medio":  st.column_config.NumberColumn("Tasa Devolución Media", format="%.3f"),
    },
    hide_index=True,
    use_container_width=True,
)

st.divider()

# ── S4: Características de los segmentos ─────────────────────────────────────
st.subheader("Características de los segmentos")

cluster_features = (
    df.groupby("cluster_label", observed=True)
    .agg(
        n_clientes            =("customer_id",   "count"),
        aov_mediana           =("aov",           "median"),
        margin_rate_mediana   =("margin_rate",   "median"),
        meses_activo_mediana  =("meses_activo",  "median"),
        return_rate_mediana   =("return_rate",   "median"),
        cltv_mediana          =("cltv",          "median"),
    )
    .reindex(CLUSTER_ORDER)
    .reset_index()
)

st.dataframe(
    cluster_features,
    column_config={
        "cluster_label":        st.column_config.TextColumn("Segmento"),
        "n_clientes":           st.column_config.NumberColumn("Clientes",             format="%d"),
        "aov_mediana":          st.column_config.NumberColumn("AOV mediana (€)",      format="%.0f"),
        "margin_rate_mediana":  st.column_config.NumberColumn("Margen Rate mediana",  format="%.3f"),
        "meses_activo_mediana": st.column_config.NumberColumn("Meses Activo mediana", format="%.0f"),
        "return_rate_mediana":  st.column_config.NumberColumn("Tasa Dev. mediana",    format="%.3f"),
        "cltv_mediana":         st.column_config.NumberColumn("CLTV mediana (€)",     format="%.0f"),
    },
    hide_index=True,
    use_container_width=True,
)

interpretaciones = {
    "Recurrentes premium":
        "Alta frecuencia, bajo return_rate y márgenes sólidos. "
        "Son el núcleo del negocio: retenerlos es prioritario. "
        "Su AOV elevado refleja tickets de compra altos y consistentes.",
    "Compradores únicos":
        "Un único pedido o frecuencia muy baja. Representan el 79% del catálogo "
        "de clientes pero con CLTV modesto. Objetivo estratégico: segunda compra.",
    "Devolvedores":
        "Frecuencia media pero tasa de devolución muy superior al resto. "
        "El margen neto queda erosionado por las devoluciones. "
        "Candidatos a revisión de la política de devoluciones o de la oferta asignada.",
    "Productos a pérdida":
        "Solo 7 clientes con CLTV negativo. Caso extremo donde el importe devuelto "
        "supera el margen bruto generado. Análisis individual recomendado.",
}

with st.expander("📝 Interpretación de segmentos"):
    for cluster, texto in interpretaciones.items():
        st.markdown(f"**{cluster}**")
        st.write(texto)
        st.markdown("---")
