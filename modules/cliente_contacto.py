import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return []


def api_post(path: str, payload: Optional[dict] = None):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_put(path: str, payload: dict):
    try:
        r = requests.put(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{api_base()}{path}", timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def render_contacto_form(clienteid: int, key_prefix: str = ""):
    clienteid = int(clienteid)
    kp = key_prefix or ""

    st.subheader("Contactos del cliente")
    st.caption("Telefonos, emails o fax asociados al cliente.")

    contactos: List[Dict[str, Any]] = api_get(f"/api/clientes/{clienteid}/contactos")

    with st.expander("Agregar nuevo contacto"):
        _contacto_editor(clienteid, None, key_prefix=kp)

    if not contactos:
        st.info("Este cliente no tiene contactos registrados.")
        return

    st.markdown("---")

    for c in contactos:
        cid = c["cliente_contactoid"]
        tipo = c.get("tipo") or "-"
        valor = c.get("valor") or "-"
        es_principal = bool(c.get("principal"))

        bg = "#f0f9ff" if es_principal else "#ffffff"
        border = "#38bdf8" if es_principal else "#e5e7eb"

        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"Tipo: {tipo}")
                st.write(f"Valor: {valor}")
            with cols[1]:
                st.write("Principal" if es_principal else "")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Editar", key=f"{kp}edit_contact_{cid}", use_container_width=True):
                st.session_state[f"{kp}edit_contact_{cid}"] = not st.session_state.get(
                    f"{kp}edit_contact_{cid}", False
                )

        with col2:
            if st.button("Eliminar", key=f"{kp}delete_contact_{cid}", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/contactos/{cid}")
                st.toast("Contacto eliminado.")
                st.rerun()

        with col3:
            if not es_principal:
                if st.button("Hacer principal", key=f"{kp}main_contact_{cid}", use_container_width=True):
                    api_post(f"/api/clientes/{clienteid}/contactos/{cid}/hacer-principal")
                    st.toast("Contacto marcado como principal.")
                    st.rerun()

        if st.session_state.get(f"{kp}edit_contact_{cid}"):
            with st.expander(f"Editar contacto {tipo}", expanded=True):
                _contacto_editor(clienteid, c, key_prefix=kp)


def _contacto_editor(clienteid: int, c: Optional[Dict[str, Any]] = None, key_prefix: str = ""):
    is_new = c is None
    cid = (c or {}).get("cliente_contactoid")
    prefix = f"{key_prefix}contact_{cid or 'new'}"

    def field(key, label, default=""):
        k = f"{prefix}_{key}"
        st.session_state.setdefault(k, (c or {}).get(key, default))
        return st.text_input(label, key=k)

    tipos = ["TELEFONO", "EMAIL", "FAX"]
    tipo_default = (c or {}).get("tipo") or "TELEFONO"
    tipo = st.selectbox("Tipo", tipos, index=tipos.index(tipo_default), key=f"{prefix}_tipo")
    valor = field("valor", "Valor *")
    principal = st.checkbox("Principal", value=bool((c or {}).get("principal")), key=f"{prefix}_principal")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Guardar", key=f"{prefix}_save", use_container_width=True):
            if not valor.strip():
                st.warning("El valor es obligatorio.")
                return

            payload = {
                "tipo": tipo,
                "valor": valor.strip(),
                "principal": principal,
            }

            if is_new:
                api_post(f"/api/clientes/{clienteid}/contactos", payload)
                st.toast("Contacto agregado.")
            else:
                api_put(f"/api/clientes/{clienteid}/contactos/{cid}", payload)
                st.toast("Contacto actualizado.")

            st.rerun()

    with col2:
        if not is_new:
            if st.button("Eliminar", key=f"{prefix}_delete", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/contactos/{cid}")
                st.toast("Contacto eliminado.")
                st.rerun()
