import streamlit as st
import pandas as pd
from datetime import date
from modules.campania.campania_nav import render_campania_nav
from modules.crm.crm_alertas_service import (
    get_alertas_trabajador,
    get_alertas_globales,
)


# ======================================================
# 🕵️ PANEL DE SUPERVISIÓN GLOBAL (ADMIN / EDITOR)
# ======================================================
def render_supervision(supa):
    campaniaid = st.session_state.get("campaniaid")
    render_campania_nav(active_view="supervision", campaniaid=campaniaid)

    st.title("🕵️ Panel de supervisión global")
    st.caption("Control avanzado de campañas, estado comercial y alertas del CRM.")
    st.divider()

    trabajadorid = st.session_state.get("trabajadorid")
    estado_pendiente_id = _estado_id(supa, "Pendiente")

    # ======================================================
    # 0) RESUMEN GLOBAL + USUARIO ACTIVO (nombre o email)
    # ======================================================
    st.subheader("🔔 Resumen global del sistema")

    # Obtener nombre o email
    user_nombre = st.session_state.get("user_nombre")
    user_email = st.session_state.get("user_email")

    if user_nombre:
        usuario_activo = user_nombre
    else:
        usuario_activo = user_email or "—"

    try:
        resumen_global = get_alertas_globales(supa)
        total_criticas = resumen_global.get("total", 0)
    except Exception:
        resumen_global = {"total": 0, "criticas": []}
        total_criticas = 0

    c1, c2 = st.columns(2)
    c1.metric("🚨 Alertas críticas (globales)", total_criticas)
    c2.metric("👤 Usuario activo", usuario_activo)

    st.divider()

    # ======================================================
    # 1) ESTADO GENERAL DE CAMPAÑAS
    # ======================================================
    st.subheader("📊 Estado general de campañas")

    try:
        camp = (
            supa.table("campania")
            .select("*")
            .order("fecha_inicio", desc=True)
            .execute()
            .data or []
        )
    except Exception:
        camp = []

    if not camp:
        st.info("No hay campañas creadas.")
        return

    df = pd.DataFrame(camp)

    total = len(df)
    activas = (df["estado"] == "activa").sum()

    riesgo = 0
    for c in camp:
        fin = c.get("fecha_fin")
        if fin:
            try:
                dias = (date.fromisoformat(str(fin)) - date.today()).days
                if dias <= 2:
                    riesgo += 1
            except Exception:
                pass

    c1, c2, c3 = st.columns(3)
    c1.metric("Activas", activas)
    c2.metric("Total campañas", total)
    c3.metric("En riesgo alto", riesgo)

    st.divider()

    # ======================================================
    # 2) ACTIVIDAD DE COMERCIALES (sin ranking)
    # ======================================================
    st.subheader("🧑‍💼 Actividad de comerciales")

    try:
        acts = (
            supa.table("crm_actuacion")
            .select("""
                crm_actuacionid,
                trabajador_creadorid,
                crm_actuacion_estado (estado),
                duracion_segundos,
                trabajador!crm_actuacion_trabajador_creadorid_fkey (trabajadorid, nombre, apellidos)
            """)
            .execute()
            .data or []
        )
    except Exception:
        acts = []

    if not acts:
        st.info("No hay actuaciones registradas.")
    else:
        rows = []
        for a in acts:
            t = a.get("trabajador") or {}
            if not t:
                continue

            rows.append({
                "trabajadorid": t.get("trabajadorid"),
                "nombre": f"{t.get('nombre','')} {t.get('apellidos','')}".strip(),
                "estado": (a.get("crm_actuacion_estado") or {}).get("estado", "—"),
                "duracion_segundos": a.get("duracion_segundos") or 0,
            })

        df_a = pd.DataFrame(rows)

        actividad = (
            df_a.groupby(["trabajadorid", "nombre"])
            .agg(
                completadas=("estado", lambda x: (x == "Completada").sum()),
                pendientes=("estado", lambda x: (x == "Pendiente").sum()),
                minutos=("duracion_segundos", lambda x: (x.sum() // 60)),
            )
            .reset_index()
        )

        st.dataframe(
            actividad[["nombre", "completadas", "pendientes", "minutos"]],
            hide_index=True,
            use_container_width=True,
        )

    st.divider()

    # ======================================================
    # 3) ALERTAS PERSONALES DEL COMERCIAL
    # ======================================================
    st.subheader("🔥 Alertas personales del comercial")

    try:
        alertas_personales = get_alertas_trabajador(supa, trabajadorid)
    except Exception:
        alertas_personales = {
            "total": 0,
            "criticas": [],
            "hoy": [],
            "proximas": [],
            "seguimiento": [],
        }

    total_personales = alertas_personales.get("total", 0)

    if total_personales == 0:
        st.success("No hay alertas activas para este comercial 🎉")
    else:
        bloques = [
            ("🔴 Críticas", alertas_personales.get("criticas", []), "#ef4444"),
            ("🟠 Hoy", alertas_personales.get("hoy", []), "#f59e0b"),
            ("🟡 Próximas", alertas_personales.get("proximas", []), "#facc15"),
            ("🔁 Seguimiento", alertas_personales.get("seguimiento", []), "#3b82f6"),
        ]

        for titulo, lista, color in bloques:
            if not lista:
                continue

            st.markdown(f"### {titulo}")
            for a in lista:
                cli = (a.get("cliente") or {}).get("razonsocial") or (a.get("cliente") or {}).get("nombre", "—")
                venc = a.get("fecha_vencimiento", "—")

                st.markdown(
                    f"""
                    <div style="
                        padding:12px;
                        border-left:5px solid {color};
                        background:{color}15;
                        border-radius:8px;
                        margin-bottom:8px;
                    ">
                        <b>{cli}</b><br>
                        Vencimiento: {venc}<br>
                        Estado: {(a.get("crm_actuacion_estado") or {}).get("estado", "—")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    # ======================================================
    # 4) ACTUACIONES VENCIDAS (GLOBAL)
    # ======================================================
    st.subheader("🚨 Actuaciones vencidas (global)")

    try:
        vencidas = (
            supa.table("crm_actuacion")
            .select("""
                crm_actuacionid,
                clienteid,
                fecha_vencimiento,
                crm_actuacion_estado (estado),
                cliente (razonsocial, nombre)
            """)
            .lt("fecha_vencimiento", date.today().isoformat())
            .eq("crm_actuacion_estadoid", estado_pendiente_id)
            .execute()
            .data or []
        )
    except Exception:
        vencidas = []

    if not vencidas:
        st.success("No hay actuaciones vencidas 🎉")
    else:
        st.error(f"Hay {len(vencidas)} actuaciones vencidas")

        rows = []
        for v in vencidas:
            rows.append({
                "ID": v.get("crm_actuacionid"),
                "Cliente": (v.get("cliente") or {}).get("razonsocial")
                or (v.get("cliente") or {}).get("nombre", "—"),
                "Vencimiento": v.get("fecha_vencimiento", "—"),
                "Estado": (v.get("crm_actuacion_estado") or {}).get("estado", "—"),
            })

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _estado_id(supa, nombre: str):
    cache = st.session_state.get("_crm_estado_map")
    if cache is None:
        rows = supa.table("crm_actuacion_estado").select("crm_actuacion_estadoid, estado").execute().data or []
        cache = {r["estado"]: r["crm_actuacion_estadoid"] for r in rows}
        st.session_state["_crm_estado_map"] = cache
    return cache.get(nombre)
