import streamlit as st
import pandas as pd
from datetime import date, datetime

# ======================================================
# 📈 PROGRESO DE CAMPAÑA — Versión PRO
# ======================================================
def render():
    from modules.campania.campania_nav import render_campania_nav

    supa = st.session_state["supa"]
    campaniaid = st.session_state.get("campaniaid")

    # -------------------------------------
    # NAV
    # -------------------------------------
    render_campania_nav(active_view="progreso", campaniaid=campaniaid)

    st.title("📈 Progreso de campaña")

    if st.button("⬅️ Volver al listado"):
        st.session_state["campania_view"] = "lista"
        st.rerun()

    # -------------------------------------
    # Cargar campaña
    # -------------------------------------
    campania = (
        supa.table("campania")
        .select("nombre, descripcion, fecha_inicio, fecha_fin, estado")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if not campania:
        st.error("Campaña no encontrada.")
        return

    # -------------------------------------
    # Cabecera
    # -------------------------------------
    st.header(f"📣 {campania['nombre']}")
    st.markdown(
        f"🗓️ **{campania['fecha_inicio']} → {campania['fecha_fin']}**"
    )
    st.markdown(_badge_estado(campania["estado"]), unsafe_allow_html=True)
    st.caption(campania.get("descripcion") or "—")

    st.divider()

    # -------------------------------------
    # Actuaciones reales
    # -------------------------------------
    acciones = _fetch_acciones(supa, campaniaid)

    if not acciones:
        st.warning("La campaña aún no tiene actuaciones generadas.")
        return

    df = pd.DataFrame(acciones)

    # =====================================
    # FILTROS
    # =====================================
    st.subheader("🔍 Filtros")

    f1, f2, f3, f4 = st.columns([3, 3, 3, 1])

    with f1:
        estado_sel = st.selectbox("Estado", ["Todos"] + sorted(df["estado"].unique()))

    with f2:
        comercial_sel = st.selectbox("Comercial", ["Todos"] + sorted(df["trabajador"].unique()))

    with f3:
        cliente_sel = st.selectbox("Cliente", ["Todos"] + sorted(df["cliente"].unique()))

    with f4:
        st.write("")
        st.write("")
        if st.button("🔄 Reset"):
            st.rerun()

    df_view = df.copy()

    if estado_sel != "Todos":
        df_view = df_view[df_view["estado"] == estado_sel]

    if comercial_sel != "Todos":
        df_view = df_view[df_view["trabajador"] == comercial_sel]

    if cliente_sel != "Todos":
        df_view = df_view[df_view["cliente"] == cliente_sel]

    # =====================================
    # MÉTRICAS
    # =====================================
    st.subheader("📊 Métricas generales")

    total = len(df)
    comp = (df["estado"] == "Completada").sum()
    pend = (df["estado"] == "Pendiente").sum()
    canc = (df["estado"] == "Cancelada").sum()

    pct = round(comp / total * 100, 1) if total else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", total)
    m2.metric("Completadas", comp)
    m3.metric("Pendientes", pend)
    m4.metric("Canceladas", canc)
    m5.metric("Avance", f"{pct}%")

    st.progress(pct / 100 if total else 0)
    st.divider()

    # =====================================
    # TABLA
    # =====================================
    st.subheader("📋 Actuaciones filtradas")

    st.dataframe(
        df_view,
        width="stretch",
        hide_index=True,
    )
    st.caption(f"{len(df_view)} de {total} actuaciones mostradas")

    st.divider()

    # ======================================================
    # 🛠 ACCIONES MASIVAS
    # ======================================================
    st.subheader("🛠 Acciones masivas")

    ids = df_view["crm_actuacionid"].tolist()

    seleccion = st.multiselect("Selecciona actuaciones:", ids)

    if not seleccion:
        st.info("Selecciona actuaciones para modificar.")
        return

    st.success(f"{len(seleccion)} actuaciones seleccionadas.")

    ac1, ac2 = st.columns(2)

    # --------- ESTADOS -------
    with ac1:
        if st.button("✔ Marcar como completadas"):
            _bulk_update_estado(supa, seleccion, "Completada")
            st.rerun()

        if st.button("❌ Cancelar seleccionadas"):
            _bulk_update_estado(supa, seleccion, "Cancelada")
            st.rerun()

    # --------- REASIGNACIÓN -------
    with ac2:
        trabajadores = st.session_state.get("all_trabajadores", [])
        mapa_trab = {
            f"{t['nombre']} {t['apellidos']}": t["trabajadorid"]
            for t in trabajadores
        }

        nuevo = st.selectbox("Reasignar a:", ["—"] + list(mapa_trab.keys()))

        if nuevo != "—" and st.button("🔄 Reasignar"):
            _bulk_update_comercial(supa, seleccion, mapa_trab[nuevo])
            st.rerun()

    st.divider()

    # --------- FECHA -------
    st.subheader("📅 Reprogramar fecha (mantiene hora actual)")

    colf1, colf2 = st.columns([3, 1])

    with colf1:
        nueva_fecha = st.date_input("Nueva fecha:", date.today())

    with colf2:
        if st.button("Aplicar fecha"):
            _bulk_update_fecha(supa, seleccion, nueva_fecha)
            st.rerun()

    st.divider()

    # --------- RESULTADO -------
    st.subheader("📝 Añadir resultado")

    texto = st.text_input("Resultado:", "")

    if texto and st.button("Guardar resultado"):
        _bulk_update_resultado(supa, seleccion, texto)
        st.rerun()


# ======================================================
# 🔧 HELPERS
# ======================================================
def _fetch_acciones(supa, campaniaid: int):
    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid")
        .eq("campaniaid", campaniaid)
        .execute()
        .data
    )

    if not rel:
        return []

    ids = [r["actuacionid"] for r in rel]

    q = (
        supa.table("crm_actuacion")
        .select("""
            crm_actuacionid,
            crm_actuacion_estadoid,
            fecha_accion,
            resultado,
            cliente (clienteid, razonsocial, nombre),
            crm_actuacion_estado (estado),
            trabajador_creadorid,
            trabajador!crm_actuacion_trabajador_creadorid_fkey (trabajadorid, nombre, apellidos)
        """)
        .in_("crm_actuacionid", ids)
        .order("fecha_accion")
        .execute()
        .data
    )

    rows = []
    for a in q:
        trabajador_nombre = "—"
        if a.get("trabajador"):
            trabajador_nombre = f"{a['trabajador']['nombre']} {a['trabajador']['apellidos']}"

        rows.append({
            "crm_actuacionid": a["crm_actuacionid"],
            "estado": (a.get("crm_actuacion_estado") or {}).get("estado", ""),
            "fecha_accion": a["fecha_accion"],
            "resultado": a["resultado"],
            "cliente": (a["cliente"]["razonsocial"] if a["cliente"] else "—"),
            "trabajador": trabajador_nombre,
        })

    return rows


# MASS UPDATES
def _estado_id(supa, nombre: str):
    cache = st.session_state.get("_crm_estado_map")
    if cache is None:
        rows = supa.table("crm_actuacion_estado").select("crm_actuacion_estadoid, estado").execute().data or []
        cache = {r["estado"]: r["crm_actuacion_estadoid"] for r in rows}
        st.session_state["_crm_estado_map"] = cache
    return cache.get(nombre)


def _bulk_update_estado(supa, ids, estado):
    estado_id = _estado_id(supa, estado)
    if not estado_id:
        return
    supa.table("crm_actuacion").update({"crm_actuacion_estadoid": estado_id}).in_("crm_actuacionid", ids).execute()


def _bulk_update_comercial(supa, ids, trabajadorid):
    supa.table("crm_actuacion").update({"trabajador_creadorid": trabajadorid}).in_("crm_actuacionid", ids).execute()


def _bulk_update_fecha(supa, ids, nueva_fecha):
    # Mantener hora original
    for actid in ids:
        act = (
            supa.table("crm_actuacion")
            .select("fecha_accion")
            .eq("crm_actuacionid", actid)
            .single()
            .execute()
            .data
        )
        if act:
            hora = datetime.fromisoformat(act["fecha_accion"]).time()
            nueva = datetime.combine(nueva_fecha, hora).isoformat()
            supa.table("crm_actuacion").update({"fecha_accion": nueva}).eq("crm_actuacionid", actid).execute()


def _bulk_update_resultado(supa, ids, texto):
    supa.table("crm_actuacion").update({"resultado": texto}).in_("crm_actuacionid", ids).execute()


# BADGE
def _badge_estado(estado):
    colores = {
        "borrador": ("🟡", "#facc15"),
        "activa": ("🟢", "#22c55e"),
        "pausada": ("🟠", "#f97316"),
        "finalizada": ("🔵", "#3b82f6"),
        "cancelada": ("🔴", "#ef4444"),
    }
    icon, color = colores.get(estado, ("⚪", "#ccc"))

    return f"""
    <div style="
        padding:6px 12px;
        background:{color}25;
        border:1px solid {color};
        border-radius:8px;
        display:inline-block;
        font-weight:600;">
        {icon} {estado.capitalize()}
    </div>
    """
