"""
5_Customer_360.py — Página 5: Perfil individual de cliente.
(Renombrado y mejorado desde 3_Customer_360.py)
Mejoras: botón 🎲 cliente aleatorio + percentiles en comparativa de segmento.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CLUSTER_COLORS, fmt_eur, fmt_pct, load_data

st.set_page_config(
    page_title="Customer 360 — saleshealth",
    page_icon="👤",
    layout="wide",
)

st.title("👤 Customer 360")
st.caption("Perfil individual de cliente · búsqueda por ID o email")

df = load_data()

# ── Buscador + botón aleatorio ────────────────────────────────────────────────
if "rand_cid" not in st.session_state:
    st.session_state["rand_cid"] = ""

col_modo, col_input, col_btn = st.columns([1, 3, 0.8])

with col_modo:
    modo = st.radio("Buscar por", ["customer_id", "email"], horizontal=False)

with col_btn:
    st.write("")
    st.write("")
    if st.button("🎲 Aleatorio", use_container_width=True,
                 help="Carga un cliente al azar"):
        rid = int(df["customer_id"].sample(1).iloc[0])
        st.session_state["rand_cid"] = str(rid)
        st.rerun()

with col_input:
    placeholder = "Ej. 1234" if modo == "customer_id" else "Ej. cliente@email.com"
    label       = "customer_id" if modo == "customer_id" else "Email del cliente"
    query_raw   = st.text_input(
        label,
        value=st.session_state["rand_cid"],
        placeholder=placeholder,
    )
    st.session_state["rand_cid"] = query_raw

if not query_raw.strip():
    st.info("Introduce un customer_id o email para ver el perfil del cliente.")
    st.stop()

# ── Búsqueda ──────────────────────────────────────────────────────────────────
if modo == "customer_id":
    try:
        cid       = int(query_raw.strip())
        resultado = df[df["customer_id"] == cid]
    except ValueError:
        st.error("El customer_id debe ser un número entero.")
        st.stop()
else:
    resultado = df[df["email"].str.lower() == query_raw.strip().lower()]

if resultado.empty:
    st.warning(f"No se encontró ningún cliente con {modo} = '{query_raw.strip()}'.")
    st.stop()

cliente      = resultado.iloc[0]
cluster_name = str(cliente["cluster_label"])
cluster_data = df[
    (df["cluster_label"] == cluster_name) &
    (df["customer_id"] != cliente["customer_id"])
]
cluster_mask = df["cluster_label"] == cluster_name

# ── Tarjeta de identidad + KPIs ───────────────────────────────────────────────
st.divider()
col_id, col_kpis = st.columns([1, 2])

with col_id:
    st.subheader(str(cliente["nombre_completo"]))
    st.write(f"📧 {cliente['email']}")
    st.write(f"📍 {cliente['distrito']}, {cliente['ciudad']}")
    st.write(f"📅 Cliente desde {cliente['fecha_alta_efectiva']}")

    badge_funcs = {
        "Recurrentes premium": st.success,
        "Compradores únicos":  st.info,
        "Devolvedores":        st.warning,
        "Productos a pérdida": st.error,
    }
    badge_funcs.get(cluster_name, st.info)(f"Segmento: {cluster_name}")

with col_kpis:
    k1, k2, k3 = st.columns(3)
    k1.metric(
        "Valor del cliente",
        fmt_eur(float(cliente["cltv"])),
        help="Margen neto histórico ajustado por devoluciones.",
    )
    k2.metric(
        "Ticket medio",
        fmt_eur(float(cliente["aov"])),
        help="Importe medio por pedido (ingresos brutos / nº pedidos).",
    )
    k3.metric("Pedidos", int(cliente["n_pedidos"]))

    k4, k5, k6 = st.columns(3)
    k4.metric(
        "Meses activo",
        int(cliente["meses_activo"]),
        help="Meses calendario distintos con al menos una compra.",
    )
    k5.metric(
        "Tasa devolución",
        fmt_pct(float(cliente["return_rate"]) * 100),
        help="Ítems devueltos / ítems vendidos.",
    )
    k6.metric(
        "Último pedido",
        f"hace {int(cliente['recency_dias'])} días",
        help="Días transcurridos desde la última compra hasta el cierre del dataset.",
    )

st.divider()

# ── Comparativa cliente vs media del segmento ─────────────────────────────────
st.subheader(f"Comparativa con su segmento: {cluster_name}")

features_map = {
    "aov":          "Ticket medio",
    "margin_rate":  "Margen",
    "meses_activo": "Tiempo activo",
    "return_rate":  "Tasa de devolución",
}

comp_rows = []
for feat, label in features_map.items():
    val      = float(cliente[feat])
    mean_val = float(cluster_data[feat].mean())
    pct_diff = (val / mean_val - 1) * 100 if mean_val != 0 else 0.0

    vals_cluster = df[cluster_mask][feat].dropna()
    n_cluster    = len(vals_cluster)
    percentil    = int(round((vals_cluster < val).sum() / n_cluster * 100)) if n_cluster > 0 else 0

    comp_rows.append({
        "Variable":        label,
        "Diferencia (%)":  round(pct_diff, 1),
        "Dirección":       "Por encima" if pct_diff >= 0 else "Por debajo",
        "Percentil":       percentil,
    })

comp_df = pd.DataFrame(comp_rows)

fig_comp = px.bar(
    comp_df,
    x="Diferencia (%)",
    y="Variable",
    orientation="h",
    color="Dirección",
    color_discrete_map={"Por encima": "#2ECC71", "Por debajo": "#E74C3C"},
    labels={"Diferencia (%)": "% vs media del segmento", "Variable": ""},
    text=comp_df["Diferencia (%)"].apply(lambda v: f"{v:+.1f}%"),
)
fig_comp.add_vline(x=0, line_color="#7F8C8D", line_width=1.5)
fig_comp.update_layout(
    showlegend=True,
    height=280,
    margin=dict(t=10, b=10, l=10, r=60),
)
fig_comp.update_traces(textposition="outside")
st.plotly_chart(fig_comp, use_container_width=True)

st.caption(
    "Las barras muestran la diferencia porcentual respecto a la media "
    "de los demás clientes del segmento (excluyendo este cliente). "
    "Verde = por encima · Rojo = por debajo. No implica necesariamente mejor o peor."
)

# Percentiles dentro del segmento
st.markdown("**Posición dentro del segmento:**")
pct_cols = st.columns(len(comp_rows))
for col, row in zip(pct_cols, comp_rows):
    col.metric(row["Variable"], f"Percentil {row['Percentil']}")

st.divider()

# ── Posición en la distribución global ───────────────────────────────────────
st.subheader("Posición en la distribución global")

cltv_cliente = float(cliente["cltv"])
percentil    = float((df["cltv"] < cltv_cliente).sum() / len(df) * 100)

st.markdown(
    f"Este cliente está en el **percentil {percentil:.0f}** "
    f"de la distribución global de valor ({fmt_eur(cltv_cliente)})."
)

if cltv_cliente <= 0:
    st.warning(
        "Este cliente tiene valor ≤ 0 (devoluciones superiores al margen bruto). "
        "La posición en el histograma no es representativa en escala logarítmica."
    )
else:
    cltv_vals  = df[df["cltv"] > 0]["cltv"].astype(float).values
    log_vals   = np.log10(cltv_vals)
    log_client = float(np.log10(cltv_cliente))

    fig_mini = go.Figure()
    fig_mini.add_trace(go.Histogram(
        x=log_vals,
        nbinsx=60,
        marker=dict(color="#BDC3C7", line=dict(color="#95A5A6", width=0.5)),
        opacity=0.7,
        name="Distribución",
        hovertemplate="Clientes: %{y}<extra></extra>",
    ))

    ticks_orig = [1, 10, 100, 1_000, 10_000, 100_000]
    fig_mini.update_xaxes(
        title="Valor del cliente (€)",
        tickvals=[np.log10(v) for v in ticks_orig],
        ticktext=["1", "10", "100", "1k", "10k", "100k"],
    )
    fig_mini.update_yaxes(title="Nº clientes")

    fig_mini.add_vline(
        x=log_client,
        line_color=CLUSTER_COLORS.get(cluster_name, "#3498DB"),
        line_width=4,
        annotation_text=f"Cliente · Percentil {percentil:.0f}",
        annotation_position="top",
        annotation_font_size=14,
        annotation_font_color=CLUSTER_COLORS.get(cluster_name, "#3498DB"),
    )
    fig_mini.update_layout(
        height=300,
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=False,
        bargap=0.05,
    )
    st.plotly_chart(fig_mini, use_container_width=True)
