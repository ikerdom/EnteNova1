from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return []


def api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def _format_fecha(raw: Any) -> str:
    if not raw:
        return "-"
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(raw)


def render_observaciones_form(clienteid: int, key_prefix: str = ""):
    clienteid = int(clienteid)
    kp = key_prefix or ""

    st.subheader("Observaciones internas")
    st.caption("Notas privadas de seguimiento, incidencias o informacion relevante del cliente.")

    notas: List[Dict[str, Any]] = api_get(
        f"/api/clientes/{clienteid}/observaciones"
    )

    if notas:
        for n in notas:
            tipo = n.get("tipo", "General")
            comentario = n.get("comentario", "")
            usuario = n.get("usuario") or "Desconocido"
            fecha = _format_fecha(n.get("fecha"))

            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"Tipo: {tipo}")
                with c2:
                    st.caption(fecha)
                st.write(comentario)
                st.caption(f"Usuario: {usuario}")
    else:
        st.info("No hay observaciones registradas.")

    st.markdown("---")

    with st.expander("Agregar nueva observacion"):
        col1, col2 = st.columns(2)

        with col1:
            tipo = st.selectbox(
                "Tipo de nota",
                ["General", "Comercial", "Administracion", "Otro"],
                index=0,
                key=f"{kp}obs_tipo_{clienteid}",
            )

        with col2:
            usuario = st.session_state.get("user_nombre", "Desconocido")
            st.text_input("Usuario", value=usuario, disabled=True, key=f"{kp}obs_user_{clienteid}")

        comentario = st.text_area(
            "Comentario",
            placeholder="Ejemplo: Cliente solicita retrasar entrega una semana.",
            height=100,
            key=f"{kp}obs_text_{clienteid}",
        )

        if st.button("Guardar observacion", use_container_width=True, key=f"{kp}obs_save_{clienteid}"):
            if not comentario.strip():
                st.warning("Debes escribir un comentario.")
                return

            payload = {
                "tipo": tipo,
                "comentario": comentario.strip(),
                "usuario": usuario,
            }

            res = api_post(
                f"/api/clientes/{clienteid}/observaciones",
                payload,
            )

            if res:
                st.toast("Observacion guardada correctamente.")
                st.rerun()
