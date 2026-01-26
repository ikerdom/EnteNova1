# modules/impuesto_lista.py
import streamlit as st
import pandas as pd
from datetime import date

def render_impuesto_lista(supabase):
    st.header("🧾 Impuestos")
    st.caption("Catálogo de impuestos. Precio base → tarifas → **impuestos** (al final).")

    # Alta/edición rápida
    with st.expander("➕ Nuevo impuesto", expanded=False):
        with st.form("form_imp_new"):
            col1, col2, col3 = st.columns([2,1,1])
            with col1:
                nombre = st.text_input("Nombre", placeholder="IVA 21%")
            with col2:
                tipo = st.selectbox("Tipo", ["porcentaje","fijo"])
            with col3:
                valor = st.number_input("Valor", min_value=0.0, step=0.01)
            ok = st.form_submit_button("Guardar")
        if ok:
            try:
                supabase.table("impuesto").insert({"nombre": nombre.strip(), "tipo": tipo, "valor": valor, "habilitado": True}).execute()
                st.success("✅ Impuesto creado.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error creando impuesto: {e}")

    # Listado
    try:
        rows = supabase.table("impuesto").select("*").order("impuestoid").execute().data or []
        if not rows:
            st.info("Sin impuestos.")
            return
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error cargando impuestos: {e}")
