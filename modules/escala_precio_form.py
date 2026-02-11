# ======================================================
# 💰 ESCALAS DE PRECIO — Gestión de descuentos y precios especiales
# ======================================================
from datetime import date

import pandas as pd
import streamlit as st
from modules.supa_client import get_supabase_client

supabase = get_supabase_client()


def render_escala_precio():
    """Vista principal de gestión de escalas de precio."""
    st.title("💰 Escalas de Precio")
    st.caption("Consulta y gestión de descuentos o precios especiales por cliente, familia o proveedor.")

    # ======================================================
    # 📋 Escalas existentes
    # ======================================================
    with st.expander("📋 Ver escalas existentes", expanded=True):
        try:
            data = supabase.table("escala_precio").select("*").execute().data
            if data:
                df = pd.DataFrame(data)
                columnas = [
                    "escala_precioid", "tipo", "clienteid", "familia_productoid",
                    "proveedorid", "descuento_pct", "precio_especial", "fecha_inicio", "fecha_fin"
                ]
                st.dataframe(df[columnas], width="stretch")
            else:
                st.info("📭 No hay registros de escala de precios aún.")
        except Exception as e:
            st.error(f"❌ Error cargando datos: {e}")

    # ======================================================
    # ➕ Formulario para nuevas escalas
    # ======================================================
    with st.expander("➕ Añadir nueva escala", expanded=False):
        tipo = st.selectbox(
            "Tipo de escala",
            ["cliente", "familia", "proveedor"],
            help="Define si el descuento aplica a un cliente, familia o proveedor."
        )

        # ------------------------------------------------
        # 🔹 Cargar opciones según tipo
        # ------------------------------------------------
        opciones = {}
        campo_id = None

        try:
            if tipo == "cliente":
                data = supabase.table("cliente").select("clienteid, razonsocial, nombre").order("razonsocial").execute().data
                opciones = {(d.get("razonsocial") or d.get("nombre","")): d["clienteid"] for d in data}
                campo_id = "clienteid"
            elif tipo == "familia":
                data = supabase.table("familia_producto").select("familia_productoid, nombre").execute().data
                opciones = {d["nombre"]: d["familia_productoid"] for d in data}
                campo_id = "familia_productoid"
            elif tipo == "proveedor":
                data = supabase.table("proveedor").select("proveedorid, nombre").execute().data
                opciones = {d["nombre"]: d["proveedorid"] for d in data}
                campo_id = "proveedorid"
        except Exception as e:
            st.error(f"❌ Error cargando opciones: {e}")
            return

        if not opciones:
            st.warning(f"⚠️ No hay registros en la tabla asociada a '{tipo}'.")
            return

        seleccionado = st.selectbox(f"Seleccionar {tipo}", list(opciones.keys()))
        id_seleccionado = opciones[seleccionado]

        # ------------------------------------------------
        # 💸 Campos y fechas
        # ------------------------------------------------
        col1, col2 = st.columns(2)
        with col1:
            descuento_pct = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5)
            fecha_inicio = st.date_input("Fecha inicio", value=date.today())
        with col2:
            precio_especial = st.number_input("Precio especial (€)", min_value=0.0, step=0.1)
            fecha_fin = st.date_input("Fecha fin (opcional)", value=None)

        # ------------------------------------------------
        # 💾 Guardar
        # ------------------------------------------------
        if st.button("💾 Guardar nueva escala", width="stretch"):
            if not (descuento_pct or precio_especial):
                st.warning("⚠️ Debes indicar un descuento o un precio especial.")
                return

            payload = {
                "tipo": tipo,
                campo_id: id_seleccionado,
                "descuento_pct": descuento_pct if descuento_pct > 0 else None,
                "precio_especial": precio_especial if precio_especial > 0 else None,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
            }

            try:
                res = supabase.table("escala_precio").insert(payload).execute()
                if res.data:
                    st.toast(f"✅ Escala creada para {tipo}: {seleccionado}", icon="✅")
                    st.rerun()
                else:
                    st.warning("⚠️ No se insertó ningún registro. Verifica los datos.")
            except Exception as e:
                st.error(f"❌ Error al guardar la escala: {e}")
