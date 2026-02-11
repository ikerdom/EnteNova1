import streamlit as st
from datetime import date, datetime, timedelta, time
import pandas as pd

from modules.campania.campania_nav import render_campania_nav


# ======================================================
# 📣 CREAR / EDITAR CAMPAÑA COMERCIAL (versión PRO)
# ======================================================

def render(supabase):

    campaniaid = st.session_state.get("campaniaid")
    st.session_state["menu_campanias"] = (
        "Nueva campaña" if campaniaid is None else "Editar campaña"
    )

    render_campania_nav(active_view="form", campaniaid=campaniaid)

    st.title("📣 Crear / Editar campaña comercial")

    # ======================================================
    # BOTÓN CANCELAR
    # ======================================================
    if st.button("⬅️ Cancelar y volver al listado", width="stretch"):
        st.session_state["campaniaid"] = None
        st.session_state["campania_step"] = 1
        st.session_state["campania_view"] = "lista"
        st.rerun()

    # ======================================================
    # CARGAR CAMPAÑA
    # ======================================================
    campania = None
    if campaniaid:
        try:
            res = (
                supabase.table("campania")
                .select("*")
                .eq("campaniaid", campaniaid)
                .single()
                .execute()
            )
            campania = res.data
        except Exception as e:
            st.error(f"Error cargando campaña: {e}")

    # Si está cerrada → bloqueamos edición
        st.info("Esta campaña está cerrada. Solo puedes consultar detalle / informes.")
        return

    # Paso actual
    step = st.session_state.get("campania_step", 1)
    if step not in (1, 2, 3):
        st.session_state["campania_step"] = 1
        step = 1

    # ======================================================
    # SIDEBAR
    # ======================================================
    with st.sidebar:
        st.title("Pasos campaña")
        st.write("1️⃣ Datos generales")
        st.write("2️⃣ Segmentación")
        st.write("3️⃣ Confirmación")

    # ======================================================
    # ROUTING DE PASOS
    # ======================================================
    if step == 1:
        step1_datos_generales(supabase, campania, campaniaid)
    elif step == 2:
        step2_segmentacion(supabase, campania, campaniaid)
    elif step == 3:
        step3_confirmacion(supabase, campania, campaniaid)



# ======================================================
# PASO 1: DATOS GENERALES
# ======================================================

def step1_datos_generales(supabase, campania, campaniaid):

    st.header("1️⃣ Datos generales de la campaña")

    nombre = st.text_input(
        "Nombre de la campaña",
        value=(campania.get("nombre") if campania else "") or "",
    )

    descripcion = st.text_area(
        "Descripción",
        value=(campania.get("descripcion") if campania else "") or "",
        placeholder="Ejemplo: Llamadas a centros de formación…",
    )

    col1, col2 = st.columns(2)

    # Fecha inicio
    with col1:
        fi = campania.get("fecha_inicio") if campania else None
        try:
            fi_default = date.fromisoformat(fi) if fi else date.today()
        except:
            fi_default = date.today()

        fecha_inicio = st.date_input("Fecha inicio", value=fi_default)

    # Fecha fin
    with col2:
        ff = campania.get("fecha_fin") if campania else None
        try:
            ff_default = date.fromisoformat(ff) if ff else fecha_inicio
        except:
            ff_default = fecha_inicio

        fecha_fin = st.date_input("Fecha fin", value=ff_default)

    # Tipo acción
    tipos = ["llamada", "email", "whatsapp", "visita"]
    tipo_accion = st.selectbox(
        "Tipo de acción principal",
        tipos,
        index=tipos.index(campania["tipo_accion"]) if campania and campania["tipo_accion"] in tipos else 0,
    )

    objetivo_total = st.number_input(
        "Objetivo total (opcional)",
        min_value=0,
        value=int(campania.get("objetivo_total") or 0) if campania else 0,
    )

    notas = st.text_area(
        "Notas internas",
        value=(campania.get("notas") if campania else "") or "",
    )

    st.divider()

    # ======================================================
    # BOTONERA
    # ======================================================
    colA, colB, colC = st.columns(3)

    # VOLVER
    with colA:
        if st.button("⬅️ Volver al listado"):
            st.session_state["campania_view"] = "lista"
            st.session_state["campania_step"] = 1
            st.session_state["campaniaid"] = None
            st.rerun()

    # SIGUIENTE
    with colB:
        if st.button("➡️ Siguiente: segmentación"):

            ok, msg = _validar_fechas(fecha_inicio, fecha_fin)
            if not ok:
                st.error(msg)
                return

            payload = {
                "nombre": nombre.strip(),
                "descripcion": descripcion.strip() or None,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "tipo_accion": tipo_accion,
                "objetivo_total": objetivo_total or None,
                "notas": notas.strip() or None,
            }

            if campaniaid:
                supabase.table("campania").update(payload).eq("campaniaid", campaniaid).execute()
            else:
                res = supabase.table("campania").insert(payload).execute()
                if res.data:
                    st.session_state["campaniaid"] = res.data[0]["campaniaid"]

            st.session_state["campania_step"] = 2
            st.rerun()

    # GUARDAR
    with colC:
        if st.button("💾 Guardar borrador"):

            ok, msg = _validar_fechas(fecha_inicio, fecha_fin)
            if not ok:
                st.error(msg)
                return

            payload = {
                "nombre": nombre.strip(),
                "descripcion": descripcion.strip() or None,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "tipo_accion": tipo_accion,
                "objetivo_total": objetivo_total,
                "notas": notas.strip() or None,
            }

            if campaniaid:
                supabase.table("campania").update(payload).eq("campaniaid", campaniaid).execute()
                st.success("Campaña guardada.")
            else:
                res = supabase.table("campania").insert(payload).execute()
                if res.data:
                    st.session_state["campaniaid"] = res.data[0]["campaniaid"]
                st.success("Borrador guardado.")

            st.rerun()



# ======================================================
# PASO 2: SEGMENTACIÓN
# ======================================================

def step2_segmentacion(supabase, campania, campaniaid):

    st.header("2️⃣ Segmentación de la campaña")

    if not campaniaid:
        st.error("Primero completa los datos generales de la campaña.")
        if st.button("⬅️ Ir a datos generales"):
            st.session_state["campania_step"] = 1
            st.rerun()
        return

    st.info("Añade clientes a la campaña manualmente o por grupo.")

    # ======================================================
    # CLIENTES ACTUALES
    # ======================================================
    clientes = _fetch_campania_clientes(supabase, campaniaid)

    st.subheader("Clientes incluidos")

    if not clientes:
        st.info("La campaña aún no tiene clientes.")
    else:
        for c in clientes:
            cli = c.get("cliente") or {}
            with st.container(border=True):
                col1, col2, col3 = st.columns([6, 3, 1])

                with col1:
                    st.markdown(
                        f"**👤 {cli.get('razonsocial') or cli.get('nombre') or '(sin nombre)'}**"
                    )

                with col2:
                    st.caption(f"ID Cliente: {cli.get('clienteid')}")

                with col3:
                    if st.button("❌", key=f"del_cli_{c['campania_clienteid']}"):
                        supabase.table("campania_cliente").delete().eq(
                            "campania_clienteid", c["campania_clienteid"]
                        ).execute()
                        st.rerun()

    st.divider()

    # ======================================================
    # AÑADIR CLIENTE MANUAL
    # ======================================================
    st.subheader("➕ Añadir cliente manualmente")

    texto = st.text_input("Buscar cliente por nombre, ID o referencia")

    if texto and len(texto) >= 2:
        try:
            res = (
                supabase.table("cliente")
                .select("clienteid, razonsocial, nombre, identificador")
                .or_(f"razonsocial.ilike.%{texto}%,clienteid.eq.{texto},identificador.ilike.%{texto}%")
                .limit(50)
                .execute()
            )
            candidatos = res.data or []
        except Exception as e:
            st.error(f"Error buscando clientes: {e}")
            candidatos = []

        for cli in candidatos:
            with st.container(border=True):
                col1, col2 = st.columns([7, 1])

                with col1:
                    st.write(
                        f"**{cli.get('razonsocial') or cli.get('nombre','')}** · ID {cli['clienteid']}"
                    )

                with col2:
                    if st.button("Añadir", key=f"add_cli_{cli['clienteid']}"):
                        _add_cliente_to_campania(supabase, campaniaid, cli["clienteid"])
                        st.rerun()

    st.divider()

    # ======================================================
    # SEGMENTACIÓN POR GRUPO
    # ======================================================
    st.subheader("🎯 Segmentar por grupo")

    try:
        res_g = supabase.table("grupo").select("idgrupo, grupo_nombre").order("grupo_nombre").execute()
        grupos = res_g.data or []
    except:
        grupos = []

    if grupos:
        sel = st.selectbox(
            "Selecciona un grupo",
            ["-- Selecciona --"] + [g["grupo_nombre"] for g in grupos]
        )

        if sel != "-- Selecciona --":
            grupo = next(g for g in grupos if g["grupo_nombre"] == sel)

            res_cli = (
                supabase.table("cliente")
                .select("clienteid, razonsocial, nombre")
                .eq("idgrupo", grupo["idgrupo"])
                .execute()
            )
            clientes_gr = res_cli.data or []

            st.write(f"{len(clientes_gr)} clientes encontrados en {sel}")

            for cli in clientes_gr:
                with st.container(border=True):
                    col1, col2 = st.columns([7, 1])

                    with col1:
                        st.write(
                            f"{cli.get('razonsocial') or cli.get('nombre','')} · ID {cli['clienteid']}"
                        )

                    with col2:
                        if st.button("Añadir", key=f"add_g_{cli['clienteid']}"):
                            _add_cliente_to_campania(supabase, campaniaid, cli["clienteid"])
                            st.rerun()

    st.divider()

    # ======================================================
    # BOTONERA
    # ======================================================
    colA, colB = st.columns(2)

    with colA:
        if st.button("⬅️ Volver a datos generales"):
            st.session_state["campania_step"] = 1
            st.rerun()

    with colB:
        if st.button("➡️ Ir a confirmación"):
            st.session_state["campania_step"] = 3
            st.rerun()



# ======================================================
# PASO 3: CONFIRMACIÓN Y ACTIVACIÓN
# ======================================================

def step3_confirmacion(supabase, campania, campaniaid):

    st.header("3️⃣ Confirmación")

    if not campaniaid:
        st.error("No hay campaña seleccionada.")
        if st.button("⬅️ Volver"):
            st.session_state["campania_step"] = 1
            st.rerun()
        return

    # Recargar campaña actualizada
    try:
        res = (
            supabase.table("campania")
            .select("*")
            .eq("campaniaid", campaniaid)
            .single()
            .execute()
        )
        campania = res.data
    except:
        st.error("Error cargando campaña.")
        return

    clientes = _fetch_campania_clientes(supabase, campaniaid)

    if len(clientes) == 0:
        st.error("La campaña no tiene clientes asignados.")
        if st.button("⬅️ Volver a segmentación"):
            st.session_state["campania_step"] = 2
            st.rerun()
        return

    # ======================================================
    # RESUMEN
    # ======================================================
    st.subheader("📄 Datos generales")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Nombre:** {campania['nombre']}")
        st.write(f"**Acción principal:** {campania['tipo_accion']}")

    with col2:
        st.write(f"**Inicio:** {campania['fecha_inicio']}")
        st.write(f"**Fin:** {campania['fecha_fin']}")

    st.write(f"**Clientes asignados:** {len(clientes)}")

    with st.expander("Ver lista de clientes"):
        df = pd.DataFrame([
            {
                "ID": (c.get("cliente") or {}).get("clienteid"),
                "Cliente": (c.get("cliente") or {}).get("razonsocial")
                or (c.get("cliente") or {}).get("nombre")
            }
            for c in clientes
        ])
        st.dataframe(df, hide_index=True, width="stretch")

    st.divider()

    # ======================================================
    # ACTIVACIÓN
    # ======================================================
    st.subheader("⚙️ Generación de actuaciones CRM")

    st.info("Se generarán actuaciones para cada cliente y la campaña pasará a estado **activa**.")

    if st.button("🚀 Generar actuaciones y activar"):

        ok, msg = _validar_activacion(campania, clientes)
        if not ok:
            st.error(msg)
            return

        with st.spinner("Generando actuaciones..."):
            creadas = _generar_acciones_campania(supabase, campania, clientes)

        st.success(f"Actuaciones generadas: {creadas}")
        st.session_state["campania_step"] = 1
        st.rerun()

    if st.button("⬅️ Volver a segmentación"):
        st.session_state["campania_step"] = 2
        st.rerun()



# ======================================================
# HELPERS
# ======================================================

def _validar_fechas(fi, ff):
    if ff < fi:
        return False, "La fecha fin no puede ser anterior a la fecha inicio."
    return True, None


def _validar_segmentacion(clientes):
    if not clientes:
        return False, "La campaña no tiene clientes."
    return True, None


def _validar_activacion(campania, clientes):
    try:
        fi = date.fromisoformat(str(campania["fecha_inicio"]))
        ff = date.fromisoformat(str(campania["fecha_fin"]))
    except:
        return False, "Fechas no válidas."

    ok, msg = _validar_fechas(fi, ff)
    if not ok:
        return False, msg

    ok, msg = _validar_segmentacion(clientes)
    if not ok:
        return False, msg

    return True, None


def _fetch_campania_clientes(supa, campaniaid):
    try:
        res = (
            supa.table("campania_cliente")
            .select("campania_clienteid, clienteid, cliente (clienteid, razonsocial, nombre)")
            .eq("campaniaid", campaniaid)
            .execute()
        )
        return res.data or []
    except:
        return []


def _add_cliente_to_campania(supa, campaniaid, clienteid):
    try:
        supa.table("campania_cliente").insert(
            {"campaniaid": campaniaid, "clienteid": clienteid}
        ).execute()
    except Exception as e:
        st.warning("No se pudo añadir el cliente (ya existe o error en BD).")


def _campania_tiene_actuaciones(supa, campaniaid):
    try:
        res = (
            supa.table("campania_actuacion")
            .select("actuacionid", count="exact")
            .eq("campaniaid", campaniaid)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except:
        return False


#
# ======================================================
# GENERACIÓN DE ACTUACIONES
# ======================================================
#

def _generar_acciones_campania(supa, campania, clientes):

    campaniaid = campania["campaniaid"]

    if _campania_tiene_actuaciones(supa, campaniaid):
        return 0

    try:
        fi = date.fromisoformat(str(campania["fecha_inicio"]))
        ff = date.fromisoformat(str(campania["fecha_fin"]))
    except:
        fi = date.today()
        ff = fi

    tipo = campania.get("tipo_accion") or "llamada"
    trab_default = st.session_state.get("trabajadorid")
    dias = max((ff - fi).days + 1, 1)

    creadas = 0

    estado_id = None
    try:
        row = (
            supa.table("crm_actuacion_estado")
            .eq("estado", "Pendiente")
            .single()
            .execute()
            .data
        )
    except Exception:
        estado_id = None


    for idx, c in enumerate(clientes):
        cli = c.get("cliente") or {}
        clienteid = cli.get("clienteid")
        if not clienteid:
            continue

        offset = idx % dias
        fecha = fi + timedelta(days=offset)

        trabajadorid = trab_default
        if not trabajadorid:
            continue

        slot = datetime.combine(fecha, time(9, 0))

        payload = {
            "clienteid": clienteid,
            "trabajador_creadorid": trabajadorid,
            "titulo": f"Campaña: {campania['nombre']}",
            "descripcion": campania.get("descripcion") or "",
            "fecha_accion": slot.isoformat(),
            "fecha_vencimiento": fecha.isoformat(),
        }
        if estado_id:
            payload["crm_actuacion_estadoid"] = estado_id
        try:
            res = supa.table("crm_actuacion").insert(payload).execute()
            if not res.data:
                continue

            actid = res.data[0]["crm_actuacionid"]

            supa.table("campania_actuacion").insert(
                {"campaniaid": campaniaid, "actuacionid": actid, "clienteid": clienteid}
            ).execute()

            creadas += 1

        except Exception as e:
            st.error(f"Error creando actuación para cliente {clienteid}: {e}")

    return creadas
