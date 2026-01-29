from datetime import datetime, date, time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


# =========================================================
# API helpers (fallback)
# =========================================================

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
    except Exception:
        return []


def api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# =========================================================
# CRM helpers (prefer Supabase)
# =========================================================

def _get_trabajadores(supa):
    if supa:
        try:
            return (
                supa.table("trabajador")
                .select("trabajadorid,nombre,apellidos")
                .order("nombre")
                .execute()
                .data
                or []
            )
        except Exception:
            pass
    return api_get("/api/catalogos/trabajadores") or []


def _get_estados(supa):
    if supa:
        try:
            rows = supa.table("crm_actuacion_estado").select("crm_actuacion_estadoid, estado").execute().data or []
            return {r["estado"]: r["crm_actuacion_estadoid"] for r in rows}
        except Exception:
            return {}
    return {}


def _listar_acciones(supa, clienteid: int) -> List[Dict[str, Any]]:
    if supa:
        try:
            return (
                supa.table("crm_actuacion")
                .select(
                    "crm_actuacionid,clienteid,trabajador_asignadoid,crm_actuacion_estadoid,"
                    "titulo,descripcion,fecha_vencimiento"
                )
                .eq("clienteid", clienteid)
                .order("fecha_accion", desc=True)
                .execute()
                .data
                or []
            )
        except Exception:
            return []
    return api_get(f"/api/clientes/{clienteid}/crm") or []


def _crear_accion(supa, clienteid: int, payload: dict) -> bool:
    if supa:
        try:
            payload = dict(payload)
            payload["clienteid"] = clienteid
            supa.table("crm_actuacion").insert(payload).execute()
            return True
        except Exception:
            return False
    return bool(api_post(f"/api/clientes/{clienteid}/crm", payload))


# =========================================================
# CRM - Acciones y seguimiento (UI ONLY)
# =========================================================

def render_crm_form(clienteid: int):
    clienteid = int(clienteid)

    st.subheader("Seguimiento CRM")
    st.caption("Acciones comerciales o administrativas asociadas al cliente.")

    trabajadorid = st.session_state.get("trabajadorid")
    if not trabajadorid:
        st.warning("No hay sesion de trabajador activa.")
        return

    supa = st.session_state.get("supa")

    trabajadores = _get_trabajadores(supa)
    trabajadores_map = {
        f"{t.get('nombre', '')} {t.get('apellidos', '')}".strip(): t.get("trabajadorid")
        for t in (trabajadores or [])
        if t.get("trabajadorid") is not None
    }
    trabajadores_rev = {v: k for k, v in trabajadores_map.items()}

    estado_map = _get_estados(supa)
    estado_rev = {v: k for k, v in estado_map.items()}

    with st.expander("Registrar nueva accion"):
        with st.form(f"crm_new_{clienteid}"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Titulo *")
            with c2:
                fecha_venc = st.date_input("Fecha limite", value=date.today())
                hora = st.time_input("Hora (opcional)", value=time(9, 0))
                descripcion = st.text_area(
                    "Descripcion / recordatorio",
                    placeholder="Detalles de la accion...",
                    height=80,
                )

            st.markdown("**Asignar responsable**")
            nombre_logueado = st.session_state.get("user_nombre", "").lower()
            idx_default = 0
            for i, n in enumerate(trabajadores_map.keys()):
                if nombre_logueado and nombre_logueado in n.lower():
                    idx_default = i
                    break

            trab_sel = st.selectbox(
                "Trabajador",
                list(trabajadores_map.keys()) if trabajadores_map else ["Sin datos"],
                index=idx_default if trabajadores_map else 0,
            )

            trabajador_asignado = trabajadores_map.get(trab_sel, trabajadorid)

            submitted = st.form_submit_button("Guardar accion", use_container_width=True)

        if submitted:
            if not titulo.strip():
                st.warning("El titulo es obligatorio.")
                return

            payload = {
                "titulo": titulo.strip(),
                "descripcion": descripcion.strip() or None,
                "crm_actuacion_estadoid": estado_map.get("Pendiente"),
                "fecha_vencimiento": fecha_venc.isoformat(),
                "trabajador_creadorid": trabajadorid,
                "trabajador_asignadoid": trabajador_asignado,
            }

            if hora:
                payload["fecha_accion"] = datetime.combine(fecha_venc, hora).replace(microsecond=0).isoformat()

            ok = _crear_accion(supa, clienteid, payload)
            if ok:
                st.toast(f"Accion creada y asignada a {trab_sel}.")
                st.rerun()
            else:
                st.error("No se pudo crear la accion.")

    st.markdown("---")
    st.markdown("#### Acciones registradas")

    acciones: List[Dict[str, Any]] = _listar_acciones(supa, clienteid)
    if not acciones:
        st.info("Este cliente no tiene acciones registradas.")
        return

    for a in acciones:
        estado = estado_rev.get(a.get("crm_actuacion_estadoid"), "Pendiente")
        titulo = a.get("titulo", "-")
        descripcion = a.get("descripcion") or ""
        fecha_venc = a.get("fecha_vencimiento", "-")
        trabajador_asignado = trabajadores_rev.get(a.get("trabajador_asignadoid"), "-")

        color_estado = {
            "Pendiente": "#f59e0b",
            "Completada": "#16a34a",
            "Cancelada": "#6b7280",
        }.get(estado, "#f59e0b")

        st.markdown(
            f"""
            <div style="border:1px solid #e5e7eb;border-radius:10px;padding:10px;margin-bottom:10px;background:#ffffff;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
                    <div style="font-weight:600;">{titulo}</div>
                    <span style="padding:2px 8px;border-radius:999px;background:{color_estado};color:#fff;font-size:0.8rem;">{estado}</span>
                </div>
                <div style="font-size:0.9rem;color:#6b7280;margin-top:6px;">{descripcion}</div>
                <div style="font-size:0.86rem;color:#6b7280;margin-top:6px;">
                    Limite: {fecha_venc} ? Asignado: {trabajador_asignado}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
