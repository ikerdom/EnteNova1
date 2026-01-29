# ======================================================
# 🚚 SIMULADOR DE PRECIOS — ahora vía API FastAPI
# ======================================================
import streamlit as st
import pandas as pd
from datetime import date

from modules.tarifa_api import catalogos, calcular_precio


def render_simulador_pedido(_supabase=None):
    st.header("🚚 Simulador de precios, tarifas e impuestos")
    st.caption("Comprueba cómo aplican las tarifas, jerarquías y el IVA según cliente/grupo/producto (motor en backend).")

    st.markdown("---")

    try:
        cats = catalogos()
    except Exception as e:
        st.error(f"❌ No se pudieron cargar catálogos: {e}")
        return

    clientes = {c["label"]: c for c in cats.get("clientes", [])}
    productos = {p["label"]: p for p in cats.get("productos", [])}

    col1, col2 = st.columns(2)
    with col1:
        cli_sel = st.selectbox("🧑‍🤝‍🧑 Cliente", list(clientes.keys()) or ["(sin clientes)"])
        clienteid = clientes.get(cli_sel, {}).get("id") if cli_sel else None
    with col2:
        prod_sel = st.selectbox("📦 Producto", list(productos.keys()) or ["(sin productos)"])
        productoid = productos.get(prod_sel, {}).get("id") if prod_sel else None

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with col2:
        fecha_sel = st.date_input("Fecha simulada", value=date.today())
    with col3:
        st.write("")
        calcular = st.button(
            "🧮 Calcular precio final",
            use_container_width=True,
            disabled=not (clienteid and productoid),
        )

    if not calcular:
        return

    try:
        engine = calcular_precio(
            {
                "clienteid": clienteid,
                "productoid": productoid,
                "precio_base_unit": None,
                "cantidad": cantidad,
                "fecha": fecha_sel.isoformat(),
            }
        )

        nivel = engine.get("nivel_tarifa")
        color = {
            "producto+cliente": "#22c55e",
            "familia+cliente": "#3b82f6",
            "producto+grupo": "#f59e0b",
            "familia+grupo": "#eab308",
            "cliente_tarifa": "#8b5cf6",
            "fallback_general": "#6b7280",
            None: "#9ca3af",
        }.get(nivel)

        st.markdown("### 🧮 Resultado del cálculo")
        st.markdown(
            f"""
            <div style="border-left:6px solid {color};padding:15px 18px;background:#f9fafb;border-radius:10px;line-height:1.7;">
            <b>Precio bruto unitario:</b> {engine["unit_bruto"]:.2f} €<br>
            <b>Descuento aplicado:</b> {engine["descuento_pct"]:.2f}%<br>
            <b>→ Neto sin IVA:</b> {engine["unit_neto_sin_iva"]:.2f} €<br>
            <b>IVA:</b> {engine["iva_pct"]:.2f}% ({engine.get("iva_nombre") or "No definido"})<br>
            <b>Total con IVA:</b> <span style="font-size:1.2em;color:#16a34a;font-weight:600;">{engine["total_con_iva"]:.2f} €</span>
            <hr>
            <b>Tarifa aplicada:</b> {engine.get("tarifa_aplicada") or "Ninguna"}<br>
            <b>Nivel jerárquico:</b> {nivel or "Sin coincidencia"}<br>
            <b>Regla ID:</b> {engine.get("regla_id") or "-"}<br>
            <b>IVA origen:</b> {engine.get("iva_origen") or "-"}<br>
            <b>Región:</b> {engine.get("region") or "-"} ({engine.get("region_origen") or "-"})
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Jerarquía evaluada")
        niveles = [
            ("producto+cliente", "Producto + Cliente"),
            ("familia+cliente", "Familia + Cliente"),
            ("producto+grupo", "Producto + Grupo"),
            ("familia+grupo", "Familia + Grupo"),
            ("cliente_tarifa", "Cliente → Tarifa asignada"),
            ("fallback_general", "Tarifa General (fallback)"),
        ]
        for clave, etiqueta in niveles:
            icon = "✅" if nivel == clave else "⚪"
            st.write(f"{icon} {etiqueta}")

        with st.expander("🛠️ Desglose completo del cálculo"):
            st.markdown("**🧾 Datos base:**")
            st.json(
                {
                    "Cliente": cli_sel,
                    "Producto": prod_sel,
                    "Cantidad": cantidad,
                    "Fecha simulada": str(fecha_sel),
                }
            )
            st.markdown("**⚙️ Resultado del motor:**")
            st.json(engine)

    except Exception as e:
        st.error(f"❌ Error durante la simulación: {e}")
