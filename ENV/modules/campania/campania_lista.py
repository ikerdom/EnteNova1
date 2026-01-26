import streamlit as st
from datetime import date
import pandas as pd

from modules.campania.campania_nav import render_campania_nav


# ======================================================
# 📋 LISTADO PRINCIPAL DE CAMPAÑAS (Versión profesional)
# ======================================================
def render(supa):

    # ==========================
    # NAV SUPERIOR
    # ==========================
    campaniaid = st.session_state.get("campaniaid")
    render_campania_nav(active_view="lista", campaniaid=campaniaid)

    st.title("📣 Campañas comerciales")
    st.caption("Gestiona campañas, consulta su avance y accede a informes.")
    st.divider()

    # ======================================================
    # ➕ BOTÓN CREAR NUEVA CAMPAÑA
    # ======================================================
    if st.button("➕ Crear nueva campaña", use_container_width=True):
        st.session_state["campaniaid"] = None
        st.session_state["campania_step"] = 1
        st.session_state["campania_view"] = "form"
        st.rerun()

    # ======================================================
    # 🎛️ FILTROS AVANZADOS
    # ======================================================
    with st.expander("🎛️ Filtros avanzados", expanded=False):

        # --- Estado & Tipo ---
        c1, c2 = st.columns(2)

        with c1:
            estados = ["Todos", "borrador", "activa", "pausada", "finalizada", "cancelada"]
            estado_sel = st.selectbox("Estado", estados)

        with c2:
            tipos = ["Todos", "llamada", "email", "whatsapp", "visita"]
            tipo_sel = st.selectbox("Tipo de acción principal", tipos)

        # --- Texto ---
        nombre_busqueda = st.text_input("Buscar por nombre o descripción")

        # --- Fechas ---
        c3, c4 = st.columns(2)

        with c3:
            usar_fecha_min = st.checkbox("Filtrar por fecha de inicio mínima")
            fecha_min = (
                st.date_input("Fecha inicio mínima", value=date.today())
                if usar_fecha_min else None
            )

        with c4:
            usar_fecha_max = st.checkbox("Filtrar por fecha fin máxima")
            fecha_max = (
                st.date_input("Fecha fin máxima", value=date.today())
                if usar_fecha_max else None
            )

        # --- Reset ---
        if st.button("🔄 Limpiar filtros"):
            for key in list(st.session_state.keys()):
                if key.startswith("estado") or key.startswith("tipo") or key in (
                    "nombre_busqueda", "usar_fecha_min", "usar_fecha_max"
                ):
                    st.session_state.pop(key, None)
            st.rerun()

    # ======================================================
    # 🔄 CARGA DE CAMPAÑAS DESDE SUPABASE
    # ======================================================
    try:
        resp = (
            supa.table("campania")
            .select("*")
            .order("fecha_inicio", desc=True)
            .execute()
        )
        campanias = resp.data or []
    except Exception as e:
        st.error(f"❌ Error cargando campañas: {e}")
        return

    # ======================================================
    # 🧹 FILTROS APLICADOS
    # ======================================================
    def aplicar_filtros(c):

        # Estado
        if estado_sel != "Todos" and c.get("estado") != estado_sel:
            return False

        # Tipo acción
        if tipo_sel != "Todos" and c.get("tipo_accion") != tipo_sel:
            return False

        # Búsqueda por texto
        if nombre_busqueda:
            texto = f"{c.get('nombre','')} {c.get('descripcion','')}".lower()
            if nombre_busqueda.lower() not in texto:
                return False

        # Fecha inicio mínima
        if fecha_min and c.get("fecha_inicio"):
            try:
                if c["fecha_inicio"] < fecha_min.isoformat():
                    return False
            except Exception:
                pass

        # Fecha fin máxima
        if fecha_max and c.get("fecha_fin"):
            try:
                if c["fecha_fin"] > fecha_max.isoformat():
                    return False
            except Exception:
                pass

        return True

    campanias = [c for c in campanias if aplicar_filtros(c)]

    if not campanias:
        st.info("📭 No hay campañas que coincidan con los filtros seleccionados.")
        return

    # ======================================================
    # 🔔 PANEL GLOBAL DE RIESGO
    # ======================================================
    alertas_global = {"criticas": 0, "altas": 0, "medias": 0}

    for c in campanias:
        fecha_fin = c.get("fecha_fin")
        if not fecha_fin:
            continue
        try:
            dias = (date.fromisoformat(fecha_fin) - date.today()).days
        except:
            continue

        if dias < 0:
            alertas_global["criticas"] += 1
        elif dias <= 2:
            alertas_global["altas"] += 1
        elif dias <= 5:
            alertas_global["medias"] += 1

    if any(alertas_global.values()):
        st.subheader("🔔 Alertas importantes")

        if alertas_global["criticas"]:
            st.error(f"⚠️ {alertas_global['criticas']} campaña(s) en situación crítica.")
        if alertas_global["altas"]:
            st.warning(f"⚠️ {alertas_global['altas']} campaña(s) en riesgo alto.")
        if alertas_global["medias"]:
            st.info(f"ℹ️ {alertas_global['medias']} campaña(s) en riesgo medio.")

        st.divider()

    # ======================================================
    # ESTADOS
    # ======================================================
    BADGE = {
        "borrador": "🟡 Borrador",
        "activa": "🟢 Activa",
        "pausada": "⏸️ Pausada",
        "finalizada": "🔵 Finalizada",
        "cancelada": "🔴 Cancelada",
    }

    st.subheader("📋 Listado de campañas")
    st.write("")

    # ======================================================
    # 🧱 TARJETAS DE CAMPAÑAS (ERP profesional)
    # ======================================================
    for camp in campanias:

        camp_id = camp["campaniaid"]

        # --------------------------------------------------
        # Cargar actuaciones asociadas
        # --------------------------------------------------
        try:
            rel = (
                supa.table("campania_actuacion")
                .select("actuacionid")
                .eq("campaniaid", camp_id)
                .execute()
            ).data or []

            act_ids = [r["actuacionid"] for r in rel]

            if act_ids:
                acc = (
                    supa.table("crm_actuacion")
                    .select("crm_actuacion_estado (estado)")
                    .in_("crm_actuacionid", act_ids)
                    .execute()
                ).data or []
            else:
                acc = []
        except:
            acc = []

        total = len(acc)
        def _estado_nombre(row):
            return (row.get("crm_actuacion_estado") or {}).get("estado", "")

        comp = sum(1 for a in acc if _estado_nombre(a) == "Completada")
        pend = sum(1 for a in acc if _estado_nombre(a) == "Pendiente")
        canc = sum(1 for a in acc if _estado_nombre(a) == "Cancelada")
        avance = int((comp / total) * 100) if total else 0

        # --------------------------------------------------
        # Tarjeta visual
        # --------------------------------------------------
        with st.container(border=True):

            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

            # --------------------------------------
            # INFO PRINCIPAL
            # --------------------------------------
            with col1:
                st.markdown(f"### {camp['nombre']}")
                st.write(camp.get("descripcion") or "—")
                st.write(f"📅 {camp.get('fecha_inicio')} → {camp.get('fecha_fin')}")
                st.write(f"🏷️ Tipo: **{camp.get('tipo_accion','—')}**")

            # --------------------------------------
            # ESTADO
            # --------------------------------------
            with col2:
                estado = camp.get("estado", "borrador")
                st.write("### Estado")
                st.markdown(f"**{BADGE.get(estado, estado)}**")

                # Acciones de estado
                if estado in ["borrador", "activa", "pausada"]:
                    if st.button("🔵 Finalizar", key=f"fin_{camp_id}"):
                        supa.table("campania").update({"estado": "finalizada"}).eq("campaniaid", camp_id).execute()
                        st.rerun()

                    if st.button("🔴 Cancelar", key=f"can_{camp_id}"):
                        supa.table("campania").update({"estado": "cancelada"}).eq("campaniaid", camp_id).execute()
                        st.rerun()

                if estado in ["cancelada", "finalizada"]:
                    if st.button("♻️ Reabrir", key=f"open_{camp_id}"):
                        supa.table("campania").update({"estado": "activa"}).eq("campaniaid", camp_id).execute()
                        st.rerun()

                if estado in ["borrador", "cancelada"]:
                    if st.button("🗑️ Eliminar", key=f"del_{camp_id}"):
                        supa.table("campania").delete().eq("campaniaid", camp_id).execute()
                        supa.table("campania_cliente").delete().eq("campaniaid", camp_id).execute()
                        supa.table("campania_actuacion").delete().eq("campaniaid", camp_id).execute()
                        st.rerun()

            # --------------------------------------
            # PROGRESO
            # --------------------------------------
            with col3:
                st.write("### 📊 Progreso")
                st.write(f"Total: **{total}**")
                st.write(f"Completadas: **{comp}**")
                st.write(f"Pendientes: **{pend}**")
                st.write(f"Canceladas: **{canc}**")
                st.progress(avance / 100 if total else 0)
                st.caption(f"{avance}% completado")

            # --------------------------------------
            # ACCIONES RÁPIDAS
            # --------------------------------------
            with col4:
                st.write("### Opciones")

                if st.button("🔎 Detalle", key=f"d_{camp_id}"):
                    st.session_state["campaniaid"] = camp_id
                    st.session_state["campania_view"] = "detalle"
                    st.rerun()

                if st.button("✏️ Editar", key=f"e_{camp_id}"):
                    st.session_state["campaniaid"] = camp_id
                    st.session_state["campania_step"] = 1
                    st.session_state["campania_view"] = "form"
                    st.rerun()

                if st.button("📈 Progreso", key=f"p_{camp_id}"):
                    st.session_state["campaniaid"] = camp_id
                    st.session_state["campania_view"] = "progreso"
                    st.rerun()

                if st.button("📊 Informes", key=f"i_{camp_id}"):
                    st.session_state["campaniaid"] = camp_id
                    st.session_state["campania_view"] = "informes"
                    st.rerun()

        st.write("")  # Separación visual
