import streamlit as st
import pandas as pd
from datetime import datetime

from modules.crm.actuacion_workflow import render_llamada_workflow
from modules.campania.campania_nav import render_campania_nav


# ======================================================
# 🔎 DETALLE DE CAMPAÑA — Versión PRO
# ======================================================
def render(campaniaid: int):
    supa = st.session_state["supa"]

    # =============================================
    # ¿Hay una llamada abierta?
    # =============================================
    llamada_id = st.session_state.get("campania_llamada_abierta")

    render_campania_nav(active_view="detalle", campaniaid=campaniaid)

    if llamada_id:
        st.title("📞 Llamada CRM")

        if st.button("⬅️ Volver a la campaña", use_container_width=True):
            st.session_state["campania_llamada_abierta"] = None
            st.rerun()

        render_llamada_workflow(supa, llamada_id)
        return

    # =============================================
    # Datos de campaña
    # =============================================
    campania = (
        supa.table("campania")
        .select("*")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if not campania:
        st.error("No se encontró la campaña.")
        return

    # ---------------------------------------------
    # CABECERA
    # ---------------------------------------------
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.title(f"📣 {campania['nombre']}")
        if campania.get("descripcion"):
            st.caption(campania["descripcion"])

    with col_right:
        st.markdown(_badge_estado(campania["estado"]), unsafe_allow_html=True)

    st.divider()

    # =============================================
    # ACCIONES RÁPIDAS
    # =============================================
    st.subheader("⚙️ Acciones rápidas")

    cA, cB, cC, cD, cE = st.columns(5)

    # EDITAR
    with cA:
        if st.button("✏️ Editar"):
            st.session_state["campaniaid"] = campaniaid
            st.session_state["campania_step"] = 1
            st.session_state["campania_view"] = "form"
            st.rerun()

    # CANCELAR
    with cB:
        if campania["estado"] == "activa":
            if st.button("🚫 Cancelar"):
                supa.table("campania").update({"estado": "cancelada"}).eq("campaniaid", campaniaid).execute()
                st.rerun()

    # REABRIR
    with cC:
        if campania["estado"] == "cancelada":
            if st.button("🔁 Reabrir"):
                supa.table("campania").update({"estado": "activa"}).eq("campaniaid", campaniaid).execute()
                st.rerun()

    # FINALIZAR
    with cD:
        if campania["estado"] == "activa":
            if st.button("✔ Finalizar"):
                supa.table("campania").update({"estado": "finalizada"}).eq("campaniaid", campaniaid).execute()
                st.rerun()

    # ELIMINAR (modal seguro)
    with cE:
        if campania["estado"] in ["borrador", "cancelada"]:
            if st.button("🗑 Eliminar"):
                st.session_state["confirmar_delete_campania"] = campaniaid

    # Modal de confirmación
    if st.session_state.get("confirmar_delete_campania") == campaniaid:
        st.error("⚠ ¿Seguro que quieres eliminar esta campaña? Esta acción es irreversible.")
        colX, colY = st.columns(2)

        with colX:
            if st.button("❗ Confirmar eliminación definitiva"):
                supa.table("campania").delete().eq("campaniaid", campaniaid).execute()
                supa.table("campania_cliente").delete().eq("campaniaid", campaniaid).execute()
                supa.table("campania_actuacion").delete().eq("campaniaid", campaniaid).execute()
                st.session_state["campania_view"] = "lista"
                st.session_state["campaniaid"] = None
                st.session_state["confirmar_delete_campania"] = None
                st.rerun()

        with colY:
            if st.button("Cancelar"):
                st.session_state["confirmar_delete_campania"] = None
                st.rerun()

    st.divider()

    # =============================================
    # OBTENER ACTUACIONES
    # =============================================
    acciones = _fetch_actuaciones_campania(supa, campaniaid)
    df = pd.DataFrame(acciones)

    if df.empty:
        st.warning("Esta campaña aún no tiene actuaciones generadas.")
        return

    df["fecha_accion"] = pd.to_datetime(df["fecha_accion"])

    # =============================================
    # KPIs
    # =============================================
    st.subheader("📊 KPIs generales")

    total = len(df)
    completas = (df["estado"] == "Completada").sum()
    pendientes = (df["estado"] == "Pendiente").sum()
    canceladas = (df["estado"] == "Cancelada").sum()
    progreso = completas / total if total else 0

    dur_media = (
        round(df["duracion_segundos"].dropna().mean() / 60, 1)
        if df["duracion_segundos"].notna().any()
        else None
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total", total)
    k2.metric("Completadas", completas)
    k3.metric("Pendientes", pendientes)
    k4.metric("Canceladas", canceladas)
    k5.metric("Duración media (min)", dur_media or "—")

    st.progress(progreso)
    st.divider()

    # =============================================
    # TABS
    # =============================================
    t1, t2, t3 = st.tabs(["👤 Por comercial", "🏢 Por cliente", "🕒 Timeline"])

    # -----------------------------------------------------
    # TAB 1 — POR COMERCIAL
    # -----------------------------------------------------
    with t1:
        st.subheader("👤 Actividad por comercial")

        df_trab = (
            df.groupby("trabajadorid")
            .agg(
                nombre=("trabajador_nombre", "first"),
                total=("crm_actuacionid", "count"),
                completadas=("estado", lambda x: (x == "Completada").sum()),
                pendientes=("estado", lambda x: (x == "Pendiente").sum()),
                canceladas=("estado", lambda x: (x == "Cancelada").sum()),
            )
            .reset_index()
        )

        st.dataframe(df_trab, hide_index=True, use_container_width=True)

        df_trab["avance"] = (df_trab["completadas"] / df_trab["total"] * 100).round(1)

        st.bar_chart(df_trab.set_index("nombre")["avance"])

    # -----------------------------------------------------
    # TAB 2 — POR CLIENTE
    # -----------------------------------------------------
    with t2:
        st.subheader("🏢 Actividad por cliente")

        df_cli = (
            df.groupby("clienteid")
            .agg(
                cliente=("cliente_razon_social", "first"),
                total=("crm_actuacionid", "count"),
                completadas=("estado", lambda x: (x == "Completada").sum()),
                pendientes=("estado", lambda x: (x == "Pendiente").sum()),
                canceladas=("estado", lambda x: (x == "Cancelada").sum()),
            )
            .reset_index()
        )

        st.dataframe(df_cli, hide_index=True, use_container_width=True)

        # Abrir llamada
        st.markdown("### 📞 Abrir llamada")
        act_sel = st.selectbox("Selecciona actuación:", df["crm_actuacionid"])

        if st.button("📞 Abrir llamada seleccionada"):
            st.session_state["campania_llamada_abierta"] = act_sel
            st.rerun()

    # -----------------------------------------------------
    # TAB 3 — TIMELINE
    # -----------------------------------------------------
    with t3:
        st.subheader("🕒 Timeline de actuaciones")

        df_ordenado = df.sort_values("fecha_accion")

        for _, a in df_ordenado.iterrows():
            st.markdown(
                f"""
                **{a['fecha_accion'].strftime('%d/%m/%Y %H:%M')}** — {a['cliente_razon_social']}  
                Estado: **{a['estado']}**  
                Resultado: {a['resultado'] or '—'}  
                """
            )

            if st.button(f"📞 Abrir llamada #{a['crm_actuacionid']}", key=f"tl_{a['crm_actuacionid']}"):
                st.session_state["campania_llamada_abierta"] = a["crm_actuacionid"]
                st.rerun()


# ======================================================
# HELPERS
# ======================================================
def _fetch_actuaciones_campania(supa, campaniaid):
    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid, clienteid")
        .eq("campaniaid", campaniaid)
        .execute()
        .data or []
    )

    if not rel:
        return []

    act_ids = [r["actuacionid"] for r in rel]

    data = (
        supa.table("crm_actuacion")
        .select(
            """
            crm_actuacionid,
            clienteid,
            trabajador_creadorid,


            fecha_accion,
            resultado,
            duracion_segundos,
            crm_actuacion_estado (estado),
            cliente (clienteid, razonsocial, nombre),
            trabajador!crm_actuacion_trabajador_creadorid_fkey (trabajadorid, nombre, apellidos)
            """
        )
        .in_("crm_actuacionid", act_ids)
        .execute()
        .data or []
    )

    rows = []
    for a in data:
        rows.append(
            {
                "crm_actuacionid": a["crm_actuacionid"],
                "clienteid": a["clienteid"],
                "cliente_razon_social": (a.get("cliente") or {}).get("razonsocial") or (a.get("cliente") or {}).get("nombre", ""),
                "trabajadorid": a.get("trabajador_creadorid"),
                "trabajador_nombre": (a.get("trabajador") or {}).get("nombre", ""),
                "trabajador_apellidos": (a.get("trabajador") or {}).get("apellidos", ""),
                "estado": (a.get("crm_actuacion_estado") or {}).get("estado"),

                "fecha_accion": a["fecha_accion"],
                "resultado": a.get("resultado"),
                "duracion_segundos": a.get("duracion_segundos"),
            }
        )

    return rows


def _badge_estado(estado: str):
    colores = {
        "borrador": ("🟡", "#facc15"),
        "activa": ("🟢", "#22c55e"),
        "finalizada": ("🔵", "#3b82f6"),
        "cancelada": ("🔴", "#ef4444"),
    }
    icon, color = colores.get(estado, ("⚪", "#999999"))

    return f"""
    <div style="
        padding:6px 12px;
        background:{color}15;
        border:1px solid {color};
        border-radius:8px;
        display:inline-block;
        font-weight:600;">
        {icon} {estado.capitalize()}
    </div>
    """
