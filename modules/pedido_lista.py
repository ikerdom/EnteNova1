import math
import pandas as pd
import streamlit as st
from datetime import date

from modules.pedido_api import (
    listar,
    detalle,
    lineas,
    totales,
    recalcular_totales,
    observaciones,
    crear_observacion,
    catalogos,
    agregar_linea,
    borrar_linea,
)
from modules.pedido_form import render_pedido_form


def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end


def _label_from(catalog: dict, id_val) -> str:
    if not id_val:
        return "-"
    for k, v in (catalog or {}).items():
        if v == id_val:
            return k
    return "-"


def _color_estado(nombre_estado: str) -> str:
    if not nombre_estado:
        return "#9ca3af"
    n = (nombre_estado or "").lower()
    if "pend" in n:
        return "#f59e0b"
    if "confir" in n or "curso" in n:
        return "#3b82f6"
    if "enviado" in n:
        return "#6366f1"
    if "entreg" in n or "factur" in n:
        return "#10b981"
    if "cancel" in n or "devol" in n:
        return "#ef4444"
    return "#6b7280"


def _money(v):
    try:
        return f"{float(v):.2f} €"
    except Exception:
        return "-"


def _abrir_edicion(pedidoid: int):
    st.session_state["pedido_editar_id"] = pedidoid
    st.session_state["pedido_show_form"] = True
    st.session_state["show_pedido_modal"] = False
    st.rerun()


def render_pedido_lista(_supabase=None):
    modo_inci = st.session_state.get("modo_incidencias", False)
    tipo_filtro = st.session_state.get("pedido_tipo_filtro")

    if modo_inci:
        st.header("🚨 Gestión de incidencias")
        st.caption("Listado de pedidos con incidencias registradas (pendientes o solucionadas).")
    elif tipo_filtro == "Devolución":
        st.header("↩️ Gestión de devoluciones")
        st.caption("Pedidos de devolución que impactan en stock y facturación.")
    else:
        st.header("📦 Gestión de pedidos")
        st.caption("Gestiona pedidos: cabecera, líneas, totales y observaciones vía API.")

    session = st.session_state
    defaults = {
        "pedido_page": 1,
        "pedido_view": "Tarjetas",
        "pedido_show_form": False,
        "pedido_editar_id": None,
        "show_pedido_modal": False,
        "pedido_modal_id": None,
    }
    for k, v in defaults.items():
        session.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    # Catálogos para labels (desde API)
    try:
        cats = catalogos()
        clientes_map = {c["label"]: c["id"] for c in cats.get("clientes", [])}
        clientes_rev = {c["id"]: c["label"] for c in cats.get("clientes", [])}
        trabajadores_map = {t["label"]: t["id"] for t in cats.get("trabajadores", [])}
        trabajadores_rev = {t["id"]: t["label"] for t in cats.get("trabajadores", [])}
        estados_map = {e["label"]: e["id"] for e in cats.get("estados", [])}
        estados_rev = {v: k for k, v in estados_map.items()}
        tipos_map = {t["label"]: t["id"] for t in cats.get("tipos", [])}
        procedencias_map = {p["label"]: p["id"] for p in cats.get("procedencias", [])}
    except Exception:
        clientes_map = {}
        clientes_rev = {}
        trabajadores_map = {}
        trabajadores_rev = {}
        estados_map = {}
        estados_rev = {}
        tipos_map = {}
        procedencias_map = {}

    if session.get("pedido_show_form"):
        st.markdown("### Editor de pedido (cabecera)")
        try:
            render_pedido_form(None, pedidoid=session.get("pedido_editar_id"), on_saved_rerun=True)
        except Exception as e:
            st.error(f"Error abriendo formulario: {e}")
        st.markdown("---")

    colf1, colf2, colf3, colf4, colf5 = st.columns([2, 2, 2, 2, 1])
    with colf1:
        q = st.text_input("🔍 Buscar (nº pedido / referencia / cliente)", key="pedido_q")
    with colf2:
        estado_sel = st.selectbox("Estado", ["Todos"] + list(estados_map.keys()), key="pedido_estado")
    with colf3:
        tipo_sel = st.selectbox("Tipo", ["Todos"] + list(tipos_map.keys()), key="pedido_tipo")
    with colf4:
        proc_sel = st.selectbox("Procedencia", ["Todas"] + list(procedencias_map.keys()), key="pedido_proc")
    with colf5:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="pedido_view")

    colf6, colf7, colf8 = st.columns([2, 2, 2])
    with colf6:
        trabajador_sel = st.selectbox("Trabajador", ["Todos"] + list(trabajadores_map.keys()), key="pedido_trab")
    with colf7:
        fecha_desde = st.date_input("Desde", value=None, key="pedido_from")
    with colf8:
        fecha_hasta = st.date_input("Hasta", value=None, key="pedido_to")

    if st.button("🆕 Nuevo pedido", use_container_width=True):
        session["pedido_show_form"] = True
        session["pedido_editar_id"] = None
        session["show_pedido_modal"] = False

    st.markdown("---")

    pedidos = []
    total = 0
    try:
        per_page = page_size_cards if view == "Tarjetas" else page_size_table
        params = {
            "q": q or None,
            "estadoid": estados_map.get(estado_sel) if estado_sel != "Todos" else None,
            "tipo_pedidoid": tipos_map.get(tipo_sel) if tipo_sel != "Todos" else None,
            "procedencia_pedidoid": procedencias_map.get(proc_sel) if proc_sel != "Todas" else None,
            "trabajadorid": trabajadores_map.get(trabajador_sel) if trabajador_sel != "Todos" else None,
            "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
            "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
            "devoluciones": tipo_filtro == "Devolución",
            "page": session.pedido_page,
            "page_size": per_page,
        }
        payload = listar(params)
        pedidos = payload.get("data", [])
        total = payload.get("total", 0)
    except Exception as e:
        st.error(f"❌ Error cargando pedidos: {e}")
        return

    total_pages = max(1, math.ceil(max(1, total) / (page_size_cards if view == "Tarjetas" else page_size_table)))
    st.caption(f"Página {session.pedido_page} de {total_pages} · Total aprox. página: {total}")

    colp1, colp2, colp3, _ = st.columns([1, 1, 1, 5])
    if colp1.button("⏮️", disabled=session.pedido_page <= 1):
        session.pedido_page = 1
        st.rerun()
    if colp2.button("⬅️", disabled=session.pedido_page <= 1):
        session.pedido_page -= 1
        st.rerun()
    if colp3.button("➡️", disabled=session.pedido_page >= total_pages):
        session.pedido_page += 1
        st.rerun()

    st.markdown("---")

    if not pedidos:
        st.info("ℹ️ No hay pedidos que coincidan con los filtros.")
        return

    if view == "Tarjetas":
        cols = st.columns(3)
        for idx, p in enumerate(pedidos):
            with cols[idx % 3]:
                _render_pedido_card(p, estados_rev, clientes_rev)
    else:
        _render_table(pedidos, estados_rev)

    if session.get("show_pedido_modal"):
        _render_pedido_modal(
            session.get("pedido_modal_id"),
            estados_rev,
            clientes_rev,
            {},
            {},
            {},
        )


def _render_table(pedidos: list[dict], estados_rev: dict):
    rows = []
    for p in pedidos:
        rows.append(
            {
                "ID": p.get("pedidoid"),
                "Número": p.get("numero"),
                "ClienteID": p.get("clienteid"),
                "Estado": estados_rev.get(p.get("estado_pedidoid")) or "-",
                "Fecha": p.get("fecha_pedido"),
                "Referencia": p.get("referencia_cliente"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_pedido_card(p, estados_rev, clientes_rev):
    cliente_nombre = clientes_rev.get(p.get("clienteid")) or "-"
    estado_nombre = estados_rev.get(p.get("estado_pedidoid"))
    color_estado = _color_estado(estado_nombre)

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;
                    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div><b>#{_safe(p.get('numero'))}</b> · {_safe(cliente_nombre)}</div>
                <span style="background:{color_estado};color:#fff;padding:3px 8px;border-radius:8px;font-size:0.8rem;">
                    {estado_nombre or '-'}
                </span>
            </div>
            <div style="margin-top:4px;color:#555;font-size:0.9rem;">
                📅 {_safe(p.get("fecha_pedido"))}
            </div>
            <div style="color:#777;font-size:0.85rem;margin-top:4px;">
                Ref. cliente: {_safe(p.get("referencia_cliente"))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if p.get("presupuesto_origenid"):
        st.markdown(f"🔗 **Origen:** Presupuesto #{p['presupuesto_origenid']}")

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("📄 Ficha", key=f"ficha_{p['pedidoid']}", use_container_width=True):
            st.session_state["pedido_modal_id"] = p["pedidoid"]
            st.session_state["show_pedido_modal"] = True
            st.session_state["pedido_show_form"] = False
            st.rerun()
    with colB:
        st.button(
            "✏️ Editar",
            key=f"edit_{p['pedidoid']}",
            use_container_width=True,
            on_click=(lambda pid=p["pedidoid"]: _abrir_edicion(pid)),
        )
    with colC:
        # Duplicar se desactiva para simplificar el flujo
        st.empty()


def _render_pedido_modal(
    pedidoid: int,
    estados_rev: dict,
    clientes_rev: dict,
    trabajadores: dict,
    formas_pago: dict,
    transportistas: dict,
):
    if not pedidoid:
        return

    st.markdown("---")
    st.markdown("### 📄 Ficha del pedido")

    try:
        p = detalle(pedidoid)
    except Exception as e:
        st.error(f"❌ Error cargando pedido: {e}")
        return

    estado_lbl = estados_rev.get(p.get("estado_pedidoid")) or "-"
    cliente_lbl = clientes_rev.get(p.get("clienteid")) or "-"
    color_estado = _color_estado(estado_lbl)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        if st.button("↩️ Cerrar ficha", use_container_width=True):
            st.session_state["show_pedido_modal"] = False
            st.session_state["pedido_modal_id"] = None
            st.rerun()
    with c2:
        st.button("🗑️ Eliminar pedido", use_container_width=True, disabled=True)
    with c3:
        st.button("🧾 Crear devolución", use_container_width=True, disabled=True)

    with st.expander("📋 Detalle general del pedido", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Cliente:** {cliente_lbl or p.get('clienteid') or '-'}")
            st.markdown(
                f"**Estado:** <span style='color:{color_estado};font-weight:700'>{estado_lbl}</span>",
                unsafe_allow_html=True,
            )
        with col2:
            st.text(f"Fecha pedido: {_safe(p.get('fecha_pedido'))}")
            st.text(f"Confirmada: {_safe(p.get('fecha_confirmada'))}")
        with col3:
            st.text(f"Entrega prevista: {_safe(p.get('fecha_entrega_prevista'))}")
            st.text(f"Ref. cliente: {_safe(p.get('referencia_cliente'))}")

    st.markdown("---")
    st.subheader("✏️ Cabecera del pedido")
    try:
        render_pedido_form(None, pedidoid=pedidoid, on_saved_rerun=True)
    except Exception as e:
        st.error(f"❌ Error al abrir el formulario de cabecera: {e}")

    st.markdown("---")
    st.subheader("📦 Líneas del pedido")
    try:
        lineas_data = lineas(pedidoid)
    except Exception as e:
        st.error(f"❌ Error cargando líneas: {e}")
        lineas_data = []

    if not lineas_data:
        st.info("ℹ️ No hay líneas registradas para este pedido.")
    else:
        df = pd.DataFrame(lineas_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Alta / baja de líneas
    with st.expander("➕ Añadir línea", expanded=False):
        with st.form(f"form_add_linea_{pedidoid}"):
            productoid = st.number_input("ID producto (opcional)", min_value=0, value=0, step=1)
            nombre_prod = st.text_input("Descripción / nombre del producto")
            cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0)
            precio = st.number_input("Precio base unitario (sin IVA)", min_value=0.0, value=0.0, step=0.01)
            desc_manual = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            add_ok = st.form_submit_button("💾 Añadir línea", use_container_width=True)

        if add_ok:
            try:
                payload = {
                    "productoid": int(productoid) if productoid else None,
                    "nombre_producto": nombre_prod.strip() or None,
                    "cantidad": float(cantidad),
                    "precio_unitario": float(precio),
                    "descuento_pct": float(desc_manual),
                }
                agregar_linea(pedidoid, payload)
                st.success("✅ Línea añadida.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error añadiendo línea: {e}")

    if lineas_data:
        with st.expander("🗑️ Eliminar línea", expanded=False):
            opciones = {f"{l.get('pedido_detalleid')} · {l.get('nombre_producto')}": l.get("pedido_detalleid") for l in lineas_data}
            sel = st.selectbox("Selecciona línea a eliminar", list(opciones.keys()))
            if st.button("Eliminar línea seleccionada"):
                try:
                    borrar_linea(pedidoid, opciones[sel])
                    st.success("🗑️ Línea eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando línea: {e}")

    st.markdown("---")
    st.subheader("💰 Totales del pedido")
    try:
        tot = totales(pedidoid)
    except Exception:
        tot = None

    colT1, colT2, colT3, colT4, colT5 = st.columns(5)
    if tot:
        colT1.metric("Base imponible", _money(tot.get("base_imponible")))
        colT2.metric("IVA", _money(tot.get("iva_importe")))
        colT3.metric("Total", _money(tot.get("total_importe")))
        colT4.metric("Gastos envío", _money(tot.get("gastos_envio")))
        colT5.metric("Env. sin cargo", "Sí" if tot.get("envio_sin_cargo") else "No")
    else:
        st.warning("⚠️ No hay totales calculados aún para este pedido.")

    with st.expander("🔄 Recalcular totales", expanded=False):
        st.caption("Recalcula los importes con tarifas, descuentos e impuestos reales por producto.")

        use_iva = st.checkbox("Aplicar IVA (según producto o tarifa)", value=True)
        gastos = st.number_input("Gastos de envío (€)", min_value=0.0, value=float(tot.get("gastos_envio", 0.0)) if tot else 0.0, step=0.01)
        envio_sin_cargo = st.checkbox("Envío sin cargo", value=bool(tot.get("envio_sin_cargo")) if tot else False)

        if st.button("🔄 Recalcular ahora"):
            try:
                recalc = recalcular_totales(
                    pedidoid,
                    use_iva=use_iva,
                    gastos_envio=gastos,
                    envio_sin_cargo=envio_sin_cargo,
                )
                st.success("✅ Totales recalculados.")
                st.session_state["pedido_totales"] = recalc
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error recalculando totales: {e}")

    st.markdown("---")
    st.subheader("📝 Observaciones")

    try:
        obs = observaciones(pedidoid)
        if not obs:
            st.info("No hay observaciones registradas.")
        else:
            for o in obs:
                st.markdown(f"**{o['tipo']}** · {o['fecha']} · {o.get('usuario','-')}\n\n> {o['comentario']}")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar observaciones: {e}")

    with st.expander("➕ Añadir observación", expanded=False):
        tipo_obs = st.selectbox("Tipo", ["pedido", "factura"])
        comentario = st.text_area("Comentario")
        user = st.session_state.get("user_nombre") or st.session_state.get("user_email") or "sistema"
        if st.button("💾 Guardar observación"):
            try:
                crear_observacion(
                    pedidoid,
                    {
                        "tipo": tipo_obs,
                        "comentario": comentario.strip(),
                        "usuario": user,
                    },
                )
                st.success("✅ Observación registrada.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando observación: {e}")
