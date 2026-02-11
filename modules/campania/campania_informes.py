import streamlit as st
import pandas as pd


# ======================================================
# 📊 INFORMES DE CAMPAÑA (VERSIÓN PRO)
# ======================================================
def render(supa, campaniaid):
    from modules.campania.campania_nav import render_campania_nav

    # Navegación superior
    render_campania_nav(active_view="informes", campaniaid=campaniaid)

    st.title("📊 Informes de campaña")

    # Botón volver
    if st.button("⬅️ Volver al listado"):
        st.session_state["campania_view"] = "lista"
        st.rerun()

    # --------------------------------------------------
    # Información básica de la campaña
    # --------------------------------------------------
    campania = (
        supa.table("campania")
        .select("nombre, fecha_inicio, fecha_fin, tipo_accion, estado")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if not campania:
        st.error("❌ No se pudo cargar información de la campaña.")
        return

    st.markdown(f"### 📣 {campania['nombre']}")
    st.caption(
        f"🗓️ {campania['fecha_inicio']} → {campania['fecha_fin']} · Estado: `{campania['estado']}`"
    )
    st.divider()

    # --------------------------------------------------
    # Cargar actuaciones reales
    # --------------------------------------------------
    acciones = _fetch_actuaciones_campania(supa, campaniaid)

    if not acciones:
        st.warning("La campaña aún no tiene actuaciones generadas.")
        return

    df = pd.DataFrame(acciones)

    # ======================================================
    # 📌 RESUMEN GENERAL (KPIs)
    # ======================================================
    st.header("📌 Resumen general")

    total = len(df)
    completadas = (df["estado"] == "Completada").sum()
    pendientes = (df["estado"] == "Pendiente").sum()
    canceladas = (df["estado"] == "Cancelada").sum()

    avance_pct = round(completadas / total * 100, 1) if total else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total", total)
    k2.metric("Completadas", completadas)
    k3.metric("Pendientes", pendientes)
    k4.metric("Canceladas", canceladas)
    k5.metric("Avance", f"{avance_pct}%")

    st.progress(avance_pct / 100 if total else 0)
    st.divider()

    # ======================================================
    # 👤 RENDIMIENTO POR COMERCIAL
    # ======================================================
    st.subheader("👤 Rendimiento por comercial")

    df_trab = (
        df.groupby("trabajadorid")
        .agg(
            nombre=("trabajador_nombre", "first"),
            apellidos=("trabajador_apellidos", "first"),
            total=("crm_actuacionid", "count"),
            completadas=("estado", lambda x: (x == "Completada").sum()),
            pendientes=("estado", lambda x: (x == "Pendiente").sum()),
        )
        .reset_index()
    )

    df_trab["avance"] = (df_trab["completadas"] / df_trab["total"] * 100).round(1)

    st.dataframe(
        df_trab[["nombre", "apellidos", "total", "completadas", "pendientes", "avance"]],
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "📥 Exportar CSV (Comerciales)",
        df_trab.to_csv(index=False).encode(),
        "campania_por_comercial.csv",
        "text/csv",
    )

    st.bar_chart(df_trab.set_index("nombre")["avance"])
    st.divider()

    # ======================================================
    # 🏢 RENDIMIENTO POR CLIENTE
    # ======================================================
    st.subheader("🏢 Rendimiento por cliente")

    df_cli = (
        df.groupby("clienteid")
        .agg(
            cliente=("cliente_razon_social", "first"),
            total=("crm_actuacionid", "count"),
            completadas=("estado", lambda x: (x == "Completada").sum()),
            pendientes=("estado", lambda x: (x == "Pendiente").sum()),
        )
        .reset_index()
    )

    df_cli["avance"] = (df_cli["completadas"] / df_cli["total"] * 100).round(1)

    st.dataframe(
        df_cli[["cliente", "total", "completadas", "pendientes", "avance"]],
        hide_index=True,
        width="stretch",
    )

    st.download_button(
        "📥 Exportar CSV (Clientes)",
        df_cli.to_csv(index=False).encode(),
        "campania_por_cliente.csv",
        "text/csv",
    )

    st.divider()

    # ======================================================
    # 📅 EVOLUCIÓN TEMPORAL
    # ======================================================
    st.subheader("📅 Evolución temporal")

    df["fecha_accion"] = pd.to_datetime(df["fecha_accion"]).dt.date

    df_fecha = (
        df.groupby("fecha_accion")
        .agg(
            total=("crm_actuacionid", "count"),
            completadas=("estado", lambda x: (x == "Completada").sum()),
        )
        .reset_index()
    )

    st.line_chart(df_fecha.set_index("fecha_accion")[["total", "completadas"]])
    st.divider()

    # ======================================================
    # 🧪 EMBUDO (Funnel)
    # ======================================================
    st.subheader("🧪 Embudo de conversión")

    funnel = pd.DataFrame({
        "Etapa": ["Generadas", "Pendientes", "Completadas"],
        "Valor": [total, pendientes, completadas],
    }).set_index("Etapa")

    st.bar_chart(funnel)

    st.caption(
        "Interpretación del embudo:\n"
        "- **Generadas** → Total de actuaciones creadas\n"
        "- **Pendientes** → Acciones aún no atendidas\n"
        "- **Completadas** → Acciones finalizadas correctamente"
    )

    st.divider()

    # ======================================================
    # 📚 ACTUACIONES POR GRUPO
    # ======================================================
    st.subheader("📚 Actuaciones por grupo de cliente")

    df_grupo = _fetch_por_grupo(supa, campaniaid)

    st.dataframe(
        df_grupo.sort_values("total", ascending=False),
        hide_index=True,
        width="stretch",
    )

    st.download_button(
        "📥 Exportar CSV (Grupos)",
        df_grupo.to_csv(index=False).encode(),
        "campania_por_grupo.csv",
        "text/csv",
    )

    st.divider()

    # ======================================================
    # 📦 EXPORTACIÓN COMPLETA
    # ======================================================
    st.subheader("📦 Exportación completa")

    st.download_button(
        "📥 Exportar dataset completo (CSV)",
        df.to_csv(index=False).encode(),
        "campania_completa.csv",
        "text/csv",
    )


# ======================================================
# 🔧 HELPERS
# ======================================================
def _fetch_actuaciones_campania(supa, campaniaid: int):
    """Carga actuaciones vinculadas a la campaña."""
    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid")
        .eq("campaniaid", campaniaid)
        .execute()
    ).data or []

    if not rel:
        return []

    act_ids = [r["actuacionid"] for r in rel]

    raw = (
        supa.table("crm_actuacion")
        .select("""
            crm_actuacionid,
            clienteid,
            trabajador_creadorid,
            crm_actuacion_estadoid,
            fecha_accion,
            resultado,
            crm_actuacion_estado (estado),
            cliente (clienteid, razonsocial, nombre),
            trabajador!crm_actuacion_trabajador_creadorid_fkey (trabajadorid, nombre, apellidos)
        """)
        .in_("crm_actuacionid", act_ids)
        .execute()
    ).data or []

    rows = []
    for a in raw:
        cliente = a.get("cliente") or {}
        trabajador = a.get("trabajador") or {}
        rows.append({
            "crm_actuacionid": a["crm_actuacionid"],
            "clienteid": a["clienteid"],
            "cliente_razon_social": cliente.get("razonsocial") or cliente.get("nombre", ""),
            "trabajadorid": a.get("trabajador_creadorid"),
            "trabajador_nombre": trabajador.get("nombre", ""),
            "trabajador_apellidos": trabajador.get("apellidos", ""),
            "estado": (a.get("crm_actuacion_estado") or {}).get("estado", ""),
            "fecha_accion": a["fecha_accion"],
            "resultado": a.get("resultado"),
        })

    return sorted(rows, key=lambda x: x["fecha_accion"])


def _fetch_por_grupo(supa, campaniaid: int):
    """Totales de actuaciones agrupadas por grupo de cliente (grupoid)."""

    sql = f"""
        SELECT 
            COALESCE(g.grupo_nombre, 'Sin grupo') AS grupo,
            COUNT(a.crm_actuacionid) AS total
        FROM crm_actuacion a
        JOIN cliente c ON c.clienteid = a.clienteid
        JOIN campania_actuacion ca ON ca.actuacionid = a.crm_actuacionid
        LEFT JOIN grupo g ON g.idgrupo = c.idgrupo
        WHERE ca.campaniaid = {campaniaid}
        GROUP BY g.grupo_nombre
        ORDER BY total DESC;
    """

    try:
        res = supa.rpc("execute_sql", {"query": sql}).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"⚠️ Error cargando datos por grupo: {e}")
        return pd.DataFrame([])
