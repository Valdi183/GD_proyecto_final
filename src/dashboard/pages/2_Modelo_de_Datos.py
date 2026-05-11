"""
2_Modelo_de_Datos.py — Página 2: Los datos del análisis.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import get_engine, get_rango_fechas, get_ventas_por_anio

st.set_page_config(page_title="Modelo de Datos", page_icon="🗄️", layout="wide")
st.title("🗄️ Los datos del análisis")

# ── De dónde vienen ───────────────────────────────────────────────────────────
st.write(
    "Los datos provienen de un sistema operacional de venta de productos "
    "de salud que registra las ventas, los clientes, los productos y las "
    "devoluciones. La información se consolida en un almacén analítico "
    "para analizar el comportamiento y el valor de cada cliente."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("🛒 Líneas de venta", "42.313")
col2.metric("👥 Clientes",        "5.750")
col3.metric("📦 Productos",       "50")
col4.metric("🔄 Devoluciones",    "2.330")

st.divider()

# ── Cómo se procesan ──────────────────────────────────────────────────────────
st.subheader("Cómo se procesan los datos")

st.markdown(
    """
    <div style="display:flex;align-items:stretch;justify-content:center;
                gap:12px;flex-wrap:wrap;padding:16px 0">

      <div style="background:#f0f2f6;border-radius:12px;padding:24px 28px;
                  min-width:190px;max-width:230px;text-align:center;flex:1">
        <div style="font-size:2.2rem">🗄️</div>
        <div style="font-weight:700;font-size:1.05rem;margin:10px 0 6px">
          Sistema operacional
        </div>
        <div style="font-size:0.87rem;color:#555;line-height:1.4">
          17 tablas con la información original del negocio
        </div>
      </div>

      <div style="display:flex;align-items:center;font-size:2.2rem;
                  color:#3498DB;font-weight:700;padding:0 4px">➜</div>

      <div style="background:#e8f4fb;border-radius:12px;padding:24px 28px;
                  min-width:190px;max-width:230px;text-align:center;flex:1">
        <div style="font-size:2.2rem">📊</div>
        <div style="font-weight:700;font-size:1.05rem;margin:10px 0 6px">
          Almacén analítico
        </div>
        <div style="font-size:0.87rem;color:#555;line-height:1.4">
          9 tablas optimizadas para análisis (modelo dimensional,
          estándar industria)
        </div>
      </div>

      <div style="display:flex;align-items:center;font-size:2.2rem;
                  color:#3498DB;font-weight:700;padding:0 4px">➜</div>

      <div style="background:#e8f8e8;border-radius:12px;padding:24px 28px;
                  min-width:190px;max-width:230px;text-align:center;flex:1">
        <div style="font-size:2.2rem">👤</div>
        <div style="font-weight:700;font-size:1.05rem;margin:10px 0 6px">
          Vista de cliente
        </div>
        <div style="font-size:0.87rem;color:#555;line-height:1.4">
          1 tabla resumen con 26 indicadores de comportamiento
          y valor por cliente
        </div>
      </div>

    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Cobertura temporal ────────────────────────────────────────────────────────
st.subheader("Cobertura temporal")

min_date, max_date = get_rango_fechas()
st.write(f"El análisis cubre desde **{min_date}** hasta **{max_date}**.")

df_anual = get_ventas_por_anio()
fig = px.bar(
    df_anual,
    x="anio",
    y="n_ventas",
    title="Actividad comercial por año",
    labels={"anio": "Año", "n_ventas": "Ventas registradas"},
    color_discrete_sequence=["#3498DB"],
    text="n_ventas",
)
fig.update_traces(textposition="outside")
fig.update_layout(
    height=340,
    margin=dict(t=40, b=20, l=20, r=20),
    showlegend=False,
    xaxis=dict(tickmode="linear", dtick=1),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Calidad de los datos ──────────────────────────────────────────────────────
with st.expander("🔍 Preparación de los datos — detalles técnicos"):
    st.write(
        "Durante la preparación se identificaron y corrigieron "
        "7 inconsistencias. Todos los cuadres financieros son exactos al céntimo."
    )

    decisiones = pd.DataFrame(
        {
            "ID": ["D01", "D02", "D03", "D04", "D05", "D06", "D07"],
            "Decisión": [
                "Múltiples códigos postales por distrito en zonas de Madrid",
                "Líneas de venta con contenido económico idéntico en el mismo pedido",
                "Total de pedido distinto de la suma de sus líneas",
                "Comprobación: subtotal = precio × cantidad en ítems sin oferta",
                "Producto sin ficha de costes en el catálogo central (19,99 €, Xiaomi)",
                "Fecha de alta de cliente almacenada como fecha de volcado del sistema",
                "Clientes sin ninguna compra registrada",
            ],
            "Impacto": [
                "Sin cambios — comportamiento geográfico correcto",
                "242 filas eliminadas por deduplicación",
                "1 pedido recalculado desde sus líneas",
                "Sin cambios — todos los subtotales correctos",
                "Coste imputado para 711 líneas de venta (28.506 €)",
                "Fecha calculada desde la primera compra de cada cliente",
                "Sin cambios — todos los clientes tienen ventas (n=0)",
            ],
        }
    )

    st.dataframe(
        decisiones,
        column_config={
            "ID":       st.column_config.TextColumn("ID",       width="small"),
            "Decisión": st.column_config.TextColumn("Decisión", width="large"),
            "Impacto":  st.column_config.TextColumn("Impacto",  width="medium"),
        },
        hide_index=True,
        use_container_width=True,
    )
