# CRM Acciones y calendario (API FastAPI + FullCalendar)

from __future__ import annotations

import calendar as _pycalendar
from datetime import date, datetime, timedelta, time
from typing import Optional, Dict, List
import uuid

import streamlit as st
from dateutil.parser import parse as parse_date

from modules.crm_api import (
    listar as api_listar,
    crear as api_crear,
    actualizar as api_actualizar,
    catalogos as api_catalogos,
)
from modules.api_base import get_api_base
from modules.crm_accion_detalle import render_crm_accion_detalle

try:
    from streamlit_calendar import calendar as st_calendar

    _HAS_CAL = True
except Exception:
    _HAS_CAL = False

_ESTADO_COLOR = {
    "pendiente": "#ef4444",
    "en curso": "#f59e0b",
    "completada": "#16a34a",
    "cancelada": "#6b7280",
}

_CSS = """
<style>
.fc .fc-toolbar-title{font-weight:700}
.fc .fc-daygrid-event,.fc .fc-timegrid-event{border-radius:10px}
.fc .fc-button{border-radius:10px}
.fc-event:hover{filter:brightness(1.05)}
.fc .fc-button-primary{background:#2563eb;border:none}
.fc .fc-button-primary:hover{background:#1d4ed8}
</style>
"""


def _color_for(estado: Optional[str]) -> str:
    e = (estado or "").strip().lower()
    return _ESTADO_COLOR.get(e, _ESTADO_COLOR["pendiente"])


def _to_event(row: dict) -> dict:
    start = end = None
    if row.get("fecha_accion"):
        start = parse_date(str(row["fecha_accion"])).isoformat()
        end = (parse_date(str(row["fecha_accion"])) + timedelta(hours=1)).isoformat()
    elif row.get("fecha_vencimiento"):
        d = parse_date(str(row["fecha_vencimiento"])).date()
        start = datetime.combine(d, time.min).isoformat()
        end = (datetime.combine(d, time.min) + timedelta(days=1)).isoformat()

    estado = row.get("estado")
    tipo = row.get("tipo")
    titulo = row.get("titulo") or "(Sin titulo)"
    if tipo:
        titulo = f"{tipo}: {titulo}"

    return {
        "id": str(row.get("crm_actuacionid")),
        "title": titulo,
        "start": start,
        "end": end,
        "allDay": not bool(row.get("fecha_accion")),
        "color": _color_for(estado),
        "extendedProps": {
            "estado": estado,
            "tipo": tipo,
            "clienteid": row.get("clienteid"),
        },
    }


def _load_trabajadores() -> Dict[str, int]:
    try:
        import requests

        r = requests.get(f"{get_api_base()}/api/catalogos/trabajadores", timeout=15)
        r.raise_for_status()
        rows = r.json() or []
    except Exception:
        return {}

    out = {}
    for r in rows:
        nombre = (r.get("nombre") or "").strip()
        apellidos = (r.get("apellidos") or "").strip()
        label = f"{nombre} {apellidos}".strip() or f"Trabajador {r.get('trabajadorid')}"
        out[label] = r.get("trabajadorid")
    return out


def _load_estados_tipos() -> tuple[Dict[str, int], Dict[str, int]]:
    try:
        cats = api_catalogos() or {}
    except Exception:
        cats = {}
    estados = cats.get("estados") or []
    tipos = cats.get("tipos") or []
    estados_map = {e.get("estado"): e.get("crm_actuacion_estadoid") for e in estados if e.get("crm_actuacion_estadoid") is not None}
    tipos_map = {t.get("tipo"): t.get("crm_actuacion_tipoid") for t in tipos if t.get("crm_actuacion_tipoid") is not None}
    return estados_map, tipos_map


def _load_clientes(search: str) -> Dict[str, int]:
    if not search:
        return {}
    try:
        import requests

        r = requests.get(
            f"{get_api_base()}/api/clientes",
            params={"q": search, "page": 1, "page_size": 40},
            timeout=15,
        )
        r.raise_for_status()
        rows = (r.json() or {}).get("data", [])
    except Exception:
        return {}

    out = {}
    for r in rows:
        label = r.get("razonsocial") or r.get("nombre") or f"Cliente {r.get('clienteid')}"
        out[str(label)] = r.get("clienteid")
    return out


def render_crm_acciones(_supabase_unused=None, clienteid: Optional[int] = None):
    st.markdown(_CSS, unsafe_allow_html=True)

    if not _HAS_CAL:
        st.error("Falta dependencia `streamlit-calendar`. Instala con: `pip install streamlit-calendar`.")
        return

    trabajadorid = st.session_state.get("trabajadorid")
    if not trabajadorid:
        st.warning("No hay sesion de trabajador activa.")
        return

    if clienteid is None:
        clienteid = st.session_state.get("cliente_actual")

    estados_map, tipos_map = _load_estados_tipos()
    trabajadores_map = _load_trabajadores()

    top_l, top_c, top_r = st.columns([2, 3, 2])
    with top_l:
        vista = st.radio(
            "Vista",
            ["Mensual", "Semanal", "Diaria"],
            horizontal=True,
            key="crm_vista",
            index=["Mensual", "Semanal", "Diaria"].index(st.session_state.get("crm_vista", "Mensual")),
        )

    with top_c:
        fecha_base = st.date_input("Fecha base", value=st.session_state.get("crm_fecha_base", date.today()))
        st.session_state["crm_fecha_base"] = fecha_base

    with top_r:
        col1, col2 = st.columns(2)
        col1.button("Anterior", on_click=_mover, args=(-1,), key="btn_prev")
        col2.button("Siguiente", on_click=_mover, args=(1,), key="btn_next")

    f1, f2, f3, f4, f5 = st.columns(5)
    filtro_estado = f1.selectbox("Estado", ["Todos"] + list(estados_map.keys()), index=0)
    filtro_tipo = f2.selectbox("Tipo", ["Todos"] + list(tipos_map.keys()), index=0)
    buscar = f3.text_input("Buscar titulo...", placeholder="Ej: llamada, presupuesto, reunion")
    modo_vista = f4.selectbox(
        "Modo",
        ["Calendario", "Lista"],
        index=["Calendario", "Lista"].index(st.session_state.get("crm_modo", "Calendario")),
    )
    rango = f5.selectbox(
        "Rango",
        ["Todo", "Hoy", "7 dias", "30 dias"],
        index=["Todo", "Hoy", "7 dias", "30 dias"].index(st.session_state.get("crm_rango", "Todo")),
    )
    st.session_state["crm_rango"] = rango
    st.session_state["crm_modo"] = modo_vista

    with st.expander("Nueva accion", expanded=False):
        with st.form("form_accion"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Titulo *")
                fecha_venc = st.date_input("Fecha limite", value=fecha_base)
                hora = st.time_input("Hora (opcional)", value=time(9, 0))
            with c2:
                tipo = st.selectbox("Tipo", list(tipos_map.keys()) or ["-"])
                estado = st.selectbox("Estado", list(estados_map.keys()) or ["-"])
                descripcion = st.text_area("Descripcion", placeholder="Detalles...")

            observaciones = st.text_area("Observaciones internas", placeholder="Notas internas...")
            requiere_seguimiento = st.checkbox("Requiere seguimiento", value=False)

            recordatorio_fecha = None
            recordatorio_hora = None
            if requiere_seguimiento:
                r1, r2 = st.columns(2)
                with r1:
                    recordatorio_fecha = st.date_input("Fecha recordatorio", value=fecha_venc)
                with r2:
                    recordatorio_hora = st.time_input("Hora recordatorio", value=time(9, 0))

            st.markdown("Asignar trabajador responsable")
            trab_sel = st.selectbox(
                "Asignar a",
                list(trabajadores_map.keys()) or ["(Ninguno)"],
                index=0,
            )
            trabajador_asignado = trabajadores_map.get(trab_sel, trabajadorid)

            cliente_sel_id = None
            if clienteid:
                cliente_sel_id = clienteid
                st.caption(f"Cliente fijo en este detalle: {clienteid}")
            else:
                cliente_search = st.text_input("Buscar cliente (opcional)", key="crm_cliente_search")
                clientes_map = _load_clientes(cliente_search.strip())
                if clientes_map:
                    cliente_label = st.selectbox(
                        "Cliente",
                        ["(Sin cliente)"] + list(clientes_map.keys()),
                        index=0,
                    )
                    if cliente_label != "(Sin cliente)":
                        cliente_sel_id = clientes_map.get(cliente_label)
                else:
                    cliente_manual = st.number_input(
                        "Cliente ID (opcional)",
                        min_value=0,
                        step=1,
                        value=0,
                    )
                    if cliente_manual > 0:
                        cliente_sel_id = int(cliente_manual)

            st.markdown("---")
            colp1, colp2, colp3 = st.columns(3)
            with colp1:
                st.caption("Resumen")
                st.write(titulo or "-")
                st.write(f"Tipo: {tipo}")
            with colp2:
                st.caption("Fechas")
                st.write(f"Vence: {fecha_venc.isoformat()}")
                st.write(f"Hora: {hora}")
            with colp3:
                st.caption("Asignacion")
                st.write(trab_sel or "-")
                st.write(f"Cliente: {cliente_sel_id or '-'}")

            enviado = st.form_submit_button("Guardar", use_container_width=True)

        if enviado and titulo.strip():
            payload = {
                "titulo": titulo.strip(),
                "descripcion": descripcion or None,
                "observaciones": observaciones or None,
                "crm_actuacion_tipoid": tipos_map.get(tipo),
                "crm_actuacion_estadoid": estados_map.get(estado),
                "fecha_vencimiento": fecha_venc.isoformat(),
                "trabajador_creadorid": trabajadorid,
                "trabajador_asignadoid": trabajador_asignado,
                "requiere_seguimiento": bool(requiere_seguimiento),
            }
            if hora:
                payload["fecha_accion"] = datetime.combine(fecha_venc, hora).replace(microsecond=0).isoformat()
            if requiere_seguimiento and recordatorio_fecha and recordatorio_hora:
                payload["fecha_recordatorio"] = datetime.combine(
                    recordatorio_fecha, recordatorio_hora
                ).replace(microsecond=0).isoformat()
            if cliente_sel_id:
                payload["clienteid"] = cliente_sel_id

            try:
                api_crear(payload)
                st.toast("Accion creada.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al crear accion: {e}")

    if st.session_state.get("force_reload"):
        st.session_state["force_reload"] = False
        st.rerun()

    try:
        payload = {
            "trabajador_asignadoid": trabajadorid,
            "clienteid": clienteid,
            "crm_actuacion_estadoid": estados_map.get(filtro_estado) if filtro_estado != "Todos" else None,
            "crm_actuacion_tipoid": tipos_map.get(filtro_tipo) if filtro_tipo != "Todos" else None,
            "buscar": buscar or None,
        }
        rows = api_listar(payload).get("data", [])
    except Exception as e:
        st.error(f"Error al cargar acciones: {e}")
        rows = []

    if rango != "Todo":
        today = date.today()
        if rango == "Hoy":
            start = today
        elif rango == "7 dias":
            start = today - timedelta(days=7)
        else:
            start = today - timedelta(days=30)

        def _in_range(r):
            raw = r.get("fecha_accion") or r.get("fecha_vencimiento")
            if not raw:
                return False
            try:
                d = parse_date(str(raw)).date()
            except Exception:
                return False
            return d >= start

        rows = [r for r in rows if _in_range(r)]

    # Resumen rápido
    counts = {}
    for r in rows:
        key = (r.get("estado") or "Sin estado").lower()
        counts[key] = counts.get(key, 0) + 1
    if rows:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(rows))
        m2.metric("Pendientes", counts.get("pendiente", 0))
        m3.metric("En curso", counts.get("en curso", 0))
        m4.metric("Completadas", counts.get("completada", 0))

    if st.session_state.get("crm_modo") == "Lista":
        for r in rows:
            titulo = r.get("titulo") or "(Sin titulo)"
            tipo = r.get("tipo") or "-"
            estado = r.get("estado") or "-"
            vence = str(r.get("fecha_vencimiento") or "")[:16].replace("T", " ")
            accion = str(r.get("fecha_accion") or "")[:16].replace("T", " ")
            cliente = r.get("clienteid") or "-"
            color = _color_for(estado)

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1.4, 1.2, 1.2])
                with c1:
                    st.markdown(f"**{titulo}**")
                    st.caption(f"Tipo: {tipo} · Cliente: {cliente}")
                with c2:
                    st.markdown(
                        f"""<div style="padding:4px 10px;border-radius:999px;background:{color};color:#fff;font-weight:700;text-align:center;">{estado}</div>""",
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.caption("Vence")
                    st.write(vence or "-")
                with c4:
                    st.caption("Accion")
                    st.write(accion or "-")
        return

    events = [_to_event(r) for r in rows]

    initial_view = {"Mensual": "dayGridMonth", "Semanal": "timeGridWeek", "Diaria": "timeGridDay"}[vista]
    options = {
        "initialView": initial_view,
        "locale": "es",
        "firstDay": 1,
        "nowIndicator": True,
        "slotMinTime": "08:00:00",
        "slotMaxTime": "20:00:00",
        "height": "auto",
        "expandRows": True,
        "selectable": True,
        "dayMaxEvents": True,
        "initialDate": fecha_base.isoformat(),
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
    }

    ret = st_calendar(events=events, options=options, key="crm_calendar")

    ev_click = (ret.get("eventClick", {}) or {}).get("event")
    if ev_click and ev_click.get("id"):
        st.session_state["crm_accion_abierta"] = int(ev_click["id"])

    if st.session_state.get("crm_accion_abierta"):
        eid = st.session_state["crm_accion_abierta"]
        suffix = str(uuid.uuid4())[:8]
        st.markdown("---")
        st.subheader("Detalle de la accion seleccionada")
        render_crm_accion_detalle(None, eid)

        st.markdown("Acciones rapidas")
        with st.expander("Posponer accion", expanded=False):
            new_date = st.date_input("Nueva fecha", date.today() + timedelta(days=1), key=f"posp_date_{eid}_{suffix}")
            new_time = st.time_input("Nueva hora", time(9, 0), key=f"posp_time_{eid}_{suffix}")
            if st.button("Guardar nueva fecha", key=f"btn_posp_{eid}_{suffix}", use_container_width=True):
                api_actualizar(
                    eid,
                    {
                        "fecha_vencimiento": new_date.isoformat(),
                        "fecha_accion": datetime.combine(new_date, new_time).isoformat(),
                    },
                )
                st.toast("Accion actualizada.")
                st.session_state["force_reload"] = True
                st.rerun()

        with st.expander("Cerrar", expanded=False):
            if st.button("Cerrar accion", key=f"cerrar_{eid}_{suffix}", use_container_width=True):
                st.session_state.pop("crm_accion_abierta", None)
                st.rerun()


def _mover(delta: int):
    base = st.session_state.get("crm_fecha_base", date.today())
    vista = st.session_state.get("crm_vista", "Mensual")
    if vista == "Mensual":
        y, m = base.year, base.month
        m += delta
        if m < 1:
            y -= 1
            m = 12
        elif m > 12:
            y += 1
            m = 1
        st.session_state["crm_fecha_base"] = date(y, m, min(base.day, _dias_mes(y, m)))
    elif vista == "Semanal":
        st.session_state["crm_fecha_base"] = base + timedelta(days=7 * delta)
    else:
        st.session_state["crm_fecha_base"] = base + timedelta(days=delta)


def _dias_mes(y: int, m: int) -> int:
    return _pycalendar.monthrange(y, m)[1]
