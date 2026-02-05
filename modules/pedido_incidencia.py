import requests
import streamlit as st
from modules.api_base import get_api_base
from modules.pedido_api import incidencias, crear_incidencia


def _load_trabajadores_api() -> dict:
    try:
        r = requests.get(f"{get_api_base()}/api/catalogos/trabajadores", timeout=15)
        r.raise_for_status()
        rows = r.json() or []
    except Exception:
        rows = []
    return {
        f"{r.get('nombre','')} {r.get('apellidos','')}".strip() or f"Trabajador {r.get('trabajadorid')}"
        : r.get("trabajadorid")
        for r in rows
        if r.get("trabajadorid") is not None
    }


def render_incidencias_pedido(_supabase_unused, pedidoid):
    st.subheader("⚠️ Incidencias asociadas al pedido")

    trabajadores = _load_trabajadores_api()

    try:
        incidencias_list = incidencias(pedidoid) or []
    except Exception as e:
        st.error(f"Error cargando incidencias: {e}")
        incidencias_list = []

    for i in incidencias_list:
        st.markdown(f"### {i.get('tipo','-')} — {i.get('estado','-')}")
        responsable = next((k for k, v in trabajadores.items() if v == i.get("responsableid")), "-")
        st.caption(f"{i.get('fecha','-')} · Responsable: {responsable}")
        st.write(i.get("descripcion") or "")
        if i.get("resolucion"):
            st.info(f"🛠️ {i['resolucion']}")
        st.divider()

    with st.expander("➕ Registrar nueva incidencia", expanded=False):
        with st.form(f"form_incidencia_{pedidoid}"):
            tipo = st.text_input("Tipo (p. ej. Producto dañado, Retraso, Error de facturación)")
            descripcion = st.text_area("Descripción detallada", "")
            responsable_sel = st.selectbox("Responsable", list(trabajadores.keys())) if trabajadores else None
            enviar = st.form_submit_button("💾 Registrar incidencia")

        if enviar:
            try:
                payload = {
                    "tipo": tipo.strip(),
                    "descripcion": descripcion.strip(),
                    "responsableid": trabajadores.get(responsable_sel) if responsable_sel else None,
                }
                crear_incidencia(pedidoid, payload)
                st.success("✅ Incidencia registrada correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando incidencia: {e}")
