# modules/crm/crm_alertas_panel.py

import streamlit as st
import pandas as pd
from datetime import date

from modules.crm.crm_alertas_service import (
    get_alertas_trabajador,
    get_alertas_globales,
)


# ======================================================
# 🔔 PANEL DE ALERTAS DEL COMERCIAL
# ======================================================
def render_alertas_usuario(supa):
    trabajadorid = st.session_state.get("trabajadorid")

    if not trabajadorid:
        st.warning("⚠️ No hay sesión de trabajador activa.")
        return

    # Cargar alertas del comercial
    alertas = get_alertas_trabajador(supa, trabajadorid)

    st.title("🔔 Alertas del día")
    st.caption("Seguimientos, tareas vencidas y próximas actuaciones asignadas.")
    st.divider()

    # Caso sin alertas
    if alertas["total"] == 0:
        st.success("🎉 Todo al día. No tienes alertas pendientes.")
        return

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total alertas", alertas["total"])
    c2.metric("Críticas", len(alertas["criticas"]))
    c3.metric("Hoy", len(alertas["hoy"]))
    c4.metric("Próximos días", len(alertas["proximas"]))
    st.divider()

    # ------------------------------------------
    # 🔥 ALERTAS CRÍTICAS
    # ------------------------------------------
    st.subheader("🔥 Alertas críticas (vencidas / urgentes)")

    if alertas["criticas"]:
        df = _alertas_to_df(alertas["criticas"])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No hay alertas críticas.")

    st.divider()

    # ------------------------------------------
    # 📅 PARA HOY
    # ------------------------------------------
    st.subheader("📅 Actuaciones para hoy")

    if alertas["hoy"]:
        df = _alertas_to_df(alertas["hoy"])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No hay actuaciones para hoy.")

    st.divider()

    # ------------------------------------------
    # 🗓️ PRÓXIMOS DÍAS
    # ------------------------------------------
    st.subheader("🗓️ Próximos días")

    if alertas["proximas"]:
        df = _alertas_to_df(alertas["proximas"])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No hay actuaciones próximas.")

    st.divider()

    # ------------------------------------------
    # 📌 SEGUIMIENTOS
    # ------------------------------------------
    st.subheader("📌 Seguimientos automáticos")

    if alertas["seguimiento"]:
        df = _alertas_to_df(alertas["seguimiento"])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Sin seguimientos pendientes.")


# ======================================================
# 🕵️ PANEL GLOBAL DE SUPERVISIÓN (ADMIN / EDITOR)
# ======================================================
def render_alertas_supervision(supa):
    rol = st.session_state.get("rol_usuario")

    if rol not in ("admin", "editor"):
        st.error("Solo usuarios con rol admin/editor pueden ver este panel.")
        return

    st.title("🕵️ Alertas globales del CRM")
    st.caption("Vistas completas de actuaciones críticas de todo el equipo.")
    st.divider()

    data = get_alertas_globales(supa)

    if data["total"] == 0:
        st.success("🎉 No hay alertas críticas globales.")
        return

    st.metric("Total alertas críticas", data["total"])
    st.divider()

    df = _alertas_global_to_df(data["criticas"])
    st.dataframe(df, width="stretch", hide_index=True)


# ======================================================
# 🔧 HELPERS — Conversión de alertas → tabla
# ======================================================
def _alertas_to_df(lista):
    rows = []

    for a in lista:
        cli = a.get("cliente") or {}

        rows.append({
            "ID": a.get("crm_actuacionid"),
            "Cliente": cli.get("razonsocial") or cli.get("nombre", "—"),
            "Estado": (a.get("crm_actuacion_estado") or {}).get("estado"),
            "Acción": a.get("fecha_accion"),
            "Vencimiento": a.get("fecha_vencimiento"),
            "Título": a.get("titulo") or "—",
            "Seguimiento": "Sí" if a.get("requiere_seguimiento") else "No",
        })

    return pd.DataFrame(rows)


def _alertas_global_to_df(lista):
    rows = []

    for a in lista:
        cli = a.get("cliente") or {}
        trab = a.get("trabajador") or {}

        rows.append({
            "ID": a.get("crm_actuacionid"),
            "Cliente": cli.get("razonsocial") or cli.get("nombre", "—"),
            "Comercial": f"{trab.get('nombre', '')} {trab.get('apellidos', '')}".strip(),
            "Estado": (a.get("crm_actuacion_estado") or {}).get("estado"),
            "Acción": a.get("fecha_accion"),
            "Vencimiento": a.get("fecha_vencimiento"),
            "Seguimiento": "Sí" if a.get("requiere_seguimiento") else "No",
        })

    return pd.DataFrame(rows)
