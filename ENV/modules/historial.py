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
    colf1, colf2, colf3, colf4 = st.columns([2, 2, 2, 2])
    with colf1:
        trab_sel = st.selectbox("Trabajador", ["Yo mismo"] + list(trabajadores_map.keys()))
    with colf2:
        cli_sel = st.selectbox("Cliente", ["Todos"] + list(clientes_map.keys()))
    with colf3:
        tipo_filtro = st.selectbox("Tipo de comunicacion", ["Todos", "llamada", "reunion", "email", "whatsapp", "otro"], index=0)
    with colf4:
        fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=60))
        fecha_hasta = st.date_input("Hasta", value=date.today())

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

    mensajes: List[Dict[str, Any]] = []
    if has_mensajes:
        try:
            query = (
                supabase.table("mensaje_contacto")
                .select("*")
                .eq("trabajadorid", trabajador_filtro)
                .order("fecha_envio", desc=True)
                .limit(200)
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
            mensajes = query.order("fecha_accion", desc=True).limit(200).execute().data or []
        except Exception:
            mensajes = []

    if not mensajes:
        st.info("No hay comunicaciones registradas todavia.")
    else:
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

        for m in mensajes:
            fecha_raw = m.get("fecha_envio") or m.get("fecha_accion") or ""
            fecha_txt = str(fecha_raw)[:16].replace("T", " ")
            tipo = m.get("tipo_comunicacion") or m.get("canal") or "accion"
            contacto_id = m.get("cliente_contactoid") or m.get("contacto_id")
            contacto_nombre = contacto_map.get(contacto_id, "-")

            with st.expander(f"{tipo.capitalize()} | {fecha_txt} | {contacto_nombre}"):
                st.markdown(f"**Remitente:** {_safe(m.get('remitente'))}")
                st.markdown(f"**Titulo:** {_safe(m.get('titulo'))}")
                st.markdown(f"**Mensaje:** {_safe(m.get('contenido') or m.get('descripcion'))}")

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
