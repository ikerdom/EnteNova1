# modules/historial.py
# Historial de comunicaciones y acciones

from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st


def _table_exists(supabase, table: str) -> bool:
    if not supabase:
        return False
    try:
        supabase.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _safe(v: Any, default: str = "-") -> str:
    return default if v in (None, "", "null") else str(v)


def _badge(label: str, *, bg: str = "#e2e8f0", color: str = "#0f172a") -> str:
    return (
        f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
        f"background:{bg};color:{color};font-size:0.82rem;font-weight:600;'>"
        f"{label}</span>"
    )


def _tipo_ui(tipo: str) -> str:
    t = (tipo or "accion").lower()
    mapping = {
        "llamada": ("📞 Llamada", "#e0f2fe", "#075985"),
        "reunion": ("🧑‍💼 Reunión", "#fef9c3", "#854d0e"),
        "email": ("✉️ Email", "#ede9fe", "#5b21b6"),
        "whatsapp": ("💬 WhatsApp", "#dcfce7", "#166534"),
        "otro": ("📝 Otro", "#f3f4f6", "#374151"),
        "accion": ("📌 Acción", "#f3f4f6", "#374151"),
    }
    label, bg, color = mapping.get(t, ("📌 Acción", "#f3f4f6", "#374151"))
    return _badge(label, bg=bg, color=color)


def render_historial(supabase):
    st.header("Historial de comunicaciones")
    st.caption("Consulta y registra tus interacciones con clientes o contactos.")

    if not supabase:
        st.warning("No hay conexion a base de datos.")
        return

    trabajadorid = st.session_state.get("trabajadorid")
    trabajador_nombre = st.session_state.get("user_nombre", "Desconocido")
    clienteid = st.session_state.get("cliente_actual")

    if not trabajadorid:
        st.warning("No hay sesion de trabajador activa.")
        return

    has_mensajes = _table_exists(supabase, "mensaje_contacto")
    has_crm = _table_exists(supabase, "crm_actuacion")
    has_log = _table_exists(supabase, "log_cambio")

    if not has_mensajes and not has_crm:
        st.info("No hay tablas de comunicaciones (mensaje_contacto o crm_actuacion).")
        return

    # Catalogos
    try:
        trabajadores = supabase.table("trabajador").select("trabajadorid,nombre,apellidos").execute().data or []
    except Exception:
        trabajadores = []
    try:
        clientes = supabase.table("cliente").select("clienteid,razonsocial,nombre").order("razonsocial").execute().data or []
    except Exception:
        clientes = []

    trabajadores_map = {f"{t.get('nombre','')} {t.get('apellidos','')}".strip(): t.get("trabajadorid") for t in trabajadores}
    clientes_map = {(c.get("razonsocial") or c.get("nombre") or "-"): c.get("clienteid") for c in clientes}

    st.markdown("### Filtros")
    colf1, colf2, colf3, colf4, colf5 = st.columns([2, 2, 2, 2, 2])
    with colf1:
        trab_sel = st.selectbox("Trabajador", ["Yo mismo"] + list(trabajadores_map.keys()))
    with colf2:
        cli_sel = st.selectbox("Cliente", ["Todos"] + list(clientes_map.keys()))
    with colf3:
        tipo_filtro = st.selectbox("Tipo de comunicacion", ["Todos", "llamada", "reunion", "email", "whatsapp", "otro"], index=0)
    with colf4:
        fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=60))
        fecha_hasta = st.date_input("Hasta", value=date.today())
    with colf5:
        buscar_txt = st.text_input("Buscar texto", placeholder="Resumen, mensaje, descripcion...")

    trabajador_filtro = trabajadorid if trab_sel == "Yo mismo" else trabajadores_map.get(trab_sel)
    if clienteid:
        cli_sel = next((k for k, v in clientes_map.items() if v == clienteid), cli_sel)

    st.markdown("---")
    st.subheader("Registrar nueva comunicacion")

    # Contactos del cliente
    contactos = []
    try:
        q_contactos = supabase.table("cliente_contacto").select("cliente_contactoid,tipo,valor,clienteid,principal")
        if clienteid:
            q_contactos = q_contactos.eq("clienteid", clienteid)
        contactos = q_contactos.order("principal", desc=True).order("tipo").execute().data or []
    except Exception:
        contactos = []

    contactos_map = {f"{c.get('tipo','-')}: {c.get('valor','-')}": c.get("cliente_contactoid") for c in contactos}
    lista_contactos = list(contactos_map.keys()) + ["Otro / no registrado"]

    with st.form("form_comunicacion"):
        c1, c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo", ["llamada", "reunion", "email", "whatsapp", "otro"])
            contacto_sel = st.selectbox("Contacto", lista_contactos)
        with c2:
            fecha = st.date_input("Fecha", value=date.today())
            hora = st.time_input("Hora", value=datetime.now().time())

        resumen = st.text_input("Resumen breve", placeholder="Ej: llamada con cliente sobre presupuesto")
        detalle = st.text_area("Detalles", placeholder="Describe lo tratado...", height=90)

        st.markdown("---")
        prev1, prev2 = st.columns([2, 1])
        with prev1:
            st.caption("Vista previa")
            st.write(resumen or "-")
            st.write(detalle[:140] + ("..." if len(detalle) > 140 else ""))
        with prev2:
            st.caption("Datos")
            st.write(f"Tipo: {tipo}")
            st.write(f"{fecha} {hora.strftime('%H:%M')}")

        enviado = st.form_submit_button("Registrar")

    if enviado:
        if not resumen.strip():
            st.warning("El resumen es obligatorio.")
        else:
            try:
                if has_mensajes:
                    contacto_id = contactos_map.get(contacto_sel)
                    registro = {
                        "cliente_contactoid": contacto_id,
                        "trabajadorid": trabajadorid,
                        "remitente": trabajador_nombre,
                        "contenido": detalle or resumen,
                        "fecha_envio": datetime.combine(fecha, hora).replace(microsecond=0).isoformat(),
                        "canal": tipo,
                        "tipo_comunicacion": tipo,
                        "estado_envio": "enviado",
                        "leido": True,
                    }
                    supabase.table("mensaje_contacto").insert(registro).execute()
                    st.success("Comunicacion registrada correctamente.")
                else:
                    accion = {
                        "clienteid": clienteid,
                        "trabajador_creadorid": trabajadorid,
                        "titulo": resumen.strip(),
                        "descripcion": detalle or resumen,
                        "fecha_accion": datetime.combine(fecha, hora).replace(microsecond=0).isoformat(),
                        "fecha_vencimiento": fecha.isoformat(),
                    }
                    supabase.table("crm_actuacion").insert(accion).execute()
                    st.success("Accion registrada en CRM.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar comunicacion: {e}")

    st.markdown("---")
    st.subheader("Historial de comunicaciones recientes")
    topn = st.selectbox("Mostrar", [50, 100, 200, 500], index=2)

    mensajes: List[Dict[str, Any]] = []
    if has_mensajes:
        try:
            query = (
                supabase.table("mensaje_contacto")
                .select("*")
                .eq("trabajadorid", trabajador_filtro)
                .order("fecha_envio", desc=True)
                .limit(topn)
            )

            if cli_sel != "Todos":
                cli_id = clientes_map.get(cli_sel)
                if cli_id:
                    contactos_ids = (
                        supabase.table("cliente_contacto")
                        .select("cliente_contactoid")
                        .eq("clienteid", cli_id)
                        .execute()
                        .data
                    )
                    ids = [c.get("cliente_contactoid") for c in contactos_ids if c.get("cliente_contactoid")]
                    if ids:
                        try:
                            query = query.in_("cliente_contactoid", ids)
                        except Exception:
                            try:
                                query = query.in_("contacto_id", ids)
                            except Exception:
                                pass

            if tipo_filtro != "Todos":
                query = query.eq("tipo_comunicacion", tipo_filtro)
            if fecha_desde:
                query = query.gte("fecha_envio", fecha_desde.isoformat())
            if fecha_hasta:
                query = query.lte("fecha_envio", fecha_hasta.isoformat())

            mensajes = query.execute().data or []
        except Exception as e:
            st.error(f"Error al cargar historial: {e}")
            mensajes = []
    else:
        # Fallback a CRM
        try:
            query = supabase.table("crm_actuacion").select("*")
            if clienteid:
                query = query.eq("clienteid", clienteid)
            if trabajador_filtro:
                query = query.eq("trabajador_creadorid", trabajador_filtro)
            mensajes = query.order("fecha_accion", desc=True).limit(topn).execute().data or []
        except Exception:
            mensajes = []

    if buscar_txt:
        q = buscar_txt.lower()
        def _match(m):
            for k in ["titulo", "contenido", "descripcion", "remitente"]:
                if q in str(m.get(k, "")).lower():
                    return True
            return False
        mensajes = [m for m in mensajes if _match(m)]

    if not mensajes:
        st.info("No hay comunicaciones registradas todavia.")
    else:
        st.caption(f"Registros: {len(mensajes)}")

        contacto_ids = [m.get("cliente_contactoid") or m.get("contacto_id") for m in mensajes]
        contacto_map = {}
        if contacto_ids:
            try:
                rows_contacto = (
                    supabase.table("cliente_contacto")
                    .select("cliente_contactoid, tipo, valor")
                    .in_("cliente_contactoid", contacto_ids)
                    .execute()
                    .data
                ) or []
                contacto_map = {r.get("cliente_contactoid"): f"{r.get('tipo','-')}: {r.get('valor','-')}" for r in rows_contacto}
            except Exception:
                contacto_map = {}

        tipos_count = {}
        for m in mensajes:
            t = (m.get("tipo_comunicacion") or m.get("canal") or "accion").lower()
            tipos_count[t] = tipos_count.get(t, 0) + 1
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(mensajes))
        m2.metric("Llamadas", tipos_count.get("llamada", 0))
        m3.metric("Emails", tipos_count.get("email", 0))
        m4.metric("WhatsApp", tipos_count.get("whatsapp", 0))

        # Timeline simple por mes (últimos 12 meses visibles)
        st.markdown("#### Timeline (últimos 12 meses)")
        by_month: Dict[str, int] = {}
        for m in mensajes:
            fecha_raw = m.get("fecha_envio") or m.get("fecha_accion") or ""
            fecha_txt = str(fecha_raw)[:10]
            if len(fecha_txt) >= 7:
                key = fecha_txt[:7]
                by_month[key] = by_month.get(key, 0) + 1
        months = sorted(by_month.keys())[-12:]
        if months:
            data = [{"Mes": k, "Registros": by_month[k]} for k in months]
            try:
                import pandas as pd

                df = pd.DataFrame(data).set_index("Mes")
                st.bar_chart(df, height=180)
            except Exception:
                st.table(data)

        st.markdown(" ")
        for m in mensajes:
            fecha_raw = m.get("fecha_envio") or m.get("fecha_accion") or ""
            fecha_txt = str(fecha_raw)[:16].replace("T", " ")
            tipo = m.get("tipo_comunicacion") or m.get("canal") or "accion"
            contacto_id = m.get("cliente_contactoid") or m.get("contacto_id")
            contacto_nombre = contacto_map.get(contacto_id, "-")
            titulo = _safe(m.get("titulo") or m.get("remitente") or "Comunicación")
            cuerpo = _safe(m.get("contenido") or m.get("descripcion"))

            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(_tipo_ui(tipo), unsafe_allow_html=True)
                    st.markdown(f"**{titulo}**")
                    st.caption(cuerpo[:180] + ("..." if len(cuerpo) > 180 else ""))
                with c2:
                    st.write("**Fecha**")
                    st.write(fecha_txt or "-")
                    st.write("**Contacto**")
                    st.write(contacto_nombre)

                with st.expander("Ver detalle"):
                    st.markdown(f"**Remitente:** {_safe(m.get('remitente'))}")
                    st.markdown(f"**Título:** {_safe(m.get('titulo'))}")
                    st.markdown(f"**Mensaje:** {cuerpo}")

    st.markdown("---")

    if has_log:
        st.subheader("Cambios en base de datos")
        if st.button("Ver historial de cambios (Log SQL)", use_container_width=True):
            st.session_state["mostrar_log_sql"] = True

        if st.session_state.get("mostrar_log_sql"):
            render_log_cambios(supabase)
    else:
        st.caption("Log de cambios no disponible (tabla log_cambio no existe).")


import json
import pandas as pd


def render_log_cambios(supabase):
    st.markdown("### Historial de cambios en base de datos")

    with st.expander("Ver historial de cambios (Log SQL)", expanded=False):
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            tabla_sel = st.selectbox(
                "Tabla",
                ["Todas", "producto", "cliente", "pedido", "crm_actuacion", "mensaje_contacto"],
                index=0,
            )
        with col2:
            accion_sel = st.selectbox("Accion", ["Todas", "INSERT", "UPDATE", "DELETE"], index=0)
        with col3:
            buscar = st.text_input("Buscar ID, campo o texto")

        st.markdown("---")

        try:
            q = (
                supabase.table("log_cambio")
                .select("logid, tabla, registro_id, accion, tipo_log, usuario, trabajadorid, fecha, detalle")
                .order("fecha", desc=True)
                .limit(300)
            )

            if tabla_sel != "Todas":
                q = q.eq("tabla", tabla_sel)

            if accion_sel != "Todas":
                q = q.eq("accion", accion_sel)

            logs = q.execute().data or []

            if buscar:
                buscar_low = buscar.lower()
                logs = [l for l in logs if buscar_low in json.dumps(l, default=str).lower()]

        except Exception as e:
            st.error(f"Error cargando historial de cambios: {e}")
            return

        if not logs:
            st.info("No hay cambios registrados con esos filtros.")
            return

        for log in logs:
            lid = log.get("logid")
            tabla = log.get("tabla", "-")
            accion = log.get("accion", "-")
            fecha = str(log.get("fecha") or "")[:19].replace("T", " ")
            detalle = log.get("detalle")

            st.markdown(f"**{tabla}** | {accion} | {fecha} | ID: {lid}")
            if detalle:
                st.code(detalle)
