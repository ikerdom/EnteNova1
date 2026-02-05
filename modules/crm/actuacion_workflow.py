import streamlit as st
from datetime import datetime, timedelta
import requests

from modules.api_base import get_api_base
from modules.crm_api import (
    detalle as api_detalle,
    actualizar as api_actualizar,
    crear as api_crear,
    catalogos as api_catalogos,
)


# ======================================================
# WORKFLOW DE LLAMADA (CRM)
# ======================================================

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


def _trabajadores_map() -> dict:
    cache_key = "crm_trabajadores_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        r = requests.get(f"{get_api_base()}/api/catalogos/trabajadores", timeout=15)
        r.raise_for_status()
        rows = r.json() or []
    except Exception:
        rows = []
    mapping = {}
    for t in rows:
        nombre = (t.get("nombre") or "").strip()
        apellidos = (t.get("apellidos") or "").strip()
        label = f"{nombre} {apellidos}".strip() or f"Trabajador {t.get('trabajadorid')}"
        mapping[t.get("trabajadorid")] = label
    st.session_state[cache_key] = mapping
    return mapping


def render_llamada_workflow(supabase, crm_actuacionid: int):
    try:
        act = api_detalle(crm_actuacionid) or {}
    except Exception as e:
        st.error(f"Error cargando actuacion: {e}")
        return

    if not act:
        st.error("No se encontro la actuacion.")
        return

    cliente_nombre = act.get("cliente_nombre") or (f"Cliente {act.get('clienteid')}" if act.get("clienteid") else "-")
    trabajador_map = _trabajadores_map()
    trabajador_nombre = trabajador_map.get(act.get("trabajador_creadorid")) or "-"
    estado = act.get("estado") or "-"

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

            api_actualizar(crm_actuacionid, {"hora_inicio": ahora})
            _registrar_historial(
                supabase,
                act.get("clienteid"),
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

            api_actualizar(crm_actuacionid, payload)

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
                    "fecha_recordatorio": fecha_seg.isoformat(),
                }

                estado_id_p = _crm_estado_id(supabase, "Pendiente")
                if estado_id_p:
                    payload_seg["crm_actuacion_estadoid"] = estado_id_p

                api_crear(payload_seg)
                _registrar_historial(
                    supabase,
                    act.get("clienteid"),
                    f"Programado seguimiento automatico para el {fecha_seg.date()}."
                )

            _registrar_historial(
                supabase,
                act.get("clienteid"),
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

def _registrar_historial(_supa_unused, _clienteid: int, _mensaje: str):
    return None
