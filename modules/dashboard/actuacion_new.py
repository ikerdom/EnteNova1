# modules/dashboard/actuacion_new.py

import streamlit as st
from datetime import datetime

from modules.dashboard.utils import cliente_autocomplete
from modules.crm_api import crear as api_crear, catalogos as api_catalogos


def _crm_estado_id(_supabase_unused, estado: str):
    try:
        cats = api_catalogos() or {}
        rows = cats.get("estados") or []
        for r in rows:
            if r.get("estado") == estado:
                return r.get("crm_actuacion_estadoid")
    except Exception:
        pass
    return None


# Formulario nueva actuacion (dia concreto)

def render_nueva_actuacion_form(supabase, fecha, day_index):
    with st.form(f"form_new_act_{day_index}"):
        descripcion = st.text_input("Descripcion")

        clienteid = cliente_autocomplete(
            supabase,
            key_prefix=f"new_act_cli_{day_index}",
            label="Cliente (opcional)",
        )

        crear = st.form_submit_button("Crear accion")

        if crear:
            if not descripcion:
                st.error("La descripcion es obligatoria.")
                return

            try:
                estado_id = _crm_estado_id(supabase, "Pendiente")
                payload = {
                    "titulo": descripcion,
                    "descripcion": descripcion,
                    "fecha_vencimiento": fecha.date().isoformat(),
                    "fecha_accion": fecha.date().isoformat(),
                    "clienteid": clienteid,
                    "trabajador_creadorid": st.session_state.get("trabajadorid"),
                }
                if estado_id:
                    payload["crm_actuacion_estadoid"] = estado_id
                payload["fecha_accion"] = f"{fecha.date().isoformat()}T00:00:00"
                api_crear({k: v for k, v in payload.items() if k != "descripcion"})

                st.success("Accion creada correctamente.")
                st.session_state["crm_open_day"] = day_index
                st.rerun()

            except Exception as e:
                st.error(f"Error creando la accion: {e}")
