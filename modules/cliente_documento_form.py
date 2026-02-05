import requests
import streamlit as st

from modules.api_base import get_api_base


def _api_get(path: str, params: dict | None = None):
    r = requests.get(f"{get_api_base()}{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _api_post(path: str, payload: dict):
    r = requests.post(f"{get_api_base()}{path}", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def render_documento_form(_supabase_unused, clienteid: int):
    """Formulario para listar, añadir y gestionar documentos de cliente vía API."""
    st.markdown("### 📎 Documentos asociados")
    st.caption("Adjunta documentos (contratos, SEPA, FACE, albaranes, etc.) o sincroniza con SharePoint.")

    try:
        tipos = _api_get("/api/clientes/documentos/tipos")
    except Exception as e:
        st.error(f"❌ Error al cargar tipos de documento: {e}")
        return

    if not tipos:
        st.warning("⚠️ No hay tipos de documento definidos.")
        return

    opciones = {f"{t.get('codigo','-')} — {t.get('descripcion','')}": t.get("documentotipoid") for t in tipos}

    with st.expander("➕ Añadir nuevo documento", expanded=False):
        tipo_sel = st.selectbox("Tipo de documento", list(opciones.keys()), key=f"tipo_doc_{clienteid}")
        url = st.text_input("URL o ruta del documento", placeholder="https://...", key=f"url_doc_{clienteid}")
        obs = st.text_area("Observaciones", placeholder="Ej. Factura electrónica, contrato firmado…", key=f"obs_doc_{clienteid}")

        if st.button("📤 Guardar documento", key=f"guardar_doc_{clienteid}", use_container_width=True):
            if not url.strip():
                st.warning("⚠️ Debes indicar una URL o ruta válida.")
                return
            data = {
                "documentotipoid": opciones[tipo_sel],
                "url": url.strip(),
                "observaciones": obs.strip() or None,
            }
            try:
                _api_post(f"/api/clientes/{clienteid}/documentos", data)
                st.toast("✅ Documento guardado correctamente.", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar documento: {e}")

    st.markdown("---")
    st.markdown("#### 📂 Documentos registrados")

    try:
        docs = _api_get(f"/api/clientes/{clienteid}/documentos")
    except Exception as e:
        st.error(f"❌ Error al cargar documentos: {e}")
        return

    if not docs:
        st.info("📭 No hay documentos aún.")
        return

    tipo_nombre = {t.get("documentotipoid"): f"{t.get('codigo','-')} — {t.get('descripcion','')}" for t in tipos}

    for doc in docs:
        tipo_label = tipo_nombre.get(doc.get("documentotipoid"), "Desconocido")
        with st.container(border=True):
            st.markdown(f"**📄 {tipo_label}**")
            st.markdown(f"🔗 [Abrir documento]({doc.get('url')})")
            if doc.get("observaciones"):
                st.caption(f"🗒️ {doc['observaciones']}")
