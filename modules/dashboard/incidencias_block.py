# modules/dashboard/incidencias_block.py

import streamlit as st
from modules.dashboard.utils import safe_date


def _get_estado_id(supabase, estado: str):
    try:
        row = (
            supabase.table("incidencia_estado")
            .select("incidencia_estadoid, estado")
            .eq("estado", estado)
            .single()
            .execute()
            .data
        )
        return row.get("incidencia_estadoid") if row else None
    except Exception:
        return None


def render_incidencias_blocks(supabase, trabajadorid: int | None):
    # --------------------------
    # Incidencias abiertas Responsable
    # --------------------------
    st.subheader("Incidencias abiertas Responsable")
    try:
        estado_id = _get_estado_id(supabase, "Abierta")
        inc_q = (
            supabase.table("incidencia")
            .select(
                "incidenciaid, incidencia_titulo, descripcion, fecha_creacion, "
                "incidencia_estado(estado), trabajador_creadorid, trabajador_asignadoid"
            )
            .eq("incidencia_estadoid", estado_id)
        )
        if trabajadorid:
            inc_q = inc_q.eq("trabajador_creadorid", trabajadorid)

        inc_resp = inc_q.order("fecha_creacion", desc=True).limit(10).execute().data or []

        if not inc_resp:
            st.success("No tienes incidencias abiertas como responsable.")
        else:
            trab_ids = list(
                {i["trabajador_creadorid"] for i in inc_resp if i.get("trabajador_creadorid")}
                | {i.get("trabajador_asignadoid") for i in inc_resp if i.get("trabajador_asignadoid")}
            )
            trab_map = {}
            if trab_ids:
                rows_trab = (
                    supabase.table("trabajador")
                    .select("trabajadorid, nombre, apellidos")
                    .in_("trabajadorid", trab_ids)
                    .execute()
                    .data or []
                )
                trab_map = {
                    t["trabajadorid"]: f"{t.get('nombre','')} {t.get('apellidos','')}".strip()
                    for t in rows_trab
                }

            for i_row in inc_resp:
                tipo = i_row.get("incidencia_titulo") or "Incidencia"
                desc = i_row.get("descripcion") or ""
                fecha_c = safe_date(i_row.get("fecha_creacion"))
                resp_name = trab_map.get(i_row.get("trabajador_creadorid"), "Sin responsable")
                asig_name = trab_map.get(i_row.get("trabajador_asignadoid"), "Sin asignado")
                st.markdown(
                    f"**{tipo}** - {desc}  \n"
                    f"Fecha: {fecha_c}  \n"
                    f"Responsable: {resp_name} - Asignado: {asig_name}"
                )
    except Exception as e:
        st.warning(f"No se pudieron cargar incidencias responsable: {e}")

    st.markdown("---")

    # --------------------------
    # Incidencias abiertas Asignadas al usuario
    # --------------------------
    st.subheader("Incidencias abiertas asignadas")
    try:
        if not trabajadorid:
            st.caption("No hay usuario trabajador en sesion.")
            return

        estado_id = _get_estado_id(supabase, "Abierta")
        inc_asig = (
            supabase.table("incidencia")
            .select(
                "incidenciaid, incidencia_titulo, descripcion, fecha_creacion, "
                "incidencia_estado(estado), trabajador_creadorid, trabajador_asignadoid"
            )
            .eq("incidencia_estadoid", estado_id)
            .eq("trabajador_asignadoid", trabajadorid)
            .order("fecha_creacion", desc=True)
            .limit(10)
            .execute()
            .data or []
        )

        if not inc_asig:
            st.success("No tienes incidencias abiertas asignadas.")
        else:
            trab_ids2 = list(
                {i["trabajador_creadorid"] for i in inc_asig if i.get("trabajador_creadorid")}
                | {i.get("trabajador_asignadoid") for i in inc_asig if i.get("trabajador_asignadoid")}
            )
            trab_map2 = {}
            if trab_ids2:
                rows_trab2 = (
                    supabase.table("trabajador")
                    .select("trabajadorid, nombre, apellidos")
                    .in_("trabajadorid", trab_ids2)
                    .execute()
                    .data or []
                )
                trab_map2 = {
                    t["trabajadorid"]: f"{t.get('nombre','')} {t.get('apellidos','')}".strip()
                    for t in rows_trab2
                }

            for i_row in inc_asig:
                tipo = i_row.get("incidencia_titulo") or "Incidencia"
                desc = i_row.get("descripcion") or ""
                fecha_c = safe_date(i_row.get("fecha_creacion"))
                resp_name = trab_map2.get(i_row.get("trabajador_creadorid"), "Sin responsable")
                asig_name = trab_map2.get(i_row.get("trabajador_asignadoid"), "Sin asignado")
                st.markdown(
                    f"**{tipo}** - {desc}  \n"
                    f"Fecha: {fecha_c}  \n"
                    f"Responsable: {resp_name} - Asignado: {asig_name}"
                )
    except Exception as e:
        st.warning(f"No se pudieron cargar incidencias asignadas: {e}")
