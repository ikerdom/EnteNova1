import streamlit as st

# =============================================================
# 📎 FORM · Documentos asociados del cliente (manual + futuro SharePoint)
# =============================================================

def render_documento_form(supabase, clienteid: int):
    """Formulario para listar, añadir y gestionar documentos de cliente."""
    st.markdown("### 📎 Documentos asociados")
    st.caption("Adjunta documentos (contratos, SEPA, FACE, albaranes, etc.) o sincroniza con SharePoint.")

    with st.expander("➕ Añadir nuevo documento", expanded=False):
        try:
            tipos = (
                supabase.table("documento_tipo")
                .select("documentotipoid, codigo, descripcion")
                .eq("habilitado", True)
                .order("codigo")
                .execute()
                .data or []
            )
        except Exception as e:
            st.error(f"❌ Error al cargar tipos de documento: {e}")
            return

        if not tipos:
            st.warning("⚠️ No hay tipos de documento definidos.")
            return

        opciones = {f"{t['codigo']} — {t['descripcion']}": t["documentotipoid"] for t in tipos}
        tipo_sel = st.selectbox("Tipo de documento", list(opciones.keys()), key=f"tipo_doc_{clienteid}")
        url = st.text_input("URL o ruta del documento", placeholder="https://...", key=f"url_doc_{clienteid}")
        obs = st.text_area("Observaciones", placeholder="Ej. Factura electrónica, contrato firmado…", key=f"obs_doc_{clienteid}")

        if st.button("📤 Guardar documento", key=f"guardar_doc_{clienteid}", use_container_width=True):
            if not url.strip():
                st.warning("⚠️ Debes indicar una URL o ruta válida.")
                return
            data = {
                "clienteid": clienteid,
                "documentotipoid": opciones[tipo_sel],
                "url": url.strip(),
                "observaciones": obs.strip() or None,
            }
            try:
                supabase.table("cliente_documento").insert(data).execute()
                st.toast("✅ Documento guardado correctamente.", icon="✅")
                st.session_state["refresh_docs"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar documento: {e}")

    # ---------------------------------------------------------
    # 📂 Documentos registrados
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📂 Documentos registrados")

    try:
        docs = (
            supabase.table("cliente_documento")
            .select("cliente_documentoid, url, observaciones, documentotipoid")
            .eq("clienteid", clienteid)
            .order("cliente_documentoid", desc=True)
            .execute()
            .data or []
        )
    except Exception as e:
        st.error(f"❌ Error al cargar documentos: {e}")
        return

    if not docs:
        st.info("📭 No hay documentos aún.")
        return

    tipo_nombre = {t["documentotipoid"]: f"{t['codigo']} — {t['descripcion']}" for t in tipos}

    for doc in docs:
        tipo_label = tipo_nombre.get(doc["documentotipoid"], "Desconocido")
        with st.container(border=True):
            st.markdown(f"**📄 {tipo_label}**")
            st.markdown(f"🔗 [Abrir documento]({doc['url']})")
            if doc.get("observaciones"):
                st.caption(f"🗒️ {doc['observaciones']}")
