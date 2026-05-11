"""
4_Segmentacion.py — Página 4: Segmentos de clientes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from utils import CLUSTER_COLORS, CLUSTER_ORDER, fmt_eur, load_data

st.set_page_config(page_title="Segmentación", page_icon="🎯", layout="wide")
st.title("🎯 Segmentos de clientes")

# ── Datos de segmentos (hardcoded) ────────────────────────────────────────────
SEGMENTOS = [
    {
        "nombre":      "Recurrentes premium",
        "color":       "#2ECC71",
        "clientes":    750,
        "pct":         13.0,
        "cltv_medio":  4480,
        "descripcion": (
            "Compran con frecuencia y mantienen la relación durante más de un año. "
            "Generan el 91% del valor del negocio."
        ),
        "accion": (
            "Retener a toda costa. Fidelización, atención prioritaria y ofertas exclusivas."
        ),
    },
    {
        "nombre":      "Compradores únicos",
        "color":       "#3498DB",
        "clientes":    4573,
        "pct":         79.5,
        "cltv_medio":  67,
        "descripcion": (
            "Han realizado una sola compra. Potencial de conversión a clientes "
            "recurrentes sin explotar."
        ),
        "accion": (
            "Activar con campañas de segunda compra y seguimiento post-venta personalizado."
        ),
    },
    {
        "nombre":      "Devolvedores",
        "color":       "#E67E22",
        "clientes":    420,
        "pct":         7.3,
        "cltv_medio":  12,
        "descripcion": (
            "Devuelven prácticamente todo lo que compran. "
            "Coste operativo elevado con retorno mínimo."
        ),
        "accion": (
            "Revisar causas de devolución. Considerar restricciones "
            "en la política de devoluciones."
        ),
    },
    {
        "nombre":      "Productos a pérdida",
        "color":       "#95A5A6",
        "clientes":    7,
        "pct":         0.1,
        "cltv_medio":  -57,
        "descripcion": (
            "Generan pérdidas netas. Detectados por el análisis de segmentación."
        ),
        "accion": (
            "Investigar caso a caso. Posibles errores de precio o fraude en devoluciones."
        ),
    },
]

# ── Sección 1: 4 tarjetas de segmento ────────────────────────────────────────
cols = st.columns(4)
for col, seg in zip(cols, SEGMENTOS):
    color = seg["color"]
    with col:
        st.markdown(
            f"""
            <div style="border-left:5px solid {color};border-radius:4px;
                        padding:16px 14px;background:#fafafa;min-height:220px">
              <div style="font-size:1.1rem;font-weight:700;color:{color};
                          margin-bottom:6px">{seg['nombre']}</div>
              <div style="font-size:0.85rem;color:#444;margin-bottom:8px">
                {seg['clientes']:,} clientes · {seg['pct']}% ·
                Valor medio: {seg['cltv_medio']:,} €
              </div>
              <div style="font-size:0.87rem;color:#333;margin-bottom:10px;
                          line-height:1.45">{seg['descripcion']}</div>
              <div style="font-size:0.85rem;color:#555;font-style:italic;
                          line-height:1.4">💡 {seg['accion']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ── Sección 2: Comparativa visual ────────────────────────────────────────────
st.subheader("Comparativa entre segmentos")

df_resumen = pd.DataFrame(SEGMENTOS)
color_map  = {s["nombre"]: s["color"] for s in SEGMENTOS}

col1, col2 = st.columns(2)

with col1:
    fig_clientes = px.bar(
        df_resumen,
        x="nombre",
        y="clientes",
        color="nombre",
        color_discrete_map=color_map,
        title="Clientes por segmento",
        labels={"nombre": "", "clientes": "Nº clientes"},
        text="clientes",
    )
    fig_clientes.update_layout(showlegend=False, height=340,
                               margin=dict(t=40, b=10, l=10, r=10))
    fig_clientes.update_traces(textposition="outside")
    st.plotly_chart(fig_clientes, use_container_width=True)

with col2:
    df_resumen["cltv_total"] = [3_360_000, 305_000, 5_200, -400]
    fig_cltv = px.bar(
        df_resumen,
        x="nombre",
        y="cltv_total",
        color="nombre",
        color_discrete_map=color_map,
        title="Valor total por segmento (€)",
        labels={"nombre": "", "cltv_total": "Valor total (€)"},
        text=df_resumen["cltv_total"].apply(
            lambda v: f"{v/1e6:.2f} M€" if abs(v) >= 1e6 else f"{v/1e3:.0f} k€"
        ),
    )
    fig_cltv.update_layout(showlegend=False, height=340,
                            margin=dict(t=40, b=10, l=10, r=10))
    fig_cltv.update_traces(textposition="outside")
    st.plotly_chart(fig_cltv, use_container_width=True)

st.divider()

# ── Sección 3: Radar charts 2×2 ──────────────────────────────────────────────
st.subheader("Perfil de comportamiento por segmento")

df_c360 = load_data(
    "SELECT cluster_label, aov, margin_rate, "
    "freq_mensual, meses_activo, return_rate, cltv "
    "FROM marts.customer_360"
)

max_aov    = float(df_c360["aov"].max())
max_freq   = float(df_c360["freq_mensual"].max())
max_meses  = float(df_c360["meses_activo"].max())
max_return = float(df_c360["return_rate"].max()) if df_c360["return_rate"].max() > 0 else 1.0

medians = (
    df_c360.groupby("cluster_label", observed=True)
    .agg(
        aov          =("aov",          "median"),
        freq_mensual =("freq_mensual", "median"),
        meses_activo =("meses_activo", "median"),
        return_rate  =("return_rate",  "median"),
        cltv         =("cltv",         "mean"),
        n_clientes   =("aov",          "count"),
    )
    .reindex(CLUSTER_ORDER)
)

categories = ["Ticket medio", "Frecuencia", "Tiempo activo", "Devoluciones"]

fig_radar = make_subplots(
    rows=2, cols=2,
    subplot_titles=CLUSTER_ORDER,
    specs=[
        [{"type": "polar"}, {"type": "polar"}],
        [{"type": "polar"}, {"type": "polar"}],
    ],
    vertical_spacing=0.12,
    horizontal_spacing=0.08,
)


def _hex_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


for i, cluster_name in enumerate(CLUSTER_ORDER):
    row, col = (i // 2) + 1, (i % 2) + 1
    color = CLUSTER_COLORS[cluster_name]

    if cluster_name in medians.index:
        med = medians.loc[cluster_name]
        values = [
            float(med["aov"])          / max_aov,
            float(med["freq_mensual"]) / max_freq,
            float(med["meses_activo"]) / max_meses,
            float(med["return_rate"])  / max_return,
        ]
    else:
        values = [0.0, 0.0, 0.0, 0.0]

    cats_closed   = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig_radar.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor=_hex_rgba(color, 0.25),
            line=dict(color=color, width=2),
            name=cluster_name,
            showlegend=False,
            hovertemplate="%{theta}: %{r:.2f}<extra>" + cluster_name + "</extra>",
        ),
        row=row,
        col=col,
    )

fig_radar.update_polars(
    radialaxis=dict(visible=True, range=[0, 1], showticklabels=False, gridcolor="#ddd"),
    angularaxis=dict(tickfont=dict(size=11)),
)
fig_radar.update_layout(
    height=560,
    margin=dict(t=70, b=20, l=30, r=30),
)
st.plotly_chart(fig_radar, use_container_width=True)
st.caption(
    "Cada eje representa una variable normalizada respecto al máximo del conjunto. "
    "Mayor área = mayor valor en esa dimensión de comportamiento."
)

st.divider()

# ── Expander: Tabla detallada ─────────────────────────────────────────────────
with st.expander("🔍 Datos detallados por segmento"):
    tabla_det = medians.reset_index().rename(columns={
        "cluster_label": "Segmento",
        "n_clientes":    "Clientes",
        "aov":           "Ticket medio (€)",
        "margin_rate":   "Margen",
        "freq_mensual":  "Frecuencia mensual",
        "meses_activo":  "Tiempo activo (meses)",
        "return_rate":   "Devoluciones",
        "cltv":          "Valor medio (€)",
    })
    st.dataframe(
        tabla_det,
        column_config={
            "Segmento":              st.column_config.TextColumn("Segmento"),
            "Clientes":              st.column_config.NumberColumn("Clientes",             format="%d"),
            "Ticket medio (€)":      st.column_config.NumberColumn("Ticket medio (€)",    format="%.0f"),
            "Margen":                st.column_config.NumberColumn("Margen",               format="%.2f"),
            "Frecuencia mensual":    st.column_config.NumberColumn("Frecuencia mensual",   format="%.2f"),
            "Tiempo activo (meses)": st.column_config.NumberColumn("Tiempo activo (meses)", format="%.0f"),
            "Devoluciones":          st.column_config.NumberColumn("Devoluciones",         format="%.3f"),
            "Valor medio (€)":       st.column_config.NumberColumn("Valor medio (€)",      format="%.0f"),
        },
        hide_index=True,
        use_container_width=True,
    )

# ── Expander: Validación técnica ──────────────────────────────────────────────
with st.expander("🔍 Validación del modelo — detalles técnicos"):
    st.write(
        "Se aplicó clustering no supervisado sobre 4 variables de comportamiento "
        "(ticket medio, margen, tiempo activo, devoluciones). "
        "El número óptimo de segmentos (K=4) se determinó con el índice de silueta "
        "(silhouette=0.696, rango 0-1, donde >0.5 indica segmentos bien diferenciados)."
    )

    sil_df = pd.DataFrame(
        {
            "K":          [2, 3, 4, 5, 6],
            "Silhouette": [0.6123, 0.6228, 0.6963, 0.5952, 0.5976],
            "Seleccionado": ["", "", "✓ óptimo", "", ""],
        }
    )
    st.dataframe(
        sil_df,
        column_config={
            "K":           st.column_config.NumberColumn("K", format="%d"),
            "Silhouette":  st.column_config.NumberColumn("Silhouette", format="%.4f"),
            "Seleccionado": st.column_config.TextColumn(""),
        },
        hide_index=True,
        use_container_width=False,
    )

    st.write(
        "Comparación con reducción dimensional (ARI=0.358): indica que proyectar "
        "a 2 dimensiones pierde información relevante. Se usó el espacio de 4 "
        "variables original para mayor precisión."
    )
