# Panel de detalle de accion CRM via API.

from datetime import datetime, date, time, timedelta
from typing import Dict

import streamlit as st
from dateutil.parser import parse as parse_date

from modules.crm_api import detalle as api_detalle, actualizar as api_actualizar


def _load_trabajadores(supabase) -> Dict[str, int]:
    if not supabase:
        return {}
    try:
        rows = (
            supabase.table("trabajador")
            .select("trabajadorid,nombre,apellidos")
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception:
        return {}

    out = {}
    for r in rows:
        nombre = (r.get("nombre") or "").strip()
        apellidos = (r.get("apellidos") or "").strip()
        label = f"{nombre} {apellidos}".strip() or f"Trabajador {r.get('trabajadorid')}"
        out[label] = r.get("trabajadorid")
    return out


def _load_estados_tipos(supabase) -> tuple[Dict[str, int], Dict[str, int]]:
    if not supabase:
        return {}, {}
    try:
        estados = (
            supabase.table("crm_actuacion_estado")
            .select("crm_actuacion_estadoid, estado")
            .eq("habilitado", True)
            .order("estado")
            .execute()
            .data
            or []
        )
        tipos = (
            supabase.table("crm_actuacion_tipo")
            .select("crm_actuacion_tipoid, tipo")
            .eq("habilitado", True)
            .order("tipo")
            .execute()
            .data
            or []
        )
    except Exception:
        return {}, {}

    estados_map = {e["estado"]: e["crm_actuacion_estadoid"] for e in estados}
    tipos_map = {t["tipo"]: t["crm_actuacion_tipoid"] for t in tipos}
    return estados_map, tipos_map


def render_crm_accion_detalle(_supabase_unused, accionid: int):
    if not accionid:
        st.warning("No se ha seleccionado ninguna accion.")
        return

    supa = st.session_state.get("supa")
    if _supabase_unused is not None:
        supa = _supabase_unused

    try:
        accion = api_detalle(accionid)
    except Exception as e:
        st.error(f"Error cargando accion: {e}")
        return

    if not accion:
        st.error("No se encontro la accion seleccionada.")
        return

    estados_map, tipos_map = _load_estados_tipos(supa)
    trabajadores_map = _load_trabajadores(supa)

    st.markdown(f"### {accion.get('titulo', '(Sin titulo)')}")
    st.caption(f"Estado: {accion.get('estado', '-')}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Descripcion:** {accion.get('descripcion') or '-'}")
    with col2:
        if accion.get("fecha_vencimiento"):
            fecha_venc = parse_date(str(accion["fecha_vencimiento"])).date()
            st.markdown(f"**Fecha limite:** {fecha_venc.strftime('%d/%m/%Y')}")
        else:
            fecha_venc = date.today()
            st.markdown("**Fecha limite:** -")

    st.divider()

    with st.expander("Editar datos", expanded=False):
        with st.form(f"crm_edit_{accionid}"):
            titulo = st.text_input("Titulo", value=accion.get("titulo") or "")
            descripcion = st.text_area("Descripcion", value=accion.get("descripcion") or "")
            observaciones = st.text_area("Observaciones internas", value=accion.get("observaciones") or "")

            c1, c2 = st.columns(2)
            with c1:
                estado_sel = st.selectbox(
                    "Estado",
                    list(estados_map.keys()) or ["-"],
                    index=0,
                )
            with c2:
                tipo_sel = st.selectbox(
                    "Tipo",
                    list(tipos_map.keys()) or ["-"],
                    index=0,
                )

            trabajadores_list = list(trabajadores_map.keys()) or ["(Ninguno)"]
            trab_sel = st.selectbox("Asignar a", trabajadores_list, index=0)

            fecha_nueva = st.date_input("Fecha limite", value=fecha_venc)
            hora_nueva = st.time_input(
                "Hora",
                value=parse_date(str(accion["fecha_accion"])).time()
                if accion.get("fecha_accion")
                else time(9, 0),
            )
            requiere = st.checkbox("Requiere seguimiento", value=bool(accion.get("requiere_seguimiento")))
            recordatorio_fecha = None
            recordatorio_hora = None
            if requiere:
                r1, r2 = st.columns(2)
                with r1:
                    recordatorio_fecha = st.date_input("Fecha recordatorio", value=fecha_nueva)
                with r2:
                    recordatorio_hora = st.time_input("Hora recordatorio", value=time(9, 0))

            guardar = st.form_submit_button("Guardar cambios", use_container_width=True)

        if guardar:
            payload = {
                "titulo": titulo.strip(),
                "descripcion": descripcion or None,
                "observaciones": observaciones or None,
                "crm_actuacion_estadoid": estados_map.get(estado_sel),
                "crm_actuacion_tipoid": tipos_map.get(tipo_sel),
                "trabajador_asignadoid": trabajadores_map.get(trab_sel),
                "fecha_vencimiento": fecha_nueva.isoformat(),
                "fecha_accion": datetime.combine(fecha_nueva, hora_nueva).isoformat(),
                "requiere_seguimiento": bool(requiere),
            }
            if requiere and recordatorio_fecha and recordatorio_hora:
                payload["fecha_recordatorio"] = datetime.combine(
                    recordatorio_fecha, recordatorio_hora
                ).isoformat()
            try:
                api_actualizar(accionid, payload)
                st.success("Accion actualizada.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    with st.expander("Posponer accion", expanded=False):
        col1, col2 = st.columns(2)
        default_date = max(date.today(), fecha_venc)
        default_time = parse_date(str(accion["fecha_accion"])).time() if accion.get("fecha_accion") else time(9, 0)
        with col1:
            nueva_fecha = st.date_input(
                "Nueva fecha",
                value=default_date,
                min_value=date.today(),
                max_value=date.today() + timedelta(days=365 * 10),
                key=f"posp_fecha_{accionid}",
            )
        with col2:
            nueva_hora = st.time_input("Nueva hora", value=default_time, key=f"posp_hora_{accionid}")

        if st.button("Guardar nueva fecha/hora", key=f"save_fecha_{accionid}"):
            try:
                nueva_fecha_accion = datetime.combine(nueva_fecha, nueva_hora).replace(microsecond=0)
                payload = {
                    "fecha_vencimiento": nueva_fecha.isoformat(),
                    "fecha_accion": nueva_fecha_accion.isoformat(),
                }
                api_actualizar(accionid, payload)
                st.success("Accion pospuesta correctamente.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al posponer: {e}")

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("Marcar completada", key=f"comp_{accionid}"):
            estado_id = estados_map.get("Completada")
            if not estado_id:
                st.error("No se pudo resolver el estado.")
                return
            api_actualizar(accionid, {"crm_actuacion_estadoid": estado_id})
            st.success("Accion completada.")
            st.session_state["force_reload"] = True
            st.rerun()

    with colB:
        if st.button("Cancelar accion", key=f"cancel_{accionid}"):
            estado_id = estados_map.get("Cancelada")
            if not estado_id:
                st.error("No se pudo resolver el estado.")
                return
            api_actualizar(accionid, {"crm_actuacion_estadoid": estado_id})
            st.warning("Accion cancelada.")
            st.session_state["force_reload"] = True
            st.rerun()

    st.markdown("---")
    st.caption("CRM Accion Detalle")
