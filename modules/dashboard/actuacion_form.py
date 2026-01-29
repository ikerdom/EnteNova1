# modules/dashboard/actuacion_form.py

import streamlit as st
from datetime import date, datetime, time

from modules.dashboard.utils import cliente_autocomplete
from modules.crm_api import crear as api_crear, actualizar as api_actualizar


def _load_estados(supabase):
    if not supabase:
        return {}, []
    try:
        rows = (
            supabase.table("crm_actuacion_estado")
            .select("crm_actuacion_estadoid, estado")
            .order("estado")
            .execute()
            .data
            or []
        )
        estado_map = {r["estado"]: r["crm_actuacion_estadoid"] for r in rows}
        labels = list(estado_map.keys())
        return estado_map, labels
    except Exception:
        return {}, []


def _load_tipos(supabase):
    if not supabase:
        return {}, []
    try:
        rows = (
            supabase.table("crm_actuacion_tipo")
            .select("crm_actuacion_tipoid, tipo")
            .eq("habilitado", True)
            .order("tipo")
            .execute()
            .data
            or []
        )
        tipos_map = {r["tipo"]: r["crm_actuacion_tipoid"] for r in rows}
        labels = list(tipos_map.keys())
        return tipos_map, labels
    except Exception:
        return {}, []


def _load_trabajadores(supabase):
    if not supabase:
        return {}, []
    try:
        rows = (
            supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos")
            .order("nombre")
            .execute()
            .data
            or []
        )
        labels = []
        mapping = {}
        for r in rows:
            nombre = (r.get("nombre") or "").strip()
            apellidos = (r.get("apellidos") or "").strip()
            label = f"{nombre} {apellidos}".strip() or f"Trabajador {r.get('trabajadorid')}"
            labels.append(label)
            mapping[label] = r.get("trabajadorid")
        return mapping, labels
    except Exception:
        return {}, []


def render_actuacion_form(supabase, act=None, fecha_default=None):
    """
    Formulario de alta/edicion de actuacion CRM.
    act = dict con datos (modo edicion) o None (modo nuevo)
    fecha_default = date para nuevas actuaciones
    """
    st.markdown("---")
    st.markdown(
        """
        <div style="background:#eff6ff;padding:14px 16px;border-radius:12px;
                    border:1px solid #bfdbfe;margin-bottom:12px;">
            <div style="font-size:16px;font-weight:600;color:#1d4ed8;">Detalle de actuacion CRM</div>
            <div style="font-size:12px;color:#4b5563;">Crear, asignar y registrar seguimiento.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_edit = act is not None

    estado_map, estado_labels = _load_estados(supabase)
    tipos_map, tipos_labels = _load_tipos(supabase)
    trabajadores_map, trabajadores_labels = _load_trabajadores(supabase)

    if not estado_labels:
        estado_labels = ["Pendiente", "Completada", "Cancelada"]

    with st.form("form_actuacion"):
        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input("Titulo *", value=act.get("titulo") if is_edit else "")
            descripcion = st.text_area(
                "Descripcion",
                value=act.get("descripcion") if is_edit else "",
                height=80,
            )
            observaciones = st.text_area(
                "Notas internas",
                value=act.get("observaciones") if is_edit else "",
                height=80,
            )
        with col2:
            current_estado = None
            if is_edit:
                current_estado = (act.get("crm_actuacion_estado") or {}).get("estado") or act.get("estado")
                if not current_estado and act.get("crm_actuacion_estadoid"):
                    for k, v in estado_map.items():
                        if v == act.get("crm_actuacion_estadoid"):
                            current_estado = k
                            break
            if not current_estado:
                current_estado = "Pendiente"
            estado_sel = st.selectbox(
                "Estado",
                estado_labels,
                index=estado_labels.index(current_estado) if current_estado in estado_labels else 0,
            )

        col3, col4 = st.columns(2)
        with col3:
            fecha_venc = st.date_input(
                "Fecha vencimiento",
                value=date.fromisoformat(str(act["fecha_vencimiento"])[:10])
                if is_edit and act.get("fecha_vencimiento")
                else fecha_default or date.today(),
            )
        with col4:
            hora_accion = st.time_input(
                "Hora (opcional)",
                value=time(9, 0),
            )

        col5, col6 = st.columns(2)
        with col5:
            tipo_sel = st.selectbox(
                "Tipo",
                ["(sin tipo)"] + tipos_labels,
                index=0,
            )
        with col6:
            trabajador_sel = st.selectbox(
                "Asignar a",
                ["(yo mismo)"] + trabajadores_labels,
                index=0,
            )

        requiere_seguimiento = st.checkbox(
            "Requiere seguimiento",
            value=bool(act.get("requiere_seguimiento")) if is_edit else False,
        )
        recordatorio_fecha = None
        recordatorio_hora = None
        if requiere_seguimiento:
            r1, r2 = st.columns(2)
            with r1:
                recordatorio_fecha = st.date_input("Fecha recordatorio", value=fecha_venc)
            with r2:
                recordatorio_hora = st.time_input("Hora recordatorio", value=time(9, 0))

        clienteid = cliente_autocomplete(
            supabase,
            "actform",
            clienteid_inicial=act.get("clienteid") if is_edit else None,
        )

        colb1, colb2 = st.columns(2)
        guardar = colb1.form_submit_button("Guardar", use_container_width=True)
        cancelar = colb2.form_submit_button("Cerrar", use_container_width=True)

        if cancelar:
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
            st.rerun()

        if guardar:
            if not titulo:
                st.warning("El titulo es obligatorio.")
                return

            estado_id = estado_map.get(estado_sel)
            tipo_id = tipos_map.get(tipo_sel) if tipo_sel != "(sin tipo)" else None
            asignado_id = (
                trabajadores_map.get(trabajador_sel)
                if trabajador_sel != "(yo mismo)"
                else st.session_state.get("trabajadorid")
            )

            fecha_accion = datetime.combine(fecha_venc, hora_accion)

            data = {
                "titulo": titulo or None,
                "descripcion": descripcion or None,
                "observaciones": observaciones or None,
                "crm_actuacion_estadoid": estado_id,
                "crm_actuacion_tipoid": tipo_id,
                "fecha_vencimiento": fecha_venc.isoformat(),
                "fecha_accion": fecha_accion.isoformat(),
                "clienteid": clienteid,
                "trabajador_creadorid": st.session_state.get("trabajadorid"),
                "trabajador_asignadoid": asignado_id,
                "requiere_seguimiento": bool(requiere_seguimiento),
            }

            if requiere_seguimiento and recordatorio_fecha and recordatorio_hora:
                data["fecha_recordatorio"] = datetime.combine(
                    recordatorio_fecha, recordatorio_hora
                ).isoformat()

            try:
                if supabase:
                    if is_edit:
                        supabase.table("crm_actuacion").update(data).eq(
                            "crm_actuacionid", act["crm_actuacionid"]
                        ).execute()
                    else:
                        supabase.table("crm_actuacion").insert(data).execute()
                else:
                    if is_edit:
                        api_actualizar(act["crm_actuacionid"], data)
                    else:
                        api_crear(data)

                st.success("Guardado correctamente.")
                st.session_state["crm_actuacion_detalle_id"] = None
                st.session_state["crm_new_act_fecha"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
