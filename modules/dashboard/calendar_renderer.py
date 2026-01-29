# modules/dashboard/calendar_renderer.py

import streamlit as st
from datetime import datetime, timedelta

from modules.dashboard.utils import (
    safe_date,
    safe_time,
    cargar_clientes_map,
    filtrar_por_trabajador,
)
from modules.dashboard.actuacion_form import render_actuacion_form
from modules.dashboard.actuacion_new import render_nueva_actuacion_form


# ======================================================
# COLORES ESTADO
# ======================================================
COLOR_ESTADO = {
    "Pendiente": "#fbbf24",     # amarillo WARNING
    "En curso": "#6b7280",      # gris secondary
    "Completada": "#4ade80",    # verde success
}


def _crm_estado_id(supabase, estado: str):
    try:
        row = (
            supabase.table("crm_actuacion_estado")
            .select("crm_actuacion_estadoid, estado")
            .eq("estado", estado)
            .single()
            .execute()
            .data
        )
        return row.get("crm_actuacion_estadoid") if row else None
    except Exception:
        return None


# ======================================================
# CALENDARIO SEMANAL CRM
# ======================================================
def render_calendar(
    supabase,
    acts_data,
    days,
    trabajadorid,
    ver_todo,
):
    """
    Dibuja el calendario semanal del dashboard.
    """

    # -----------------------------------------
    # Filtrar por trabajador si aplica
    # -----------------------------------------
    if not ver_todo and trabajadorid:
        acts = filtrar_por_trabajador(acts_data, trabajadorid)
    else:
        acts = acts_data

    # -----------------------------------------
    # Mapa clienteid -> nombre
    # -----------------------------------------
    clientes_map = cargar_clientes_map(supabase, acts)

    # -----------------------------------------
    # Mostrar panel de detalle si esta activo
    # -----------------------------------------
    act_det_id = st.session_state.get("crm_actuacion_detalle_id")
    if act_det_id:
        act_obj = next((a for a in acts if a["crm_actuacionid"] == act_det_id), None)
        if act_obj:
            render_actuacion_form(supabase, act_obj, None)

    # -----------------------------------------
    # Layout entre calendario y panel lateral
    # -----------------------------------------
    col_cal, col_side = st.columns([4, 1])

    # =====================================================
    # PANEL LATERAL - RESUMEN SEMANAL
    # =====================================================
    with col_side:
        st.markdown("### Resumen semanal")

        if not acts:
            st.caption("Sin actuaciones en la semana.")
        else:
            total = len(acts)
            por_estado = {}
            for a in acts:
                est = (a.get("crm_actuacion_estado") or {}).get("estado") or a.get("estado") or "Sin estado"
                por_estado[est] = por_estado.get(est, 0) + 1

            st.markdown(f"**Total actuaciones:** {total}")
            for est, cnt in por_estado.items():
                st.markdown(f"- **{est}**: {cnt}")

            if trabajadorid and not ver_todo:
                st.caption("Mostrando solo tus actuaciones.")
            elif ver_todo:
                st.caption("Mostrando actuaciones de todo el equipo.")

    # =====================================================
    # CALENDARIO
    # =====================================================
    with col_cal:
        cols = st.columns(7)
        wd = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

        for i, d in enumerate(days):
            with cols[i]:
                st.markdown(f"### {wd[i]} {d.strftime('%d/%m')}")

                daily = [
                    a
                    for a in acts
                    if (a.get("fecha_vencimiento") or "")[:10] == d.date().isoformat()
                ]

                if not daily:
                    st.caption("Sin acciones.")

                for a in daily:
                    _render_actuacion_card(a, clientes_map, supabase, i)

                # Formulario nueva actuacion
                with st.expander(
                    "Nueva accion",
                    expanded=(st.session_state.get("crm_open_day") == i),
                ):
                    render_nueva_actuacion_form(supabase, d, i)


# ======================================================
# Tarjeta de actuacion individual en el calendario
# ======================================================
def _render_actuacion_card(a, clientes_map, supabase, day_index):
    estado = (a.get("crm_actuacion_estado") or {}).get("estado") or a.get("estado") or "-"
    color = COLOR_ESTADO.get(estado, "#6b7280")
    cliente = clientes_map.get(a.get("clienteid"), "Sin cliente")
    desc = a.get("descripcion") or a.get("titulo") or "Actuacion CRM"

    hora_in = safe_time(a.get("hora_inicio"))
    hora_fin = safe_time(a.get("hora_fin"))

    if hora_in and hora_fin:
        franja = f"{hora_in}-{hora_fin}"
    elif hora_in:
        franja = f"desde {hora_in}"
    else:
        franja = ""

    bloque_horario = bool(a.get("hora_inicio") or a.get("hora_fin"))

    st.markdown(
        f"""
        <div style="
            border-left:5px solid {color};
            padding:6px 8px;
            margin:6px 0;
            border-radius:6px;
            background:#f9fafb;">
            <b>{desc}</b><br>
            <small>
                {cliente}
                {' - ' + franja if franja else ''}
                - {estado}
            </small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botones de accion
    btn1, btn2 = st.columns(2)

    # Ver / editar
    with btn1:
        if st.button("Ver / editar", key=f"btn_edit_{a['crm_actuacionid']}"):
            st.session_state["crm_actuacion_detalle_id"] = a["crm_actuacionid"]
            st.session_state["crm_open_day"] = day_index
            st.rerun()

    # Completar (solo si NO es bloque horario)
    if not bloque_horario and estado != "Completada":
        with btn2:
            if st.button("Completar", key=f"btn_comp_{a['crm_actuacionid']}"):
                try:
                    payload = {"fecha_accion": datetime.now().isoformat()}
                    estado_id = _crm_estado_id(supabase, "Completada")
                    if estado_id:
                        payload["crm_actuacion_estadoid"] = estado_id
                    supabase.table("crm_actuacion").update(payload).eq(
                        "crm_actuacionid", a["crm_actuacionid"]
                    ).execute()
                    st.success("Actuacion marcada como completada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al completar: {e}")
