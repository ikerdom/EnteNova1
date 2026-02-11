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


def _truncate(text: str, max_len: int = 32) -> str:
    if not text:
        return "-"
    txt = str(text)
    return (txt[: max_len - 1] + "...") if len(txt) > max_len else txt


def _ensure_icon_css():
    if st.session_state.get("icon_btn_css_loaded"):
        return
    st.session_state["icon_btn_css_loaded"] = True
    st.markdown(
        """
        <style>
        .card-actions {
            display: flex;
            justify-content: flex-end;
            margin-top: -34px;
            margin-bottom: 6px;
        }
        .icon-btn button {
            border-radius: 999px !important;
            width: 36px !important;
            height: 36px !important;
            padding: 0 !important;
            min-height: 36px !important;
        }
        .icon-btn button p { margin: 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_filter_buttons(items):
    active = [(k, v, fn) for k, v, fn in items if v]
    if not active:
        return
    cols = st.columns(min(4, len(active)))
    for i, (label, value, fn) in enumerate(active):
        col = cols[i % len(cols)]
        if col.button(f"✕ {label}: {value}", key=f"ped_chip_{i}_{label}"):
            fn()
            st.rerun()


def _clear_pedido_filters():
    st.session_state["pedido_q"] = ""
    st.session_state["pedido_estado"] = "Todos"
    st.session_state["pedido_pago"] = "Todas"
    st.session_state["pedido_cliente"] = "Todos"
    st.session_state["pedido_procedencia"] = ""
    st.session_state["pedido_ref"] = ""
    st.session_state["pedido_cif"] = ""
    st.session_state["pedido_total_min"] = None
    st.session_state["pedido_total_max"] = None
    st.session_state["pedido_tipodoc"] = ""
    st.session_state["pedido_tipo_docid"] = None
    st.session_state["pedido_estado_nombre"] = ""
    st.session_state["pedido_comp_from"] = None
    st.session_state["pedido_comp_to"] = None
    st.session_state["pedido_from"] = None
    st.session_state["pedido_to"] = None
    st.session_state["pedido_page"] = 1


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


def _abrir_edicion(pedido_id: int):
    st.session_state["pedido_editar_id"] = pedido_id
    st.session_state["pedido_show_form"] = True
    st.session_state["show_pedido_modal"] = False
    st.rerun()


def render_pedido_lista(_supabase=None):
    _ensure_icon_css()
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
        "pedido_compact": st.session_state.get("pref_compact", True),
        "pedido_edit_open": False,
        "pedido_cliente": "Todos",
        "pedido_procedencia": "Todas",
        "pedido_ref": "",
        "pedido_cif": "",
        "pedido_total_min": None,
        "pedido_total_max": None,
        "pedido_tipodoc": "",
        "pedido_tipo_docid": None,
        "pedido_estado_nombre": "",
        "pedido_comp_from": None,
        "pedido_comp_to": None,
    }
    for k, v in defaults.items():
        session.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    try:
        cats = catalogos()
        clientes_map = {c["label"]: c["id"] for c in cats.get("clientes", [])}
        clientes_rev = {c["id"]: c["label"] for c in cats.get("clientes", [])}
        estados_map = {e["label"]: e["id"] for e in cats.get("estados", [])}
        estados_rev = {v: k for k, v in estados_map.items()}
        formas_pago_map = {f["label"]: f["id"] for f in cats.get("formas_pago", [])}
        formas_pago_rev = {f["id"]: f["label"] for f in cats.get("formas_pago", [])}
    except Exception:
        clientes_map = {}
        clientes_rev = {}
        estados_map = {}
        estados_rev = {}
        formas_pago_map = {}
        formas_pago_rev = {}

    if session.get("pedido_show_form"):
        st.markdown("### Editor de pedido (cabecera)")
        try:
            render_pedido_form(None, pedidoid=session.get("pedido_editar_id"), on_saved_rerun=True)
        except Exception as e:
            st.error(f"Error abriendo formulario: {e}")
        st.markdown("---")

    colf1, colf2, colf3, colf4, colf5 = st.columns([3, 2, 2, 2, 1])
    with colf1:
        q = st.text_input("🔍 Buscar (id / referencia / cliente)", key="pedido_q")
    with colf2:
        cliente_sel = st.selectbox("Cliente", ["Todos"] + list(clientes_map.keys()), key="pedido_cliente")
    with colf3:
        estado_sel = st.selectbox("Estado", ["Todos"] + list(estados_map.keys()), key="pedido_estado")
    with colf4:
        forma_sel = st.selectbox("Forma de pago", ["Todas"] + list(formas_pago_map.keys()), key="pedido_pago")
    with colf5:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="pedido_view")

    colf6, colf7, colf8, colf9 = st.columns([2, 2, 2, 1])
    with colf6:
        fecha_desde = st.date_input("Desde", value=st.session_state.get("pedido_from"), key="pedido_from")
    with colf7:
        fecha_hasta = st.date_input("Hasta", value=st.session_state.get("pedido_to"), key="pedido_to")
    with colf8:
        procedencia = st.text_input("Procedencia", key="pedido_procedencia")
    with colf9:
        st.button("Limpiar filtros", on_click=_clear_pedido_filters, use_container_width=True)

    with st.expander("Filtros avanzados", expanded=False):
        total_min_val = float(st.session_state.get("pedido_total_min") or 0.0)
        total_max_val = float(st.session_state.get("pedido_total_max") or 0.0)
        a1, a2, a3, a4 = st.columns([2, 2, 2, 2])
        with a1:
            ref_cli = st.text_input("Referencia cliente", key="pedido_ref")
        with a2:
            cif_cli = st.text_input("CIF cliente", key="pedido_cif")
        with a3:
            total_min = st.number_input("Total mínimo", min_value=0.0, value=total_min_val, step=1.0, key="pedido_total_min")
        with a4:
            total_max = st.number_input("Total máximo", min_value=0.0, value=total_max_val, step=1.0, key="pedido_total_max")

        b1, b2, b3, b4 = st.columns([2, 2, 2, 2])
        with b1:
            estado_nombre = st.text_input("Estado (texto)", key="pedido_estado_nombre")
        with b2:
            tipodoc = st.text_input("Tipo doc", key="pedido_tipodoc")
        with b3:
            tipo_docid = st.number_input("Tipo doc ID", min_value=0, value=0, step=1, key="pedido_tipo_docid")
        with b4:
            comp_from = st.date_input("Completado desde", value=st.session_state.get("pedido_comp_from"), key="pedido_comp_from")

        c1, c2 = st.columns(2)
        with c1:
            comp_to = st.date_input("Completado hasta", value=st.session_state.get("pedido_comp_to"), key="pedido_comp_to")
        with c2:
            st.caption("Filtra por fecha de completado cuando exista.")

    _render_filter_buttons([
        ("Cliente", None if cliente_sel == "Todos" else cliente_sel, lambda: st.session_state.update({"pedido_cliente": "Todos"})),
        ("Estado", None if estado_sel == "Todos" else estado_sel, lambda: st.session_state.update({"pedido_estado": "Todos"})),
        ("Forma", None if forma_sel == "Todas" else forma_sel, lambda: st.session_state.update({"pedido_pago": "Todas"})),
        ("Procedencia", procedencia or None, lambda: st.session_state.update({"pedido_procedencia": ""})),
        ("Referencia", ref_cli or None, lambda: st.session_state.update({"pedido_ref": ""})),
        ("CIF", cif_cli or None, lambda: st.session_state.update({"pedido_cif": ""})),
        ("Estado texto", estado_nombre or None, lambda: st.session_state.update({"pedido_estado_nombre": ""})),
        ("Tipo doc", tipodoc or None, lambda: st.session_state.update({"pedido_tipodoc": ""})),
        ("Tipo doc ID", str(tipo_docid) if tipo_docid else None, lambda: st.session_state.update({"pedido_tipo_docid": None})),
        ("Total ≥", f"{total_min:.2f}" if total_min and total_min > 0 else None, lambda: st.session_state.update({"pedido_total_min": None})),
        ("Total ≤", f"{total_max:.2f}" if total_max and total_max > 0 else None, lambda: st.session_state.update({"pedido_total_max": None})),
        ("Desde", fecha_desde.isoformat() if fecha_desde else None, lambda: st.session_state.update({"pedido_from": None})),
        ("Hasta", fecha_hasta.isoformat() if fecha_hasta else None, lambda: st.session_state.update({"pedido_to": None})),
        ("Comp. desde", comp_from.isoformat() if comp_from else None, lambda: st.session_state.update({"pedido_comp_from": None})),
        ("Comp. hasta", comp_to.isoformat() if comp_to else None, lambda: st.session_state.update({"pedido_comp_to": None})),
        ("Buscar", (q or "").strip() or None, lambda: st.session_state.update({"pedido_q": ""})),
    ])

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
            "clienteid": clientes_map.get(cliente_sel) if cliente_sel != "Todos" else None,
            "estadoid": estados_map.get(estado_sel) if estado_sel != "Todos" else None,
            "forma_pagoid": formas_pago_map.get(forma_sel) if forma_sel != "Todas" else None,
            "pedido_procedencia": procedencia or None,
            "pedido_estado_nombre": estado_nombre or None,
            "tipodoc": tipodoc or None,
            "pedido_tipo_documentoid": int(tipo_docid) if tipo_docid else None,
            "referencia_cliente": ref_cli or None,
            "cif_cliente": cif_cli or None,
            "total_min": float(total_min) if total_min and total_min > 0 else None,
            "total_max": float(total_max) if total_max and total_max > 0 else None,
            "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
            "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
            "fecha_completado_desde": comp_from.isoformat() if comp_from else None,
            "fecha_completado_hasta": comp_to.isoformat() if comp_to else None,
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

    if session.get("show_pedido_modal"):
        _render_pedido_modal(
            session.get("pedido_modal_id"),
            estados_rev,
            clientes_rev,
            formas_pago_rev,
        )
        st.markdown("---")

    if view == "Tarjetas":
        cols = st.columns(3)
        for idx, p in enumerate(pedidos):
            with cols[idx % 3]:
                _render_pedido_card(p, estados_rev, clientes_rev)
    else:
        _render_table(pedidos, estados_rev)


def _render_table(pedidos: list[dict], estados_rev: dict):
    rows = []
    for p in pedidos:
        rows.append(
            {
                "ID": p.get("pedido_id"),
                "Cliente": p.get("cliente") or p.get("clienteid"),
                "Estado": estados_rev.get(p.get("pedido_estadoid")) or p.get("pedido_estado_nombre") or "-",
                "Fecha": p.get("fecha_pedido"),
                "Referencia": p.get("referencia_cliente"),
                "Total": p.get("total"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_pedido_card(p, estados_rev, clientes_rev):
    cliente_nombre = p.get("cliente") or clientes_rev.get(p.get("clienteid")) or "-"
    estado_nombre = estados_rev.get(p.get("pedido_estadoid")) or p.get("pedido_estado_nombre")
    color_estado = _color_estado(estado_nombre)
    estado_lower = (estado_nombre or "").lower()
    editable = ("borr" in estado_lower) or ("pend" in estado_lower)
    compact = st.session_state.get("pedido_compact", False)
    min_h = "100px" if compact else "120px"
    clamp = "1" if compact else "2"

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;
                    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05);min-height:{min_h};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="max-width:80%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    <b>#{_safe(p.get('pedido_id'))}</b> · {_safe(_truncate(cliente_nombre, 28 if compact else 32))}
                </div>
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

    colA, colB, colC = st.columns(3)
    st.markdown('<div class="card-actions"><div class="icon-btn">', unsafe_allow_html=True)
    if st.button("🔍", key=f"detalle_{p['pedido_id']}"):
        st.session_state["pedido_modal_id"] = p["pedido_id"]
        st.session_state["show_pedido_modal"] = True
        st.session_state["pedido_show_form"] = False
        st.session_state["pedido_edit_open"] = False
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


def _render_pedido_modal(
    pedido_id: int,
    estados_rev: dict,
    clientes_rev: dict,
    formas_pago_rev: dict,
):
    if not pedido_id:
        return

    st.markdown("---")
    st.markdown("### 📄 Detalle del pedido")

    try:
        p = detalle(pedido_id)
    except Exception as e:
        st.error(f"❌ Error cargando pedido: {e}")
        return

    estado_lbl = estados_rev.get(p.get("pedido_estadoid")) or p.get("pedido_estado_nombre") or "-"
    cliente_lbl = p.get("cliente") or clientes_rev.get(p.get("clienteid")) or "-"
    forma_lbl = formas_pago_rev.get(p.get("forma_pagoid")) or "-"
    color_estado = _color_estado(estado_lbl)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        if st.button("↩️ Cerrar detalle", use_container_width=True):
            st.session_state["show_pedido_modal"] = False
            st.session_state["pedido_modal_id"] = None
            st.rerun()
    with c2:
        if st.button("✏️ Editar", use_container_width=True, disabled=not editable):
            st.session_state["pedido_edit_open"] = True
            st.rerun()
    with c3:
        st.button("🗑️ Eliminar", use_container_width=True, disabled=True)

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
            st.text(f"Forma de pago: {_safe(forma_lbl)}")
        with col3:
            st.text(f"Procedencia: {_safe(p.get('pedido_procedencia'))}")
            st.text(f"Ref. cliente: {_safe(p.get('referencia_cliente'))}")

    st.markdown("---")
    if st.session_state.get("pedido_edit_open"):
        st.subheader("✏️ Cabecera del pedido")
        try:
            render_pedido_form(None, pedidoid=pedido_id, on_saved_rerun=True)
        except Exception as e:
            st.error(f"❌ Error al abrir el formulario de cabecera: {e}")
    else:
        st.caption("Edición disponible en el detalle (botón Editar).")

    st.markdown("---")
    st.subheader("📦 Líneas del pedido")
    try:
        lineas_data = lineas(pedido_id)
    except Exception as e:
        st.error(f"❌ Error cargando líneas: {e}")
        lineas_data = []

    if not lineas_data:
        st.info("ℹ️ No hay líneas registradas para este pedido.")
    else:
        df = pd.DataFrame(lineas_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("➕ Añadir línea", expanded=False):
        with st.form(f"form_add_linea_{pedido_id}"):
            producto_id = st.number_input("ID producto (opcional)", min_value=0, value=0, step=1)
            nombre_prod = st.text_input("Descripción / nombre del producto")
            cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0)
            precio = st.number_input("Precio unitario", min_value=0.0, value=0.0, step=0.01)
            desc_manual = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            add_ok = st.form_submit_button("💾 Añadir línea", use_container_width=True)

        if add_ok:
            try:
                payload = {
                    "producto_id": int(producto_id) if producto_id else None,
                    "nombre_producto": nombre_prod.strip() or None,
                    "cantidad": float(cantidad),
                    "precio": float(precio),
                    "descuento_pct": float(desc_manual),
                }
                agregar_linea(pedido_id, payload)
                st.success("✅ Línea añadida.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error añadiendo línea: {e}")

    if lineas_data:
        with st.expander("🗑️ Eliminar línea", expanded=False):
            opciones = {f"{l.get('pedido_linea_id')} · {l.get('nombre_producto')}": l.get("pedido_linea_id") for l in lineas_data}
            sel = st.selectbox("Selecciona línea a eliminar", list(opciones.keys()))
            if st.button("Eliminar línea seleccionada"):
                try:
                    borrar_linea(pedido_id, opciones[sel])
                    st.success("🗑️ Línea eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando línea: {e}")

    st.markdown("---")
    st.subheader("💰 Totales del pedido")
    try:
        tot = totales(pedido_id)
    except Exception:
        tot = None

    colT1, colT2, colT3, colT4, colT5 = st.columns(5)
    if tot:
        colT1.metric("Base imponible", _money(tot.get("total_base_imponible")))
        colT2.metric("Impuestos", _money(tot.get("total_impuestos")))
        colT3.metric("Recargos", _money(tot.get("total_recargos")))
        colT4.metric("Gastos envío", _money(tot.get("total_base_gastos_envios")))
        colT5.metric("Total", _money(tot.get("total")))
    else:
        st.warning("⚠️ No hay totales calculados aún para este pedido.")

    with st.expander("🔄 Recalcular totales", expanded=False):
        st.caption("Recalcula los importes usando las líneas del pedido.")

        use_iva = st.checkbox("Aplicar IVA (según líneas)", value=True)
        gastos = st.number_input("Gastos de envío (€)", min_value=0.0, value=0.0, step=0.01)
        envio_sin_cargo = st.checkbox("Envío sin cargo", value=False)

        if st.button("🔄 Recalcular ahora"):
            try:
                recalc = recalcular_totales(
                    pedido_id,
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
        obs = observaciones(pedido_id)
        if not obs:
            st.info("No hay observaciones registradas.")
        else:
            for o in obs:
                st.markdown(f"**{o.get('tipo','pedido')}** · {_safe(o.get('fecha'))} · {_safe(o.get('usuario'))}\n\n> {_safe(o.get('comentario'))}")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar observaciones: {e}")

    with st.expander("➕ Añadir observación", expanded=False):
        tipo_obs = st.selectbox("Tipo", ["pedido", "logistica"])
        comentario = st.text_area("Comentario")
        user = st.session_state.get("user_nombre") or st.session_state.get("user_email") or "sistema"
        if st.button("💾 Guardar observación"):
            try:
                crear_observacion(
                    pedido_id,
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
