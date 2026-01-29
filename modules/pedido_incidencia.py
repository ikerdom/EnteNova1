import streamlit as st
from modules.pedido_models import load_trabajadores

def render_incidencias_pedido(supabase, pedidoid):
    st.subheader("⚠️ Incidencias asociadas al pedido")

    trabajadores = load_trabajadores(supabase)

    try:
        res = supabase.table("pedido_incidencia").select("*").eq("pedidoid", pedidoid).order("fecha", desc=True).execute()
        incidencias = res.data or []
    except Exception as e:
        st.error(f"Error cargando incidencias: {e}")
        incidencias = []

    # Mostrar incidencias
    for i in incidencias:
        st.markdown(f"### {i['tipo']} — {i['estado']}")
        st.caption(f"{i['fecha']} · Responsable: {next((k for k, v in trabajadores.items() if v == i.get('responsableid')), '-')}")
        st.write(i.get("descripcion") or "")
        if i.get("resolucion"):
            st.info(f"🛠️ {i['resolucion']}")
        st.divider()

    # Nueva incidencia
    with st.expander("➕ Registrar nueva incidencia", expanded=False):
        with st.form(f"form_incidencia_{pedidoid}"):
            tipo = st.text_input("Tipo (p. ej. Producto dañado, Retraso, Error de facturación)")
            descripcion = st.text_area("Descripción detallada", "")
            responsable_sel = st.selectbox("Responsable", list(trabajadores.keys()))
            enviar = st.form_submit_button("💾 Registrar incidencia")

        if enviar:
            try:
                payload = {
                    "pedidoid": pedidoid,
                    "tipo": tipo.strip(),
                    "descripcion": descripcion.strip(),
                    "responsableid": trabajadores.get(responsable_sel),
                }
                supabase.table("pedido_incidencia").insert(payload).execute()
                st.success("✅ Incidencia registrada correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando incidencia: {e}")
