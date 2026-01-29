# modules/incidencia_workflow.py
# ======================================================
# ⚠️ Gestión de incidencias — Workflow profesional (versión final)
# ======================================================
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

# ======================================================
# 🔹 Loaders reutilizables
# ======================================================
try:
    from modules.pedido_models import load_trabajadores, load_clientes
except Exception:
    def load_trabajadores(_supabase) -> Dict[str, int]:
        try:
            rows = (
                _supabase.table("trabajador")
                .select("trabajadorid, nombre, habilitado")
                .eq("habilitado", True)
                .order("nombre")
                .execute()
                .data or []
            )
            return {r["nombre"]: r["trabajadorid"] for r in rows if r.get("trabajadorid")}
        except Exception:
            return {}

    def load_clientes(_supabase) -> Dict[str, int]:
        try:
            rows = (
                _supabase.table("cliente")
                .select("clienteid, razonsocial, nombre")
                .order("razonsocial")
                .limit(5000)
                .execute()
                .data or []
            )
            return {(r.get("razonsocial") or r.get("nombre","")): r["clienteid"] for r in rows if r.get("clienteid")}
        except Exception:
            return {}

# ======================================================
# 🧱 Helpers
# ======================================================
def _label(mapping: Dict[str, Any], idv: Any) -> str:
    for k, v in (mapping or {}).items():
        if v == idv:
            return k
    return "-"

def _safe(v, default="-"):
    return v if v not in (None, "", "null") else default

def _estado_badge(estado_nombre: str) -> str:
    e = (estado_nombre or "-").lower()
    color, emoji = "#9ca3af", "📩"
    if "abier" in e: color, emoji = "#f59e0b", "📩"
    elif "curso" in e: color, emoji = "#3b82f6", "🔄"
    elif "solu" in e: color, emoji = "#10b981", "✅"
    elif "rech" in e: color, emoji = "#ef4444", "🚫"
    return f"<span style='background:{color};color:#fff;padding:4px 10px;border-radius:999px;font-size:0.82rem;'>{emoji} {estado_nombre}</span>"

def _load_estados(_supabase) -> Dict[str, int]:
    try:
        rows = (
            _supabase.table("incidencia_estado")
            .select("incidencia_estadoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("incidencia_estadoid")
            .execute()
            .data or []
        )
        return {r["nombre"]: r["incidencia_estadoid"] for r in rows}
    except Exception:
        return {"Abierta": None, "En curso": None, "Solucionada": None, "Rechazada": None}

def _estado_text_from_id(estado_id: Optional[int], estados: Dict[str, int]) -> str:
    if not estado_id:
        return "-"
    for nombre, eid in estados.items():
        if eid == estado_id:
            return nombre
    return "-"

def _estado_idx(nombre: str) -> int:
    n = (nombre or "").lower()
    if "curso" in n: return 1
    if "solu" in n: return 2
    if "rech" in n: return 3
    return 0

def _prio_index(p):
    if not p: return 1
    p = p.lower()
    if "baj" in p: return 0
    if "alt" in p: return 2
    return 1

# ======================================================
# 🔧 Acciones básicas
# ======================================================
def _add_comentario(supabase, incidenciaid: int, comentario: str, usuario: str = "Usuario"):
    supabase.table("incidencia_comentario").insert({
        "incidenciaid": incidenciaid,
        "comentario": comentario.strip(),
        "usuario": usuario,
        "fecha": datetime.now().isoformat(timespec="seconds")
    }).execute()

def _update_incidencia(supabase, incidenciaid: int, payload: dict):
    supabase.table("incidencia").update(payload).eq("incidenciaid", incidenciaid).execute()

# ======================================================
# 💳 Tarjeta
# ======================================================
def _render_incidencia_card(i, trabajadores, clientes, estados_map):
    cliente_name = "-"
    if i.get("clienteid"):
        cliente_name = _label(clientes, i["clienteid"])

    estado_txt = _estado_text_from_id(i.get("incidencia_estadoid"), estados_map) or i.get("estado", "-")
    badge = _estado_badge(estado_txt)
    trabajador = _label(trabajadores, i.get("responsableid"))
    tipo_origen = i.get("origen_tipo", "-")
    titulo = _safe(i.get("tipo"))
    desc = _safe(i.get("descripcion"))
    fecha = _safe(i.get("fecha_creacion"))

    st.markdown(f"""
        <div style='border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:12px;background:#fff;'>
            <div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'>
                <div><b>#{i['incidenciaid']}</b> · {tipo_origen} · <span style='opacity:.75'>{cliente_name}</span></div>
                {badge}
            </div>
            <div style='margin-top:6px;'>
                <div style='font-weight:600;'>{titulo}</div>
                <div style='color:#555;'>{desc}</div>
            </div>
            <div style='margin-top:6px;color:#6b7280;font-size:0.9rem;'>👤 {trabajador} · 📅 {fecha}</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("👁️ Ver workflow", key=f"inci_work_{i['incidenciaid']}", use_container_width=True):
            st.session_state["inci_detalle_id"] = i["incidenciaid"]
            st.session_state["inci_show_modal"] = True
            st.rerun()
    with c2:
        st.button("✅ Marcar solucionada", key=f"inci_solve_{i['incidenciaid']}", use_container_width=True, disabled=True)

# ======================================================
# 📋 Tabla
# ======================================================
def _render_incidencia_table(rows, trabajadores, clientes, estados_map):
    if not rows:
        st.info("📭 No hay incidencias.")
        return
    df = pd.DataFrame(rows)
    df["Responsable"] = df["responsableid"].apply(lambda x: _label(trabajadores, x))
    df["Cliente"] = df["clienteid"].apply(lambda x: _label(clientes, x))
    df["Estado"] = df.apply(lambda r: _estado_text_from_id(r.get("incidencia_estadoid"), estados_map) or r.get("estado", "-"), axis=1)
    st.dataframe(df[["incidenciaid", "tipo", "descripcion", "Estado", "Cliente", "Responsable", "fecha_creacion"]], use_container_width=True)

# ======================================================
# 🕒 Timeline
# ======================================================
def _render_timeline(comentarios):
    if not comentarios:
        st.info("No hay conversaciones todavía.")
        return
    for c in sorted(comentarios, key=lambda x: x.get("fecha") or ""):
        usuario = _safe(c.get("usuario"), "Sistema")
        fecha = _safe(c.get("fecha"), "")
        texto = _safe(c.get("comentario"), "")
        is_cliente = "cliente" in usuario.lower()
        bg = "#f3f4f6" if is_cliente else "#eef2ff"
        st.markdown(f"""
            <div style="display:flex;justify-content:{'flex-start' if is_cliente else 'flex-end'};margin:8px 0;">
              <div style="max-width:75%;background:{bg};border:1px solid #e5e7eb;padding:10px;border-radius:12px;">
                <div style="font-size:0.85rem;color:#6b7280;">{usuario} · {fecha}</div>
                <div style="margin-top:4px;white-space:pre-wrap;">{texto}</div>
              </div>
            </div>
        """, unsafe_allow_html=True)

# ======================================================
# 🧾 Modal Detalle (con evolución de estado)
# ======================================================
def render_incidencia_detalle(supabase):
    incidenciaid = st.session_state.get("inci_detalle_id")
    if not incidenciaid:
        return
    try:
        data = supabase.table("incidencia").select("*").eq("incidenciaid", incidenciaid).execute()
        i = (data.data or [None])[0]
        if not i:
            st.warning("Incidencia no encontrada.")
            return
    except Exception as e:
        st.error(f"❌ Error cargando incidencia: {e}")
        return

    trabajadores = load_trabajadores(supabase)
    clientes = load_clientes(supabase)
    estados_map = _load_estados(supabase)

    estado_txt = _estado_text_from_id(i.get("incidencia_estadoid"), estados_map) or i.get("estado", "-")
    badge = _estado_badge(estado_txt)

    cliente_name = _label(clientes, i.get("clienteid"))
    origen_tipo = i.get("origen_tipo", "-")
    origen_id = i.get("origen_id")

    # Enriquecemos contexto
    origen_info = "-"
    try:
        if origen_tipo == "pedido" and origen_id:
            p = supabase.table("pedido").select("numero, fecha_pedido").eq("pedidoid", origen_id).execute().data
            if p:
                origen_info = f"Pedido #{p[0].get('numero','-')} ({p[0].get('fecha_pedido','-')})"
        elif origen_tipo == "producto" and origen_id:
            pr = supabase.table("producto").select("nombre").eq("productoid", origen_id).execute().data
            if pr:
                origen_info = f"Producto: {pr[0].get('nombre','-')}"
        elif origen_tipo == "cliente" and origen_id:
            cl = supabase.table("cliente").select("razonsocial, nombre").eq("clienteid", origen_id).execute().data
            if cl:
                origen_info = f"Cliente: {cl[0].get('razonsocial') or cl[0].get('nombre','-')}"
    except Exception:
        pass

    st.markdown("---")
    st.markdown(f"### 🧾 Incidencia #{incidenciaid}")
    st.markdown(badge, unsafe_allow_html=True)
    st.caption(f"📅 Creada: {_safe(i.get('fecha_creacion'))} · 👤 Responsable: {_safe(_label(trabajadores, i.get('responsableid')))}")
    st.write(f"**Tipo:** {_safe(i.get('tipo'))} ({_safe(origen_tipo)})")
    st.write(f"**Cliente:** {_safe(cliente_name)}")
    st.write(f"**Relacionado con:** {_safe(origen_info)}")

    # ======================================================
    # 🧪 Evolución de estado (auditoría)
    # ======================================================
    st.markdown("### 🧪 Evolución de estado")
    try:
        estado_log = (
            supabase.table("incidencia_estado_log")
            .select("*")
            .eq("incidenciaid", incidenciaid)
            .order("fecha", desc=False)
            .execute()
            .data or []
        )
    except Exception:
        estado_log = []

    if not estado_log:
        st.caption("No hay cambios de estado registrados todavía.")
    else:
        for ev in estado_log:
            f = (ev.get("fecha") or "")[:19]
            fr = ev.get("estado_from") or "—"
            to = ev.get("estado_to") or "—"
            who = ev.get("usuario") or "Sistema"
            pill_color = "#9ca3af"
            t = (to or "").lower()
            if "abier" in t: pill_color = "#f59e0b"
            elif "curso" in t: pill_color = "#3b82f6"
            elif "solu" in t: pill_color = "#10b981"
            elif "rech" in t: pill_color = "#ef4444"

            st.markdown(f"""
            <div style='border-left:4px solid #e5e7eb;padding-left:10px;margin:6px 0;'>
                <div style='color:#374151;'>
                    <b>{who}</b> — <span style='color:#6b7280;font-size:0.85rem;'>{f}</span>
                </div>
                <div style='margin-top:3px;'>
                    <span style='opacity:.8;'>Estado:</span> <b>{fr}</b> → 
                    <span style='background:{pill_color};color:#fff;padding:2px 8px;border-radius:999px;font-size:0.82rem;'>{to}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 💬 Conversación")
    comentarios = []
    try:
        comentarios = supabase.table("incidencia_comentario").select("*").eq("incidenciaid", incidenciaid).order("fecha").execute().data or []
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar comentarios: {e}")
    _render_timeline(comentarios)

    st.markdown("---")
    nuevo = st.text_area("✍️ Añadir comentario o nota")
    if st.button("💾 Enviar comentario", use_container_width=True):
        if nuevo.strip():
            _add_comentario(supabase, incidenciaid, nuevo.strip(), st.session_state.get("user_nombre", "Agente"))
            st.success("✅ Comentario añadido.")
            st.rerun()

    st.markdown("---")
    if st.button("⬅️ Volver al listado", use_container_width=True):
        st.session_state["inci_show_modal"] = False
        st.session_state["inci_detalle_id"] = None
        st.rerun()

# ======================================================
# 📈 Vista principal
# ======================================================
def render_incidencia_workflow(supabase):
    st.header("⚠️ Gestión de incidencias")
    st.caption("Workflow completo por cliente/pedido/producto, con conversación, estados y asignación.")

    session = st.session_state
    session.setdefault("inci_view", "Tarjetas")

    trabajadores = load_trabajadores(supabase)
    clientes = load_clientes(supabase)
    estados_map = _load_estados(supabase)

    # Filtros
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        cliente_sel = st.selectbox("Cliente", ["Todos"] + list(clientes.keys()))
    with col2:
        estado_sel = st.selectbox("Estado", ["Todos", "Abierta", "En curso", "Solucionada", "Rechazada"])
    with col3:
        asignado_sel = st.selectbox("Responsable", ["Todos"] + list(trabajadores.keys()))
    with col4:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="inci_view")

    tipo_sel = st.selectbox("Origen", ["Todos", "cliente", "pedido", "producto", "otro"])

    # Query
    incidencias = []
    try:
        base = supabase.table("incidencia").select("*")
        if tipo_sel != "Todos":
            base = base.eq("origen_tipo", tipo_sel)
        if cliente_sel != "Todos":
            base = base.eq("clienteid", clientes[cliente_sel])
        if estado_sel != "Todos":
            eid = estados_map.get(estado_sel)
            if eid:
                base = base.eq("incidencia_estadoid", eid)
            else:
                base = base.eq("estado", estado_sel)
        if asignado_sel != "Todos":
            base = base.eq("responsableid", trabajadores[asignado_sel])
        incidencias = base.order("fecha_creacion", desc=True).limit(300).execute().data or []
    except Exception as e:
        st.error(f"❌ Error cargando incidencias: {e}")
        return

    if not incidencias:
        st.info("📭 No hay incidencias con estos filtros.")
        return

    # KPIs
    def _estado_row(r):
        t = _estado_text_from_id(r.get("incidencia_estadoid"), estados_map)
        return t if t != "-" else (r.get("estado") or "-")

    total = len(incidencias)
    abiertas = sum(1 for r in incidencias if "abier" in _estado_row(r).lower())
    curso = sum(1 for r in incidencias if "curso" in _estado_row(r).lower())
    solu = sum(1 for r in incidencias if "solu" in _estado_row(r).lower())
    rech = sum(1 for r in incidencias if "rech" in _estado_row(r).lower())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔢 Total", total)
    k2.metric("🟠 Abiertas", abiertas)
    k3.metric("🔵 En curso", curso)
    k4.metric("🟢 Solucionadas", solu)
    k5.metric("🔴 Rechazadas", rech)

    st.markdown("---")

    # Render
    if view == "Tarjetas":
        cols = st.columns(2)
        for idx, i in enumerate(incidencias):
            with cols[idx % 2]:
                _render_incidencia_card(i, trabajadores, clientes, estados_map)
    else:
        _render_incidencia_table(incidencias, trabajadores, clientes, estados_map)

    # Modal detalle
    if st.session_state.get("inci_show_modal"):
        render_incidencia_detalle(supabase)


def _load_estado_log(supabase, incidenciaid: int):
    try:
        res = (
            supabase.table("incidencia_estado_log")
            .select("*")
            .eq("incidenciaid", incidenciaid)
            .order("fecha", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []
