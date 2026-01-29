import streamlit as st
from datetime import datetime, timedelta


# ======================================================
# WORKFLOW DE LLAMADA (CRM)
# ======================================================

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


def render_llamada_workflow(supabase, crm_actuacionid: int):
    res = (
        supabase.table("crm_actuacion")
        .select(
            """
            crm_actuacionid,
            clienteid,
            trabajador_creadorid,
            crm_actuacion_estadoid,
            fecha_accion,
            fecha_vencimiento,
            hora_inicio,
            hora_fin,
            duracion_segundos,
            resultado,
            titulo,
            descripcion,
            requiere_seguimiento,
            fecha_recordatorio,
            cliente (clienteid, razonsocial, nombre),
            trabajador!crm_actuacion_trabajador_creadorid_fkey (trabajadorid, nombre, apellidos),
            crm_actuacion_estado (estado)
        """
        )
        .eq("crm_actuacionid", crm_actuacionid)
        .single()
        .execute()
        .data
    )

    if not res:
        st.error("No se encontro la actuacion.")
        return

    act = res
    cliente_nombre = act.get("cliente", {}).get("razonsocial") or act.get("cliente", {}).get("nombre") or "-"
    trabajador_nombre = (
        f"{act['trabajador']['nombre']} {act['trabajador']['apellidos']}"
        if act.get("trabajador")
        else "-"
    )
    estado = (act.get("crm_actuacion_estado") or {}).get("estado") or "-"

    st.markdown(
        f"### Llamada - <b>{cliente_nombre}</b>",
        unsafe_allow_html=True
    )
    st.caption(f"Comercial: {trabajador_nombre} - Estado: **{estado}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"Accion: {act.get('fecha_accion')}")
    with col2:
        st.write(f"Vence: {act.get('fecha_vencimiento')}")
    with col3:
        if act.get("duracion_segundos"):
            m = act["duracion_segundos"] // 60
            s = act["duracion_segundos"] % 60
            st.write(f"Duracion: {m}m {s}s")

    if act.get("descripcion"):
        st.markdown("**Descripcion:**")
        st.write(act["descripcion"])

    st.divider()

    hora_inicio = act.get("hora_inicio")
    hora_fin = act.get("hora_fin")

    def _parse_fecha(x):
        if not x:
            return None
        return datetime.fromisoformat(x.replace("Z", "+00:00"))

    if not hora_inicio:
        if st.button("Iniciar llamada", use_container_width=True):
            ahora = datetime.utcnow().isoformat()

            supabase.table("crm_actuacion") \
                .update({"hora_inicio": ahora}) \
                .eq("crm_actuacionid", crm_actuacionid) \
                .execute()

            _registrar_historial(
                supabase,
                act["clienteid"],
                f"Inicio de llamada (Actuacion #{crm_actuacionid})."
            )

            st.success("Llamada iniciada.")
            st.rerun()

        return
    else:
        st.info(f"Llamada iniciada: {hora_inicio}")

    if hora_inicio and not hora_fin:
        st.markdown("### Finalizar llamada")

        resultado_principal = st.selectbox(
            "Resultado",
            [
                "Contactado - Interesado",
                "Contactado - No interesado",
                "No contesta",
                "Numero incorrecto",
                "Buzon de voz",
                "Otro",
            ],
        )

        notas = st.text_area(
            "Notas / detalles",
            value=act.get("resultado") or "",
        )

        crear_seguimiento = st.checkbox(
            "Crear actuacion de seguimiento automatica",
            value=(resultado_principal in ["Contactado - Interesado", "No contesta"]),
        )

        if crear_seguimiento:
            dias_seg = st.number_input("Dias hasta el seguimiento", 1, 60, 3)

        if st.button("Guardar y finalizar", use_container_width=True):

            ahora = datetime.utcnow()
            inicio_dt = _parse_fecha(hora_inicio)
            duracion = int((ahora - inicio_dt).total_seconds())

            estado_id = _crm_estado_id(supabase, "Completada")
            payload = {
                "hora_fin": ahora.isoformat(),
                "duracion_segundos": duracion,
                "resultado": notas or resultado_principal,
            }
            if estado_id:
                payload["crm_actuacion_estadoid"] = estado_id

            supabase.table("crm_actuacion").update(payload).eq(
                "crm_actuacionid", crm_actuacionid
            ).execute()

            if crear_seguimiento:
                fecha_seg = (ahora + timedelta(days=int(dias_seg))).replace(
                    hour=10, minute=0, second=0, microsecond=0
                )

                payload_seg = {
                    "clienteid": act["clienteid"],
                    "trabajador_creadorid": act.get("trabajador_creadorid"),
                    "descripcion": f"Seguimiento automatico: {resultado_principal}",
                    "fecha_accion": fecha_seg.isoformat(),
                    "fecha_vencimiento": fecha_seg.date().isoformat(),
                    "titulo": "Seguimiento de llamada",
                    "resultado": None,
                    "requiere_seguimiento": True,
                    "fecha_recordatorio": fecha_seg.date().isoformat(),
                }

                estado_id_p = _crm_estado_id(supabase, "Pendiente")
                if estado_id_p:
                    payload_seg["crm_actuacion_estadoid"] = estado_id_p

                supabase.table("crm_actuacion").insert(payload_seg).execute()

                _registrar_historial(
                    supabase,
                    act["clienteid"],
                    f"Programado seguimiento automatico para el {fecha_seg.date()}."
                )

            _registrar_historial(
                supabase,
                act["clienteid"],
                f"Llamada finalizada. Resultado: {resultado_principal}."
            )

            st.success("Llamada finalizada correctamente.")
            st.rerun()

    if hora_fin:
        st.success("La llamada ya esta finalizada.")
        st.write(f"Inicio: {hora_inicio}")
        st.write(f"Fin: {hora_fin}")

        if act.get("resultado"):
            st.markdown("**Notas registradas:**")
            st.write(act["resultado"])


# ======================================================
# REGISTRO DE HISTORIAL CRM (mensajes / actividad)
# ======================================================

def _registrar_historial(supa, clienteid: int, mensaje: str):
    try:
        supa.table("mensaje_contacto").insert({
            "clienteid": clienteid,
            "mensaje": mensaje,
            "fecha": datetime.utcnow().isoformat()
        }).execute()
    except Exception:
        pass
