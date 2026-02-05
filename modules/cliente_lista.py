from typing import Any, Dict, Optional, List


import math


import pandas as pd


import requests


import streamlit as st







from modules.orbe_theme import apply_orbe_theme
from modules.api_base import get_api_base


from modules.cliente_form_api import render_cliente_form


from modules.cliente_direccion import render_direccion_form


from modules.cliente_contacto import render_contacto_form


from modules.cliente_observacion import render_observaciones_form
from modules.cliente_albaran_form import render_albaran_form
from modules.cliente_crm import render_crm_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_documento_form import render_documento_form
from modules.pedido_api import listar as pedidos_listar
from modules.pedido_detalle import render_pedido_detalle





try:


    from streamlit_modal import Modal  # type: ignore


except Exception:


    # Fallback minimo para evitar errores si la dependencia no esta instalada


    class Modal:  # type: ignore


        def __init__(self, *args, **kwargs):


            pass





        def is_open(self):


            return True





        def open(self):


            return None





        def close(self):


            return None








def _safe(v, d: str = "-"):


    return v if v not in (None, "", "null") else d








def _normalize_id(v: Any):


    if isinstance(v, float) and v.is_integer():


        return int(v)


    return v








def _api_base() -> str:
    return get_api_base()








def _api_get(path: str, params: Optional[dict] = None) -> dict:


    try:


        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)


        r.raise_for_status()


        return r.json()


    except Exception as e:


        st.error(f"Error llamando a API: {e}")


        return {}








def render_cliente_lista(API_URL: str):
    apply_orbe_theme()

    st.header("Gestion de clientes")
    st.caption("Consulta, filtra y accede a la ficha completa de tus clientes.")

    ctop1, ctop2 = st.columns(2)
    with ctop1:
        if st.button("+ Nuevo cliente"):
            st.session_state["cli_show_form"] = "cliente"
            st.rerun()
    with ctop2:
        if st.button("+ Nuevo potencial"):
            st.session_state["cli_show_form"] = "potencial"
            st.rerun()

    modo_form = st.session_state.get("cli_show_form")
    if modo_form in ("cliente", "potencial"):
        render_cliente_form(modo=modo_form)
        return

    defaults = {
        "cli_page": 1,
        "cli_sort_field": "razonsocial",
        "cli_sort_dir": "ASC",
        "cli_view": "Tarjetas",
        "cli_result_count": 0,
        "cli_table_cols": ["razonsocial", "nombre", "cifdni"],
        "cli_page_size": 30,
        "cli_compact": st.session_state.get("pref_compact", True),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    cli_catalogos = _api_get("/api/clientes/catalogos")
    grupos = {c["label"]: c["id"] for c in cli_catalogos.get("grupos", [])}

    c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1, 1, 1])
    with c1:
        q = st.text_input(
            "Buscar cliente",
            placeholder="Razon social o CIF/DNI",
            key="cli_q",
        )
        if st.session_state.get("last_q") != q:
            st.session_state["cli_page"] = 1
            st.session_state["last_q"] = q
    with c2:
        st.session_state["cli_view"] = st.selectbox(
            "Vista",
            ["Tarjetas", "Tabla"],
            index=["Tarjetas", "Tabla"].index(st.session_state.get("cli_view", "Tarjetas")),
        )
    with c3:
        st.session_state["cli_page_size"] = st.selectbox(
            "Por pagina",
            options=[15, 30, 50, 100],
            index=[15, 30, 50, 100].index(st.session_state.get("cli_page_size", 30)),
        )
    with c4:
        st.metric("Resultados", st.session_state["cli_result_count"])
    with c5:
        if st.button("Limpiar filtros"):
            st.session_state["cli_q"] = ""
            st.session_state["cli_tipo_filtro"] = "Todos"
            st.session_state["cli_grupo_filtro"] = "Todos"
            st.session_state["cli_page"] = 1
            st.rerun()

    st.markdown("---")

    sel = st.session_state.get("cliente_detalle_id")
    if sel:
        _render_ficha_panel(sel)
        st.markdown("---")
        st.subheader("Catálogo de clientes")

    # Filtros rápidos
    quick1, quick2, quick3, quick4 = st.columns(4)
    with quick1:
        if st.button("Todos", use_container_width=True):
            st.session_state["cli_tipo_filtro"] = "Todos"
            st.session_state["cli_page"] = 1
            st.rerun()
    with quick2:
        if st.button("Clientes", use_container_width=True):
            st.session_state["cli_tipo_filtro"] = "CLIENTE"
            st.session_state["cli_page"] = 1
            st.rerun()
    with quick3:
        if st.button("Proveedores", use_container_width=True):
            st.session_state["cli_tipo_filtro"] = "PROVEEDOR"
            st.session_state["cli_page"] = 1
            st.rerun()
    with quick4:
        if st.button("Ambos", use_container_width=True):
            st.session_state["cli_tipo_filtro"] = "AMBOS"
            st.session_state["cli_page"] = 1
            st.rerun()

    with st.expander("Filtros avanzados", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            st.session_state["cli_tipo_filtro"] = st.selectbox(
                "Tipo cliente/proveedor",
                ["Todos", "CLIENTE", "PROVEEDOR", "AMBOS"],
            )
        with f2:
            grupo_labels = ["Todos"] + list(grupos.keys())
            st.session_state["cli_grupo_filtro"] = st.selectbox("Grupo", grupo_labels)
        with f3:
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar por",
                ["razonsocial", "nombre", "cifdni", "codigocuenta", "codigoclienteoproveedor"],
            )
            st.session_state["cli_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
            )

        if st.session_state["cli_view"] == "Tabla":
            all_cols = [
                "razonsocial",
                "nombre",
                "cifdni",
                "codigocuenta",
                "codigoclienteoproveedor",
                "clienteoproveedor",
                "idgrupo",
            ]
            st.session_state["cli_table_cols"] = st.multiselect(
                "Columnas a mostrar",
                options=all_cols,
                default=st.session_state.get("cli_table_cols", defaults["cli_table_cols"]),
            )
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar tabla por",
                options=st.session_state["cli_table_cols"] or all_cols,
                key="cli_sort_field_table",
            )
            st.session_state["cli_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
                key="cli_sort_dir_table",
            )

    page = st.session_state["cli_page"]
    page_size = st.session_state.get("cli_page_size", 30)

    params = {
        "q": q or None,
        "page": page,
        "page_size": page_size,
        "sort_field": st.session_state["cli_sort_field"],
        "sort_dir": st.session_state["cli_sort_dir"],
    }

    tipo_filtro = st.session_state.get("cli_tipo_filtro", "Todos")
    if tipo_filtro != "Todos":
        params["tipo"] = tipo_filtro
    grupo_filtro = st.session_state.get("cli_grupo_filtro", "Todos")
    if grupo_filtro != "Todos":
        params["idgrupo"] = grupos.get(grupo_filtro)

    payload = _api_get("/api/clientes", params=params)
    clientes: List[Dict[str, Any]] = payload.get("data", [])
    total = payload.get("total", 0)
    total_pages = payload.get("total_pages", 1)
    st.session_state["cli_result_count"] = len(clientes)

    if not clientes:
        st.info("No se encontraron clientes.")
        return

    if st.session_state["cli_view"] == "Tabla":
        cols_sel = st.session_state.get("cli_table_cols") or defaults["cli_table_cols"]
        rows = []
        for c in clientes:
            row = {col: c.get(col) for col in cols_sel}
            rows.append(row)
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "razonsocial": st.column_config.TextColumn("Razon social"),
                "nombre": st.column_config.TextColumn("Nombre"),
                "cifdni": st.column_config.TextColumn("CIF/DNI"),
                "codigocuenta": st.column_config.TextColumn("Cuenta"),
                "codigoclienteoproveedor": st.column_config.TextColumn("Codigo C/P"),
                "clienteoproveedor": st.column_config.TextColumn("Tipo"),
                "idgrupo": st.column_config.TextColumn("Grupo"),
            },
        )
        opciones = [
            (f"{c.get('razonsocial') or c.get('nombre') or 'Cliente'}", c.get("clienteid"))
            for c in clientes
            if c.get("clienteid") is not None
        ]
        if opciones:
            label_map = {label: cid for label, cid in opciones}
            elegido = st.selectbox("Ficha de cliente", options=list(label_map.keys()))
            if st.button("🔍", key="cli_table_open", use_container_width=True):
                st.session_state["cliente_detalle_id"] = label_map[elegido]
                st.rerun()
    else:
        cols = st.columns(3)
        for i, c in enumerate(clientes):
            with cols[i % 3]:
                _render_card(c)

    st.markdown("---")
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1):
            st.session_state["cli_page"] = page - 1
            st.rerun()
    with p2:
        st.write(f"Pagina {page} / {max(1, total_pages)} - Total: {total}")
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages):
            st.session_state["cli_page"] = page + 1
            st.rerun()


def _render_card(c: Dict[str, Any]):
    razon = _safe(c.get("razonsocial") or c.get("nombre"))
    ident = _safe(c.get("cifdni"))
    grupo = c.get("idgrupo", "-")
    tipo = c.get("clienteoproveedor") or "-"
    codcta = _safe(c.get("codigocuenta"))
    codcp = _safe(c.get("codigoclienteoproveedor"))
    compact = st.session_state.get("cli_compact", False)
    min_h = "92px" if compact else "118px"
    clamp = "1" if compact else "2"
    pad = "10px" if compact else "12px"
    sub_fs = "0.8rem" if compact else "0.86rem"

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:{pad};margin-bottom:10px;
                    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05);min-height:{min_h};">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;line-height:1.1;display:-webkit-box;-webkit-line-clamp:{clamp};-webkit-box-orient:vertical;overflow:hidden;">
                        {razon}
                    </div>
                    <div style="color:#6b7280;font-size:{sub_fs};margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {ident} · Cuenta {codcta} · Código {codcp}
                    </div>
                </div>
                <div style="text-align:right;min-width:90px;">
                    <span style="display:inline-block;padding:2px 8px;border-radius:999px;background:#e2e8f0;color:#0f172a;font-size:0.82rem;font-weight:600;">
                        {tipo}
                    </span><br>
                    <span style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:999px;background:#ecfdf5;color:#166534;font-size:0.82rem;font-weight:600;">
                        Grupo {grupo}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cid = c.get("clienteid")
    contact_line = _safe(c.get("telefono") or c.get("movil"), "")
    if contact_line:
        st.caption(f"Contacto: {contact_line}")
    if st.button("🔍", key=f"cli_ficha_{cid}", use_container_width=True):
        st.session_state["cliente_detalle_id"] = cid
        st.rerun()


def _render_ficha_panel(clienteid: int):
    top1, top2, top3 = st.columns([2, 1, 1])
    with top1:
        if st.button("Crear presupuesto para este cliente", key=f"cli_pres_{clienteid}", use_container_width=True):
            st.session_state["pres_cli_prefill"] = int(clienteid)
            st.session_state["show_creator"] = True
            st.session_state["menu_principal"] = "💼 Gestion de presupuestos"
            st.rerun()
    with top2:
        if st.button("Editar cliente", key=f"cli_edit_top_{clienteid}", use_container_width=True):
            st.session_state["cli_show_form"] = "cliente"
            st.session_state["cliente_actual"] = clienteid
            st.rerun()
    with top3:
        if st.button("Cerrar ficha", key=f"cerrar_cli_top_{clienteid}", use_container_width=True):
            st.session_state["cliente_detalle_id"] = None
            st.rerun()

    with st.container(border=True):
        c1, _ = st.columns([4, 1])
        with c1:
            st.subheader(f"Ficha cliente {clienteid}")

        base = _api_base()
        try:
            res = requests.get(f"{base}/api/clientes/{clienteid}", timeout=15)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            st.error(f"Error cargando ficha: {e}")
            if st.button("Cerrar", key=f"cerrar_cli_err_{clienteid}"):
                st.session_state["cliente_detalle_id"] = None
                st.rerun()
            return

        cli = data.get("cliente", {})
        direcciones = data.get("direcciones") or []
        contactos = data.get("contactos") or []
        cp = data.get("contacto_principal") or (contactos[0] if contactos else {})
        df = direcciones[0] if direcciones else {}

        tabs = st.tabs(
            [
                "Resumen",
                "Direcciones",
                "Contactos",
                "Observaciones",
                "Facturación",
                "Documentos",
                "Albaranes",
                "Pedidos",
                "CRM",
                "Historial",
            ]
        )
        with tabs[0]:
            tipo = cli.get("clienteoproveedor") or "-"
            grupo = cli.get("idgrupo") or "-"
            razon = cli.get("razonsocial") or cli.get("nombre") or "-"

            top_l, top_r = st.columns([3, 1])
            with top_l:
                st.markdown(f"### {razon}")
            with top_r:
                st.markdown(
                    f"""<div style="text-align:right;">
<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:#e2e8f0;color:#0f172a;font-size:0.82rem;font-weight:600;">{tipo}</span><br>
<span style="display:inline-block;margin-top:6px;padding:4px 10px;border-radius:999px;background:#ecfdf5;color:#166534;font-size:0.82rem;font-weight:600;">Grupo {grupo}</span>
</div>""",
                    unsafe_allow_html=True,
                )

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("CIF/DNI", cli.get("cifdni") or "-")
            kpi2.metric("Cuenta", cli.get("codigocuenta") or "-")
            kpi3.metric("Código C/P", cli.get("codigoclienteoproveedor") or "-")

            st.markdown("### Datos principales")
            left, right = st.columns(2)
            with left:
                _render_kv_block(
                    [
                        ("Razón social", cli.get("razonsocial") or cli.get("nombre")),
                        ("Nombre comercial", cli.get("nombre")),
                        ("Email", cli.get("email") or cli.get("correoelectronico")),
                        ("Teléfono", cli.get("telefono") or cli.get("movil")),
                    ]
                )
            with right:
                _render_kv_block(
                    [
                        ("Tipo", tipo),
                        ("Grupo", grupo),
                        ("Web", cli.get("web")),
                        ("Fecha alta", cli.get("fechaalta") or cli.get("fecha_alta")),
                    ]
                )

            st.markdown("### Dirección y contacto")
            d1, d2 = st.columns(2)
            with d1:
                with st.container(border=True):
                    st.markdown("**Dirección principal**")
                    _render_dir_summary(df)
            with d2:
                with st.container(border=True):
                    st.markdown("**Contacto principal**")
                    _render_contact_summary(cp)

        with tabs[1]:
            render_direccion_form(clienteid, key_prefix="panel_")
        with tabs[2]:
            render_contacto_form(clienteid, key_prefix="panel_")
        with tabs[3]:
            render_observaciones_form(clienteid, key_prefix="panel_")
        with tabs[4]:
            render_facturacion_form(None, int(clienteid))
        with tabs[5]:
            render_documento_form(None, int(clienteid))
        with tabs[6]:
            render_albaran_form(None, int(clienteid))
        with tabs[7]:
            _render_pedidos_tab(int(clienteid))
        with tabs[8]:
            render_crm_form(int(clienteid))
        with tabs[9]:
            st.info("Historial disponible en próxima fase (modo API).")



def _render_dir_summary(df: dict):
    if not df:
        st.info("Sin direccion")
        return
    direccion = df.get('direccion') or df.get('direccionfiscal') or '-'
    cp = df.get('codigopostal') or '-'
    municipio = df.get('municipio') or '-'
    provincia = df.get('idprovincia') or '-'
    pais = df.get('idpais') or '-'
    st.markdown(
        f"""
        **{direccion}**

        {cp} {municipio} ({provincia}) - {pais}
        """,
    )


def _render_kv_block(items: List[tuple]):
    for label, value in items:
        v = value if value not in (None, "", "null") else "-"
        st.markdown(f"**{label}:** {v}")


def _render_contact_summary(cp: dict):
    if not cp:
        st.info("Sin contacto")
        return
    _render_kv_block(
        [
            ("Nombre", cp.get("nombre") or cp.get("razonsocial")),
            ("Cargo", cp.get("cargo")),
            ("Email", cp.get("email") or cp.get("correoelectronico")),
            ("Teléfono", cp.get("telefono") or cp.get("movil")),
        ]
    )


def _render_pedidos_tab(clienteid: int):
    st.markdown("### Pedidos del cliente")
    try:
        payload = pedidos_listar({"clienteid": clienteid, "page": 1, "page_size": 50})
        pedidos = payload.get("data") or []
    except Exception as e:
        st.error(f"Error cargando pedidos: {e}")
        return

    if not pedidos:
        st.info("Este cliente todavía no tiene pedidos.")
        return

    rows = []
    for p in pedidos:
        rows.append(
            {
                "pedido_id": p.get("pedido_id"),
                "fecha_pedido": p.get("fecha_pedido"),
                "estado": p.get("pedido_estado_nombre") or p.get("pedido_estadoid"),
                "referencia": p.get("referencia_cliente"),
                "total": p.get("total"),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "pedido_id": st.column_config.NumberColumn("Pedido", format="%d"),
            "fecha_pedido": st.column_config.DatetimeColumn("Fecha"),
            "estado": st.column_config.TextColumn("Estado"),
            "referencia": st.column_config.TextColumn("Referencia"),
            "total": st.column_config.NumberColumn("Total", format="%.2f"),
        },
    )

    ids = [p.get("pedido_id") for p in pedidos if p.get("pedido_id")]
    if not ids:
        return
    sel = st.selectbox(
        "Ver detalle de pedido",
        options=["-"] + [str(i) for i in ids],
        index=0,
    )
    if sel != "-":
        render_pedido_detalle(None, int(sel))

