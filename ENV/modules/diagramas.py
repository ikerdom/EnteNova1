import streamlit as st
from graphviz import Digraph

# ======================================================
# 🧬 GENERADOR DE DIAGRAMAS ERP · EnteNova Gnosis
# ======================================================
def generar_diagrama(tipo="general", detallado=False):
    """Genera diagramas con estilo corporativo y coherencia entre módulos."""
    g = Digraph(format="png")
    g.attr(rankdir="LR", bgcolor="white", splines="ortho", nodesep="0.6", ranksep="0.7")

    # 🎨 Paleta corporativa
    color_cliente = "#bde0fe"
    color_producto = "#caf0f8"
    color_pedido = "#ffe5b4"
    color_logistica = "#ffd6a5"
    color_crm = "#e4c1f9"
    color_trabajador = "#cdeac0"
    color_finanzas = "#f0efeb"

    # ------------------------------------------------------
    # 🔹 VISTA GENERAL
    # ------------------------------------------------------
    if tipo == "general":
        g.node("grupo", "🏢 grupo", shape="box", fillcolor=color_cliente, style="filled")
        g.node("cliente", "👤 cliente", shape="box", fillcolor=color_cliente, style="filled")
        g.node("trabajador", "🧑‍💼 trabajador", shape="box", fillcolor=color_trabajador, style="filled")
        g.node("pedido", "📦 pedido", shape="box", fillcolor=color_pedido, style="filled")
        g.node("pedido_detalle", "🧾 pedido_detalle", shape="box", fillcolor=color_pedido, style="filled")
        g.node("pedido_albaran", "🚚 pedido_albaran", shape="box", fillcolor=color_logistica, style="filled")
        g.node("transportista", "🚛 transportista", shape="box", fillcolor=color_logistica, style="filled")
        g.node("producto", "📘 producto", shape="box", fillcolor=color_producto, style="filled")
        g.node("familia_producto", "📂 familia_producto", shape="box", fillcolor=color_producto, style="filled")
        g.node("crm_lead", "📞 crm_lead", shape="box", fillcolor=color_crm, style="filled")
        g.node("crm_actuacion", "🗒️ crm_actuacion", shape="box", fillcolor=color_crm, style="filled")
        g.node("presupuesto", "💼 presupuesto", shape="box", fillcolor=color_finanzas, style="filled")

        # Relaciones principales
        g.edge("grupo", "cliente", label="1:N")
        g.edge("trabajador", "cliente", label="1:N (gestor)")
        g.edge("cliente", "pedido", label="1:N")
        g.edge("pedido", "pedido_detalle", label="1:N")
        g.edge("pedido", "pedido_albaran", label="1:N")
        g.edge("pedido_albaran", "transportista", label="N:1")
        g.edge("producto", "pedido_detalle", label="N:1")
        g.edge("familia_producto", "producto", label="1:N")
        g.edge("trabajador", "crm_lead", label="1:N")
        g.edge("crm_lead", "crm_actuacion", label="1:N")
        g.edge("crm_actuacion", "cliente", label="N:1 (posible cliente)")
        g.edge("cliente", "presupuesto", label="1:N")
        return g

    # ------------------------------------------------------
    # 🔹 CRM
    # ------------------------------------------------------
    elif tipo == "crm":
        g.node("crm_lead", "📞 crm_lead", shape="box", fillcolor=color_crm, style="filled")
        g.node("crm_estado", "🟣 crm_estado", shape="box", fillcolor="#dec9e9", style="filled")
        g.node("crm_actuacion", "🗒️ crm_actuacion", shape="box", fillcolor=color_crm, style="filled")
        g.node("trabajador", "🧑‍💼 trabajador", shape="box", fillcolor=color_trabajador, style="filled")
        g.node("cliente", "👤 cliente", shape="box", fillcolor=color_cliente, style="filled")

        g.edge("crm_estado", "crm_lead", label="1:N")
        g.edge("trabajador", "crm_lead", label="1:N")
        g.edge("crm_lead", "crm_actuacion", label="1:N")
        g.edge("trabajador", "crm_actuacion", label="1:N")
        g.edge("crm_actuacion", "cliente", label="N:1 (resultado)")
        return g

    # ------------------------------------------------------
    # 🔹 LOGÍSTICA
    # ------------------------------------------------------
    elif tipo == "logistica":
        g.node("pedido", "📦 pedido", shape="box", fillcolor=color_pedido, style="filled")
        g.node("pedido_albaran", "🚚 albarán", shape="box", fillcolor=color_logistica, style="filled")
        g.node("transportista", "🚛 transportista", shape="box", fillcolor=color_logistica, style="filled")
        g.node("cliente_direccion", "📍 cliente_direccion", shape="box", fillcolor=color_cliente, style="filled")

        g.edge("pedido", "pedido_albaran", label="1:N")
        g.edge("pedido_albaran", "transportista", label="N:1")
        g.edge("pedido_albaran", "cliente_direccion", label="N:1")
        return g

    # ------------------------------------------------------
    # 🔹 COMERCIAL / FINANZAS
    # ------------------------------------------------------
    elif tipo == "comercial":
        g.node("presupuesto", "💼 presupuesto", shape="box", fillcolor=color_finanzas, style="filled")
        g.node("pedido", "📦 pedido", shape="box", fillcolor=color_pedido, style="filled")
        g.node("pedido_detalle", "🧾 pedido_detalle", shape="box", fillcolor=color_pedido, style="filled")
        g.node("cliente", "👤 cliente", shape="box", fillcolor=color_cliente, style="filled")
        g.node("trabajador", "🧑‍💼 trabajador", shape="box", fillcolor=color_trabajador, style="filled")

        g.edge("trabajador", "presupuesto", label="1:N")
        g.edge("cliente", "presupuesto", label="1:N")
        g.edge("presupuesto", "pedido", label="1:N (conversión)")
        g.edge("pedido", "pedido_detalle", label="1:N")
        return g


# ======================================================
# 🎨 RENDERIZADOR EN STREAMLIT
# ======================================================
def render_diagramas(embed=False):
    """Renderiza los diagramas, con soporte para embed en dashboard."""
    st.subheader("🕸️ Mapa de relaciones principales")

    tabs = st.tabs(["📦 General", "💬 CRM", "🚚 Logística", "💼 Comercial / Finanzas"])
    tipos = ["general", "crm", "logistica", "comercial"]

    for i, tab in enumerate(tabs):
        with tab:
            g = generar_diagrama(tipos[i])
            st.graphviz_chart(g, use_container_width=True)
            st.caption(f"Diagrama: **{tipos[i]}** — modelo de datos y relaciones clave.")

    if not embed:
        st.info("📘 Estos diagramas reflejan las relaciones reales del ERP EnteNova Gnosis.")
