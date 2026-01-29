from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import streamlit as st

from modules.incidencia_workflow import render_incidencia_detalle as _render_inci_detalle


# ======================================================
# Gestion de incidencias - vista principal
# ======================================================
def render_incidencia_lista(supabase):
    st.session_state["supa"] = supabase

    st.header("Gestion de incidencias")
    st.caption(
        "Monitorea y resuelve incidencias de clientes, pedidos o productos; abre el workflow completo para cada una."
    )

    session = st.session_state
    session.setdefault("inci_view", "Tarjetas")

    trabajadores = _load_trabajadores(supabase)

    # ----------------------------
    # Crear nueva incidencia
    # ----------------------------
    with st.expander("Registrar nueva incidencia", expanded=False):
        with st.form("inci_new"):
            c1, c2 = st.columns(2)
            with c1:
                tipo = st.text_input("Tipo *", placeholder="Ej: Retraso, Producto danado, Error facturacion")
                origen_tipo = st.selectbox("Origen", ["cliente", "pedido", "producto", "otro"])
                prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], index=1)
            with c2:
                descripcion = st.text_area("Descripcion *", height=120)
                responsable_sel = st.selectbox("Responsable", list(trabajadores.keys()) or ["(Sin asignar)"])

            cliente_id = None
            if origen_tipo == "cliente":
                cliente_search = st.text_input("Buscar cliente (opcional)")
                clientes_map = _load_clientes(supabase, cliente_search.strip())
                if clientes_map:
                    cliente_label = st.selectbox(
                        "Cliente",
                        ["(Sin cliente)"] + list(clientes_map.keys()),
                        index=0,
                    )
                    if cliente_label != "(Sin cliente)":
                        cliente_id = clientes_map.get(cliente_label)
                else:
                    cliente_manual = st.number_input("Cliente ID (opcional)", min_value=0, step=1, value=0)
                    if cliente_manual > 0:
                        cliente_id = int(cliente_manual)

            origen_id = None
            if origen_tipo in ("pedido", "producto"):
                origen_id = st.number_input(
                    f"{origen_tipo.capitalize()} ID (opcional)",
                    min_value=0,
                    step=1,
                    value=0,
                )
                if origen_id == 0:
                    origen_id = None

            enviar = st.form_submit_button("Registrar incidencia", use_container_width=True)

        if enviar:
            if not tipo.strip() or not descripcion.strip():
                st.warning("Tipo y descripcion son obligatorios.")
            else:
                payload = {
                    "tipo": tipo.strip(),
                    "descripcion": descripcion.strip(),
                    "origen_tipo": origen_tipo,
                    "prioridad": prioridad,
                    "responsableid": trabajadores.get(responsable_sel),
                    "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
                    "estado": "Abierta",
                }
                if cliente_id:
                    payload["clienteid"] = cliente_id
                if origen_id:
                    payload["origen_id"] = origen_id

                estado_id = _get_estado_id(supabase, "Abierta")
                if estado_id:
                    payload["incidencia_estadoid"] = estado_id

                try:
                    supabase.table("incidencia").insert(payload).execute()
                    st.success("Incidencia registrada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo registrar: {e}")

    # ----------------------------
    # Filtros
    # ----------------------------
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        tipo_sel = st.selectbox("Origen tipo", ["Todos", "cliente", "pedido", "producto", "otro"])
    with col2:
        estado_sel = st.selectbox("Estado", ["Todos", "Abierta", "En curso", "Solucionada", "Rechazada"])
    with col3:
        asignado_sel = st.selectbox("Responsable", ["Todos"] + list(trabajadores.keys()))
    with col4:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="inci_view")

    # ----------------------------
    # Query principal
    # ----------------------------
    incidencias: List[dict] = []
    try:
        base = supabase.table("incidencia").select("*")
        if tipo_sel != "Todos":
            base = base.eq("origen_tipo", tipo_sel)
        if estado_sel != "Todos":
            base = base.eq("estado", estado_sel)
        if asignado_sel != "Todos":
            base = base.eq("responsableid", trabajadores[asignado_sel])
        data = base.order("fecha_creacion", desc=True).limit(150).execute()
        incidencias = data.data or []
    except Exception as e:
        st.error(f"Error cargando incidencias: {e}")
        return

    if not incidencias:
        st.info("No hay incidencias con los filtros seleccionados.")
        return

    # ----------------------------
    # KPIs rapidos
    # ----------------------------
    total = len(incidencias)
    abiertas = sum(1 for i in incidencias if "abier" in str(i.get("estado", "")).lower())
    curso = sum(1 for i in incidencias if "curso" in str(i.get("estado", "")).lower())
    solu = sum(1 for i in incidencias if "solu" in str(i.get("estado", "")).lower())
    rech = sum(1 for i in incidencias if "rech" in str(i.get("estado", "")).lower())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Abiertas", abiertas)
    c3.metric("En curso", curso)
    c4.metric("Solucionadas", solu)
    c5.metric("Rechazadas", rech)

    # ----------------------------
    # Render listado
    # ----------------------------
    if view == "Tarjetas":
        cols = st.columns(2)
        for idx, i in enumerate(incidencias):
            with cols[idx % 2]:
                _render_incidencia_card(i, trabajadores)
    else:
        _render_incidencia_table(incidencias, trabajadores)

    # Modal de detalle
    if st.session_state.get("inci_show_modal"):
        _render_inci_detalle(supabase)


# ======================================================
# Tarjetas
# ======================================================
def _render_incidencia_card(i, trabajadores):
    estado = i.get("estado", "-")
    trabajador = _label(trabajadores, i.get("responsableid"))
    tipo = i.get("origen_tipo", "-")
    color = "#9ca3af"

    e = estado.lower()
    if "abier" in e:
        color = "#f59e0b"
    elif "curso" in e:
        color = "#3b82f6"
    elif "solu" in e:
        color = "#10b981"
    elif "rech" in e:
        color = "#ef4444"

    st.markdown(
        f"""
    <div style='border:1px solid #ddd;border-radius:10px;padding:10px;margin-bottom:10px;background:#fff;'>
        <div style='display:flex;justify-content:space-between;align-items:center;'>
            <b>#{i['incidenciaid']} - {tipo}</b>
            <span style='background:{color};color:#fff;padding:2px 8px;border-radius:8px;font-size:0.8rem;'>{estado}</span>
        </div>
        <p style='margin-top:6px;'><b>{i.get('tipo','-')}</b> - {i.get('descripcion','')}</p>
        <p style='color:#555;font-size:0.85rem;'>Resp: {trabajador or '-'} - {i.get('fecha_creacion','')}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ver workflow", key=f"detalle_{i['incidenciaid']}", use_container_width=True):
            st.session_state["inci_detalle_id"] = i["incidenciaid"]
            st.session_state["inci_show_modal"] = True
            st.rerun()
    with col2:
        if st.button("Marcar solucionada", key=f"solve_{i['incidenciaid']}", use_container_width=True):
            now = datetime.now().isoformat(timespec="seconds")
            supa = st.session_state.get("supa")
            if supa:
                try:
                    supa.table("incidencia").update(
                        {
                            "estado": "Solucionada",
                            "fecha_resolucion": now,
                            "resolucion": "Cerrada desde listado",
                        }
                    ).eq("incidenciaid", i["incidenciaid"]).execute()
                    st.success("Incidencia marcada como solucionada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo marcar: {e}")


# ======================================================
# Tabla
# ======================================================
def _render_incidencia_table(data, trabajadores):
    if not data:
        st.info("No hay incidencias para mostrar.")
        return

    df = pd.DataFrame(data)
    df["Responsable"] = df["responsableid"].apply(lambda rid: _label(trabajadores, rid))

    show_cols = ["incidenciaid", "tipo", "origen_tipo", "descripcion", "estado", "Responsable", "fecha_creacion"]
    show_cols = [c for c in show_cols if c in df.columns]

    st.dataframe(df[show_cols].sort_values("fecha_creacion", ascending=False), hide_index=True, use_container_width=True)

    opts = {f"#{r['incidenciaid']} - {r.get('tipo','')[:30]}": r["incidenciaid"] for r in data}
    sel_label = st.selectbox("Abrir incidencia", list(opts.keys()), key="inci_sel")
    if st.button("Ver workflow seleccionado", key="inci_sel_btn", use_container_width=True):
        st.session_state["inci_detalle_id"] = opts[sel_label]
        st.session_state["inci_show_modal"] = True
        st.rerun()


# ======================================================
# Helpers
# ======================================================
def _label(d: dict, idv):
    for k, v in (d or {}).items():
        if v == idv:
            return k
    return "-"


def _load_trabajadores(supabase) -> dict:
    if supabase is None:
        return {}

    try:
        rows = (
            supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos")
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception:
        return {}

    result = {}
    for r in rows:
        nombre = (r.get("nombre") or "").strip()
        apellidos = (r.get("apellidos") or "").strip()
        etiqueta = f"{nombre} {apellidos}".strip() or f"Trabajador {r.get('trabajadorid')}"
        result[etiqueta] = r.get("trabajadorid")
    return result


def _load_clientes(supabase, search: str) -> Dict[str, int]:
    if supabase is None or not search:
        return {}
    try:
        rows = (
            supabase.table("cliente")
            .select("clienteid, razonsocial, nombre")
            .ilike("razonsocial", f"%{search}%")
            .order("razonsocial")
            .limit(40)
            .execute()
            .data
            or []
        )
    except Exception:
        return {}

    out = {}
    for r in rows:
        label = r.get("razonsocial") or r.get("nombre") or f"Cliente {r.get('clienteid')}"
        out[str(label)] = r.get("clienteid")
    return out


def _get_estado_id(supabase, estado: str) -> Optional[int]:
    if not supabase:
        return None
    try:
        rows = (
            supabase.table("incidencia_estado")
            .select("*")
            .execute()
            .data
            or []
        )
        for r in rows:
            nombre = (r.get("estado") or r.get("nombre") or "").strip().lower()
            if nombre == estado.lower():
                return r.get("incidencia_estadoid")
    except Exception:
        return None
    return None
