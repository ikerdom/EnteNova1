import io
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from modules.orbe_theme import apply_orbe_theme
from modules.presupuesto_api import (
    list_presupuestos,
    get_presupuesto,
    crear_presupuesto,
    actualizar_presupuesto,
    get_catalogos,
    agregar_linea,
    borrar_presupuesto,
    cliente_basico,
)
from modules.presupuesto_detalle import render_presupuesto_detalle
from modules.presupuesto_form import render_presupuesto_form
from modules.presupuesto_convert import convertir_presupuesto_a_pedido
from modules.presupuesto_pdf import generate_pdf_for_download, build_pdf_bytes, upload_pdf_to_storage, _build_data_real
from modules.presupuesto_api import _base_url
from modules.ui.page import page
from modules.ui.section import section
from modules.ui.card import card
from modules.ui.empty import empty_state


def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _render_filter_chips(items):
    active = [(k, v) for k, v in items if v]
    if not active:
        return
    chips = " ".join(
        [
            f"<span style=\"display:inline-flex;align-items:center;gap:6px;"
            f"padding:4px 10px;border-radius:999px;background:#0f172a;color:#fff;"
            f"font-size:0.78rem;\">{k}: {v}</span>"
            for k, v in active
        ]
    )
    st.markdown(chips, unsafe_allow_html=True)


def _estado_bucket(label: str):
    v = (label or "").lower()
    if any(k in v for k in ["acept", "convert"]):
        return "aceptados"
    if any(k in v for k in ["borrador", "enviad", "pend", "espera"]):
        return "espera"
    return "otros"


def _render_estado_quick_filters(estados_labels):
    buckets = {"espera": [], "aceptados": []}
    for e in estados_labels:
        b = _estado_bucket(e)
        if b in buckets:
            buckets[b].append(e)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Todos", key="pres_qf_all", use_container_width=True):
            st.session_state["pres_estado"] = "Todos"
            st.rerun()
    with c2:
        if st.button("En espera", key="pres_qf_wait", use_container_width=True):
            st.session_state["pres_estado"] = buckets["espera"][0] if buckets["espera"] else "Todos"
            st.rerun()
    with c3:
        if st.button("Aceptados", key="pres_qf_ok", use_container_width=True):
            st.session_state["pres_estado"] = buckets["aceptados"][0] if buckets["aceptados"] else "Todos"
            st.rerun()






def _emitir_pdf_presupuesto(supabase, presupuestoid: int, estados_map: dict):
    data_real = _build_data_real(supabase, presupuestoid)
    pdf_bytes, fname = build_pdf_bytes(data_real)
    try:
        url = upload_pdf_to_storage(supabase, pdf_bytes, fname, bucket="presupuestos")
    except Exception as e:
        st.error(f"Error subiendo PDF: {e}")
        return

    enviado_id = None
    for k, v in estados_map.items():
        if isinstance(v, str) and "envi" in v.lower():
            enviado_id = k
            break

    if enviado_id is None:
        st.warning("No se encontro el estado 'Enviado'.")
    else:
        try:
            actualizar_presupuesto(presupuestoid, {"estado_presupuestoid": enviado_id})
        except Exception as e:
            st.error(f"Error actualizando estado: {e}")
            return

    st.success("PDF emitido y guardado correctamente.")
    st.caption(url)

def _render_presupuesto_timeline(estado: str | None):
    steps = ["Borrador", "Enviado", "Aceptado", "Convertido"]
    est = (estado or "").lower()
    idx = 0
    if "enviad" in est:
        idx = 1
    if "acept" in est:
        idx = 2
    if "convert" in est:
        idx = 3

    items = []
    for i, s in enumerate(steps):
        if i <= idx:
            color = "#0f172a"
            bg = "#f3b340"
        else:
            color = "#64748b"
            bg = "#e2e8f0"
        items.append(
            f"<span style=\"padding:4px 10px;border-radius:999px;"
            f"background:{bg};color:{color};font-size:0.78rem;\">{s}</span>"
        )
    st.markdown(
        "<div style=\"display:flex;gap:8px;flex-wrap:wrap;\">" + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )


def _api_products():
    try:
        r = requests.get(
            f"{_base_url()}/api/productos",
            params={"page": 1, "page_size": 200, "sort_field": "nombre"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar productos: {e}")
        return []


def _render_nuevo_presupuesto_inline():
    """Constructor rapido usando API (crea cabecera + linea opcional)."""
    st.markdown("### Nuevo presupuesto")

    catalogos = get_catalogos()
    clientes = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}
    trabajadores = {c["label"]: c["id"] for c in catalogos.get("trabajadores", [])}
    productos = _api_products()

    pref_cli = st.session_state.get("pres_cli_prefill")
    pref_label = None
    if pref_cli is not None:
        pref_label = next((k for k, v in clientes.items() if v == pref_cli), None)

    with st.form("pres_new_wizard"):
        st.caption("Crea un borrador y a?ade lineas cuando quieras. El numero se genera automaticamente si no lo indicas.")

        col1, col2 = st.columns(2)
        with col1:
            cliente_opts = ["(selecciona)"] + list(clientes.keys())
            cliente_idx = cliente_opts.index(pref_label) if pref_label in cliente_opts else 0
            cliente_sel = st.selectbox("Cliente", cliente_opts, index=cliente_idx)
        with col2:
            trabajador_sel = st.selectbox("Comercial", ["(sin comercial)"] + list(trabajadores.keys()))

        col3, col4 = st.columns(2)
        with col3:
            fecha_pres = st.date_input("Fecha del presupuesto", value=date.today())
        with col4:
            fecha_validez = st.date_input("Validez hasta", value=date.today() + timedelta(days=30))

        col7, col8 = st.columns(2)
        with col7:
            ambito = st.selectbox(
                "Ambito impuesto",
                ["ES", "ES-CN", "ES-CE", "ES-ML", "EXT"],
            )
        with col8:
            st.caption("El ambito determina IVA/IGIC/IPSI.")

        st.markdown("#### Linea inicial (opcional)")
        col5, col6 = st.columns(2)
        with col5:
            producto_sel = st.selectbox(
                "Producto",
                ["(sin linea)"] + [p.get("nombre") for p in productos],
            )
        with col6:
            cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)

        crear = st.form_submit_button("Crear presupuesto", use_container_width=True)

    if not crear:
        return

    if cliente_sel == "(selecciona)":
        st.warning("Selecciona un cliente para crear el presupuesto.")
        return

    clienteid = clientes.get(cliente_sel)
    trabajadorid = trabajadores.get(trabajador_sel) if trabajador_sel != "(sin comercial)" else None
    payload = {
        "clienteid": clienteid,
        "trabajadorid": trabajadorid,
        "fecha_presupuesto": fecha_pres.isoformat(),
        "fecha_validez": fecha_validez.isoformat(),
        "ambito_impuesto": ambito,
        "observaciones": None,
        "facturar_individual": False,
    }
    try:
        pres = crear_presupuesto(payload)
        pid = pres.get("presupuestoid")

        if producto_sel != "(sin linea)" and pid:
            prod = next((p for p in productos if p.get("nombre") == producto_sel), None)
            if prod:
                try:
                    agregar_linea(
                        pid,
                        {
                            "productoid": prod.get("productoid"),
                            "cantidad": float(cantidad),
                            "descripcion": prod.get("nombre"),
                        },
                    )
                except Exception as e:
                    st.warning(f"Presupuesto creado sin linea inicial: {e}")

        st.session_state["presupuesto_modal_id"] = pid
        st.session_state["show_presupuesto_modal"] = True
        st.session_state["show_creator"] = False
        st.session_state.pop("pres_cli_prefill", None)
        st.success(f"Presupuesto creado correctamente: {pres.get('numero')}")
        st.rerun()
    except Exception as e:
        st.error(f"Error creando presupuesto: {e}")


def _render_card(r, estados_map: dict):
    cliente_label = r.get("cliente") or _safe(r.get("clienteid"))
    est_nombre = r.get("estado") or estados_map.get(r.get("estado_presupuestoid"))

    e = (est_nombre or "").lower()
    if "acept" in e:
        color_estado = "#10b981"
    elif "rechaz" in e:
        color_estado = "#ef4444"
    elif "convert" in e:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    pres_id = r.get("presupuestoid")
    numero = _safe(r.get("numero"))
    fecha = _safe(r.get("fecha_presupuesto"))
    base_imponible = r.get("base_imponible")
    iva_total = r.get("iva_total")
    total_doc = r.get("total_documento") or r.get("total_estimada")
    num_lineas = r.get("num_lineas")

    with card():
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:0.75rem;">
                  #{pres_id}
                </span>
                <div style="font-weight:700;">{numero}</div>
              </div>
              <span style="background:{color_estado};color:#fff;padding:3px 10px;border-radius:999px;font-size:0.8rem;font-weight:600;">
                {est_nombre or '-'}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"Cliente: {cliente_label} | Fecha: {fecha}")
        if num_lineas is not None:
            st.caption(f"Lineas: {num_lineas}")
        if base_imponible is not None and iva_total is not None and total_doc is not None:
            st.caption(f"Base {base_imponible} | IVA {iva_total} | Total {total_doc}")
        else:
            st.caption(f"Total: {total_doc}")

        if st.button("Ficha", key=f"pres_ficha_{pres_id}", use_container_width=True):
            st.session_state["presupuesto_modal_id"] = pres_id
            st.session_state["show_presupuesto_modal"] = True
            st.rerun()


def _render_table(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay presupuestos.")
        return
    cols = [
        "presupuestoid",
        "numero",
        "cliente",
        "clienteid",
        "estado",
        "estado_presupuestoid",
        "fecha_presupuesto",
        "fecha_validez",
        "ambito_impuesto",
        "num_lineas",
        "base_imponible",
        "iva_total",
        "total_documento",
        "total_estimada",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    buff = io.StringIO()
    df[cols].to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"presupuestos_{date.today()}.csv",
        mime="text/csv",
    )


def _render_presupuesto_modal(estados_map: dict):
    pid = st.session_state.get("presupuesto_modal_id")
    if not pid:
        return

    try:
        pres = get_presupuesto(pid)
    except Exception as e:
        empty_state(f"No se encontró el presupuesto. {e}", icon="⚠️")
        return

    est_nombre = pres.get("estado") or estados_map.get(pres.get("estado_presupuestoid"))
    est_lower = (est_nombre or "").lower()
    bloqueado = (pres.get("editable") is False) or ("acept" in est_lower) or ("convert" in est_lower)

    if "acept" in est_lower:
        color_estado = "#10b981"
    elif "rechaz" in est_lower:
        color_estado = "#ef4444"
    elif "convert" in est_lower:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    numero = pres.get("numero") or "N/A"
    base_imponible = pres.get("base_imponible")
    iva_total = pres.get("iva_total")
    total_doc = pres.get("total_documento") or pres.get("total_estimada")
    ambito = pres.get("ambito_impuesto") or "-"

    with card():
        top1, top2 = st.columns([3, 2])
        with top1:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                  <div style="font-size:1.15rem;font-weight:800;">📄 Presupuesto {numero}</div>
                  <span style="background:#111827;color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;">
                    ID #{pid}
                  </span>
                  <span style="background:{color_estado};color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:700;">
                    {est_nombre or "Sin estado"}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"📅 {_safe(pres.get('fecha_presupuesto'))} · ⏱️ Validez: {_safe(pres.get('fecha_validez'))}")

        with top2:
            colm1, colm2 = st.columns(2)
            with colm1:
                try:
                    st.metric("Total", f"{float(total_doc or 0):,.2f} €")
                except Exception:
                    st.metric("Total", _safe(total_doc))
            with colm2:
                st.metric("Ambito", _safe(ambito))

        _render_presupuesto_timeline(est_nombre)


        a1, a2, a3 = st.columns([1, 1, 1])
        with a1:
            if st.button("↩️ Volver", use_container_width=True):
                st.session_state["show_presupuesto_modal"] = False
                st.session_state["presupuesto_modal_id"] = None
                st.rerun()
        with a2:
            if st.button("🗑️ Eliminar", use_container_width=True, disabled=bloqueado):
                try:
                    borrar_presupuesto(pid)
                    st.success("✅ Presupuesto eliminado.")
                    st.session_state["show_presupuesto_modal"] = False
                    st.session_state["presupuesto_modal_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
        with a3:
            if "acept" in est_lower:
                if st.button("🔄 Convertir", use_container_width=True):
                    convertir_presupuesto_a_pedido(pid)
                    st.rerun()
            else:
                st.button("🔄 Convertir", use_container_width=True, disabled=True)

    if bloqueado:
        st.warning("🔒 Este presupuesto está Aceptado/Convertido y no se puede editar.")
    else:
        st.info("✅ Presupuesto editable.")

    tab1, tab2, tab3 = st.tabs(["Cabecera", "Lineas", "Documento PDF"])

    with tab1:
        with section("Cliente", icon="Cliente"):
            cli_id = pres.get("clienteid")
            if cli_id:
                try:
                    cli = cliente_basico(int(cli_id))
                except Exception:
                    cli = {}
            else:
                cli = {}
            if cli:
                st.write(f"Nombre: {cli.get('razonsocial') or cli.get('nombre') or '-'}")
                st.write(f"CIF/NIF: {cli.get('cifdni') or '-'}")
                st.write(f"Telefono: {cli.get('telefono') or '-'}")
            else:
                st.caption("Sin datos de cliente.")

        with section("Datos del presupuesto", icon="🧾"):
            render_presupuesto_form(presupuestoid=pid, bloqueado=bloqueado)

        if base_imponible is not None or iva_total is not None or total_doc is not None:
            with section("Totales del presupuesto", icon="Totales"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Base imponible", _safe(base_imponible))
                c2.metric("IVA/IGIC/IPSI", _safe(iva_total))
                c3.metric("Total documento", _safe(total_doc))

    with tab2:
        with section("Detalle de líneas", icon="📦"):
            render_presupuesto_detalle(pid, bloqueado=bloqueado)



    with tab3:
        with section("Documento PDF", icon="PDF"):
            supa = st.session_state.get("supa")
            if not supa:
                st.warning("No hay conexion a base de datos.")
            else:
                key = f"pres_show_pdf_{pid}"
                if st.button("Ver PDF", key=key, use_container_width=True):
                    generate_pdf_for_download(supa, pid)
                if st.button("Descargar PDF", key=f"pres_dl_pdf_{pid}", use_container_width=True):
                    try:
                        data_real = _build_data_real(supa, pid)
                        pdf_bytes, fname = build_pdf_bytes(data_real)
                        st.download_button("Descargar PDF generado", pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
                    except Exception as err:
                        st.error(f"Error generando PDF: {err}")

                colp1, colp2 = st.columns(2)
                with colp1:
                    if st.button("Emitir PDF", key=f"pres_emit_pdf_{pid}", use_container_width=True):
                        _emitir_pdf_presupuesto(supa, pid, estados_map)
                with colp2:
                    st.caption("Emite, guarda en storage y marca como Enviado.")


def render_presupuesto_lista(api_base: Optional[str] = None):
    apply_orbe_theme()

    defaults = {
        "pres_page": 1,
        "pres_view": "Tarjetas",
        "show_presupuesto_modal": False,
        "presupuesto_modal_id": None,
        "show_creator": False,
        "pres_q": "",
        "pres_estado": "Todos",
        "pres_cliente_filtro": "Todos",
        "pres_only_with_lines": False,
        "pres_orden": "Últimos creados",
        "pres_result_count": 0,
        "pres_last_fingerprint": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    catalogos = get_catalogos()
    estados_map = {c["id"]: c["label"] for c in catalogos.get("estados", [])}
    clientes_map = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}

    if st.session_state.get("show_presupuesto_modal") and st.session_state.get("presupuesto_modal_id"):
        _render_presupuesto_modal(estados_map)
        return

    with page(
        "Gestión de presupuestos",
        "Visualiza, filtra, edita y genera presupuestos.",
        icon="🧾",
    ):
        if st.button("Nuevo presupuesto", key="pres_btn_top_create", use_container_width=True):
            st.session_state["show_creator"] = True
            st.rerun()
        c1, c2 = st.columns([3, 1])
        with c1:
            q = st.text_input(
                "Buscar presupuesto",
                placeholder="Número o referencia cliente…",
                key="pres_q",
            )
        with c2:
            st.metric("Resultados (página)", st.session_state.get("pres_result_count", 0))

        _render_estado_quick_filters(list(estados_map.values()))

        with st.expander("Filtros avanzados", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                estado_sel = st.selectbox(
                    "Estado",
                    ["Todos"] + list(estados_map.values()),
                    key="pres_estado",
                )
            with f2:
                cliente_filtro = st.selectbox(
                    "Cliente",
                    ["Todos"] + list(clientes_map.keys()),
                    key="pres_cliente_filtro",
                )
            with f3:
                orden_sel = st.selectbox(
                    "Ordenar por",
                    ["Ultimos creados", "Fecha de presupuesto"],
                    key="pres_orden",
                )
            with f4:
                ambito_sel = st.selectbox(
                    "Ambito",
                    ["Todos", "ES", "ES-CN", "ES-CE", "ES-ML", "EXT"],
                    key="pres_ambito",
                )

            f5, f6, f7 = st.columns([1, 1, 1])
            with f5:
                st.radio(
                    "Vista",
                    ["Tarjetas", "Tabla"],
                    horizontal=True,
                    key="pres_view",
                )
            with f6:
                st.checkbox("Solo con lineas", key="pres_only_with_lines")
            with f7:
                if st.button("Nuevo presupuesto", use_container_width=True):
                    st.session_state["show_creator"] = True
                    st.rerun()

        _render_filter_chips([
            ("Estado", None if estado_sel == "Todos" else estado_sel),
            ("Cliente", None if cliente_filtro == "Todos" else cliente_filtro),
            ("Ambito", None if ambito_sel == "Todos" else ambito_sel),
            ("Buscar", (q or "").strip() or None),
        ])

        fingerprint = (
            (q or "").strip(),
            estado_sel,
            cliente_filtro,
            ambito_sel,
            orden_sel,
            st.session_state.get("pres_view"),
        )
        if st.session_state.get("pres_last_fingerprint") != fingerprint:
            st.session_state["pres_page"] = 1
            st.session_state["pres_last_fingerprint"] = fingerprint

        st.markdown("---")

        if st.session_state.get("show_creator"):
            with section("Nuevo presupuesto", icon="🆕"):
                _render_nuevo_presupuesto_inline()
            st.markdown("")

        total, rows = 0, []
        try:
            per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
            params = {
                "q": q or None,
                "page": st.session_state["pres_page"],
                "page_size": per_page,
                "ordenar_por": "fecha_presupuesto" if orden_sel == "Fecha de presupuesto" else "creado_en",
                "ambito_impuesto": None if ambito_sel == "Todos" else ambito_sel,
            }
            if estado_sel != "Todos":
                params["estadoid"] = next((k for k, v in estados_map.items() if v == estado_sel), None)
            if cliente_filtro != "Todos":
                params["clienteid"] = clientes_map.get(cliente_filtro)

            payload = list_presupuestos(params)
            rows = payload.get("data", [])
            total = payload.get("total", 0)
            if st.session_state.get("pres_only_with_lines"):
                rows = [r for r in rows if (r.get("num_lineas") or 0) > 0]

            st.session_state["pres_result_count"] = len(rows)
        except Exception as e:
            st.error(f"❌ Error cargando presupuestos: {e}")
            rows = []
            total = 0

        if not rows:
            empty_state("No hay presupuestos que coincidan con los filtros.", icon="🗒️")
            return

        per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
        total_pages = max(1, math.ceil((total or 0) / per_page))

        st.caption(f"Página {st.session_state['pres_page']} / {total_pages} · Total: {total}")

        p1, p2, p3 = st.columns(3)
        with p1:
            if st.button("⬅️ Anterior", disabled=st.session_state["pres_page"] <= 1):
                st.session_state["pres_page"] -= 1
                st.rerun()
        with p2:
            st.write("")
        with p3:
            if st.button("Siguiente ➡️", disabled=st.session_state["pres_page"] >= total_pages):
                st.session_state["pres_page"] += 1
                st.rerun()

        st.markdown("---")

        if st.session_state["pres_view"] == "Tarjetas":
            cols = st.columns(3)
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    _render_card(r, estados_map)
        else:
            _render_table(rows)
