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








def _normalize_id(v: Any):


    if isinstance(v, float) and v.is_integer():


        return int(v)


    return v








def _api_base() -> str:
    return get_api_base()








def _api_get(path: str, params: Optional[dict] = None, show_error: bool = True) -> dict:


    try:


        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)


        r.raise_for_status()


        return r.json()


    except Exception as e:


        if show_error:
            st.error(f"Error llamando a API: {e}")


        return {}


@st.cache_data(ttl=60)
def _api_get_cached(path: str, params: Optional[dict] = None) -> dict:
    return _api_get(path, params=params, show_error=False)


def _clear_filters():
    st.session_state["cli_q"] = ""
    st.session_state["cli_grupo_filtro"] = "Todos"
    st.session_state["cli_page"] = 1
    st.session_state["cli_f_razon"] = ""
    st.session_state["cli_f_nombre"] = ""
    st.session_state["cli_f_cif"] = ""
    st.session_state["cli_f_codcta"] = ""
    st.session_state["cli_f_codcp"] = ""


def _compare_add(cid: Any, label: str, cif: str):
    items = st.session_state.setdefault("cli_compare", [])
    if any(i["id"] == cid for i in items):
        return
    if len(items) >= 3:
        st.session_state["cli_compare_full"] = True
        return
    items.append({"id": cid, "label": label, "cif": cif})
    st.session_state["cli_compare"] = items
    st.session_state["cli_compare_last"] = label
    if len(items) >= 2:
        st.session_state["cli_compare_mode"] = True
        st.session_state["cliente_detalle_id"] = items[0]["id"]
        st.rerun()


def _compare_remove(cid: Any):
    items = st.session_state.get("cli_compare", [])
    st.session_state["cli_compare"] = [i for i in items if i["id"] != cid]


def _on_filter_change():
    st.session_state["cli_page"] = 1


@st.cache_data(ttl=120)
def _fetch_cliente_detalle_cached(clienteid: int) -> dict:
    base = _api_base()
    try:
        res = requests.get(f"{base}/api/clientes/{clienteid}", timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"_error": str(e)}


def _fetch_cliente_detalle(clienteid: int) -> dict:
    return _fetch_cliente_detalle_cached(clienteid)


def _render_compact_cliente(clienteid: int, label: str):
    data = _fetch_cliente_detalle(clienteid)
    if data.get("_error"):
        st.error(f"Error cargando detalle: {data['_error']}")
        return
    cli = data.get("cliente", {})
    tipo = cli.get("clienteoproveedor") or "-"
    grupo = cli.get("idgrupo") or "-"
    razon = cli.get("razonsocial") or cli.get("nombre") or label
    with st.container(border=True):
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


def _render_compare_card(data: dict, title: str):
    cli = data.get("cliente", {})
    contactos = data.get("contactos") or []
    direcciones = data.get("direcciones") or []
    cp = data.get("contacto_principal") or (contactos[0] if contactos else {})
    df = direcciones[0] if direcciones else {}
    tipo = cli.get("clienteoproveedor") or "-"
    grupo = cli.get("idgrupo") or "-"
    razon = cli.get("razonsocial") or cli.get("nombre") or title
    with st.container(border=True):
        top_l, top_r = st.columns([3, 1])
        with top_l:
            st.markdown(f"### {razon}")
            st.caption(title)
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
        left, right = st.columns(2)
        with left:
            _render_kv_block(
                [
                    ("Razón social", cli.get("razonsocial") or cli.get("nombre")),
                    ("Nombre comercial", cli.get("nombre")),
                    ("Email", cli.get("email") or cli.get("correoelectronico")),
                ]
            )
        with right:
            _render_kv_block(
                [
                    ("Teléfono", cli.get("telefono") or cli.get("movil")),
                    ("Provincia", cli.get("provincia") or cli.get("idprovincia")),
                    ("Municipio", cli.get("municipio") or cli.get("idmunicipio")),
                ]
            )
        st.markdown("**Contacto y dirección**")
        c1, c2 = st.columns(2)
        with c1:
            _render_kv_block(
                [
                    ("Contacto", cp.get("nombre") or cp.get("razonsocial")),
                    ("Cargo", cp.get("cargo")),
                    ("Email", cp.get("email") or cp.get("correoelectronico")),
                    ("Teléfono", cp.get("telefono") or cp.get("movil") or cp.get("valor")),
                ]
            )
        with c2:
            _render_kv_block(
                [
                    ("Dirección", df.get("direccion") or df.get("direccionfiscal")),
                    ("CP", df.get("codigopostal")),
                    ("Municipio", df.get("municipio") or df.get("rci_poblacion")),
                    ("Provincia", df.get("idprovincia") or df.get("provincia")),
                ]
            )


def _render_compare_panel(main_clienteid: int):
    compare_items = [i for i in st.session_state.get("cli_compare", []) if i["id"] != main_clienteid]
    st.markdown("---")
    st.subheader("Vista comparativa")
    st.caption("Coloca clientes a la izquierda y derecha para verlos a la vez.")
    search_col, add_col = st.columns([3, 1])
    with search_col:
        q_cmp = st.text_input("Buscar cliente para comparar", key=f"cmp_q_{main_clienteid}")
    with add_col:
        st.markdown(" ")
        st.markdown(" ")
        add_clicked = st.button("Buscar", key=f"cmp_search_{main_clienteid}")

    options = []
    if q_cmp and add_clicked:
        payload = _api_get_cached("/api/clientes", params={"q": q_cmp, "page": 1, "page_size": 10})
        for c in payload.get("data", []):
            label = c.get("razonsocial") or c.get("nombre") or f"Cliente {c.get('clienteid')}"
            options.append((f"{label} · {c.get('cifdni') or '-'}", c.get("clienteid")))
    if options:
        label_map = {label: cid for label, cid in options}
        elegido = st.selectbox("Resultados", options=list(label_map.keys()), key=f"cmp_pick_{main_clienteid}")
        if st.button("Añadir a comparar", key=f"cmp_add_{main_clienteid}"):
            cid = label_map[elegido]
            label = elegido.split(" · ")[0]
            _compare_add(cid, label, "")

    if not compare_items:
        st.info("No hay clientes añadidos para comparar. Usa el botón Comparar o la búsqueda arriba.")
        return
    layout = st.radio(
        "Diseño",
        ["Izquierda/Derecha", "Tabla"],
        horizontal=True,
        key=f"cmp_layout_{main_clienteid}",
    )
    entries = [{"id": main_clienteid, "label": "Cliente actual"}] + compare_items
    payloads = []
    for item in entries:
        data = _fetch_cliente_detalle(int(item["id"]))
        payloads.append((item, data))

    if layout == "Tabla":
        rows = [
            ("Razón social", "razonsocial"),
            ("Nombre", "nombre"),
            ("CIF/DNI", "cifdni"),
            ("Cuenta", "codigocuenta"),
            ("Código C/P", "codigoclienteoproveedor"),
            ("Tipo", "clienteoproveedor"),
            ("Grupo", "idgrupo"),
            ("Email", "email"),
            ("Teléfono", "telefono"),
            ("Móvil", "movil"),
            ("Provincia", "provincia"),
            ("Municipio", "municipio"),
        ]
        table = {}
        for item, data in payloads:
            label = item["label"]
            if data.get("_error"):
                table[label] = {k: f"Error: {data['_error']}" for k, _ in rows}
                continue
            cli = data.get("cliente", {})
            table[label] = {
                label_name: _safe(cli.get(field))
                for label_name, field in rows
            }
        df = pd.DataFrame(table)
        st.dataframe(df, width="stretch")
        return

    # Izquierda/Derecha: máximo 2 columnas visibles, el resto apilado abajo
    main_payloads = payloads[:2]
    extra_payloads = payloads[2:]
    cols = st.columns(2)
    for idx, (item, data) in enumerate(main_payloads):
        with cols[idx]:
            if data.get("_error"):
                st.error(f"Error cargando detalle: {data['_error']}")
                continue
            _render_compare_card(data, item["label"])
    if extra_payloads:
        st.markdown("---")
        st.caption("Más clientes añadidos")
        for item, data in extra_payloads:
            if data.get("_error"):
                st.error(f"Error cargando detalle: {data['_error']}")
                continue
            _render_compare_card(data, item["label"])








def render_cliente_lista(API_URL: str):
    _ensure_icon_css()
    apply_orbe_theme()

    st.header("Gestion de clientes")
    st.caption("Consulta, filtra y accede al detalle completo de tus clientes.")
    last_added = st.session_state.pop("cli_compare_last", None)
    if last_added:
        with st.container(border=True):
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f"**Añadido a comparativa:** {last_added}")
                st.caption("Abre un cliente para ver la comparativa izquierda/derecha.")
            with c2:
                st.button("OK", key="cli_cmp_ok")

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
        "cli_grupo_filtro": "Todos",
        "cli_compare": [],
        "cli_f_razon": "",
        "cli_f_nombre": "",
        "cli_f_cif": "",
        "cli_f_codcta": "",
        "cli_f_codcp": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    cli_catalogos = _api_get_cached("/api/clientes/catalogos")
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
        st.button("Limpiar filtros", on_click=_clear_filters)

    top_pres = _api_get_cached("/api/presupuestos/top-clientes", params={"limit": 5})
    top_pres_items = top_pres.get("data") or []
    if top_pres_items:
        st.caption("Top clientes (presupuestos)")
        cols = st.columns(min(5, len(top_pres_items)))

        def _set_cli_q(label: str):
            st.session_state.update({"cli_q": label, "cli_page": 1})

        for i, it in enumerate(top_pres_items):
            label = it.get("label") or f"Cliente {it.get('clienteid')}"
            count = it.get("count") or 0
            cols[i % len(cols)].button(
                f"{label} · {count}",
                key=f"cli_top_pres_{it.get('clienteid')}",
                on_click=_set_cli_q,
                args=(label,),
            )

    st.markdown("---")

    sel = st.session_state.get("cliente_detalle_id")
    if sel:
        if st.session_state.get("cli_compare_mode"):
            if st.button("Ver ficha completa", key="cli_cmp_full"):
                st.session_state["cli_compare_mode"] = False
                st.rerun()
            _render_compare_panel(int(sel))
        else:
            _render_detalle_panel(sel)
        st.markdown("---")
        st.subheader("Catálogo de clientes")

    st.subheader("Comparar clientes (max 3)")
    compare_items = st.session_state.get("cli_compare", [])
    if st.session_state.pop("cli_compare_full", False):
        st.warning("Puedes comparar hasta 3 clientes.")
    if compare_items:
        cols_cmp = st.columns(min(3, len(compare_items)))
        for i, item in enumerate(compare_items):
            label = item["label"]
            cif = item.get("cif")
            txt = f"{label}" + (f" · {cif}" if cif else "")
            if cols_cmp[i % len(cols_cmp)].button(f"✕ {txt}", key=f"cmp_rm_{item['id']}"):
                _compare_remove(item["id"])
                st.rerun()
        st.caption("Abre un cliente para ver la comparativa izquierda/derecha.")
        st.button("Limpiar comparativa", key="cmp_clear", on_click=lambda: st.session_state.update({"cli_compare": []}))
    else:
        st.caption("Selecciona clientes con el botón Comparar en la lista.")

    with st.expander("Filtros avanzados", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            grupo_labels = ["Todos"] + list(grupos.keys())
            st.session_state["cli_grupo_filtro"] = st.selectbox("Grupo", grupo_labels)
        with f2:
            st.session_state["cli_f_razon"] = st.text_input(
                "Razón social",
                value=st.session_state.get("cli_f_razon", ""),
                on_change=_on_filter_change,
            )
            st.session_state["cli_f_nombre"] = st.text_input(
                "Nombre",
                value=st.session_state.get("cli_f_nombre", ""),
                on_change=_on_filter_change,
            )
        with f3:
            st.session_state["cli_f_cif"] = st.text_input(
                "CIF/DNI",
                value=st.session_state.get("cli_f_cif", ""),
                on_change=_on_filter_change,
            )
            st.session_state["cli_f_codcta"] = st.text_input(
                "Código cuenta",
                value=st.session_state.get("cli_f_codcta", ""),
                on_change=_on_filter_change,
            )
            st.session_state["cli_f_codcp"] = st.text_input(
                "Código cliente",
                value=st.session_state.get("cli_f_codcp", ""),
                on_change=_on_filter_change,
            )

        f4, f5 = st.columns(2)
        with f4:
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar por",
                ["razonsocial", "nombre", "cifdni", "codigocuenta", "codigoclienteoproveedor"],
            )
        with f5:
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
        "razonsocial": st.session_state.get("cli_f_razon") or None,
        "nombre": st.session_state.get("cli_f_nombre") or None,
        "cifdni": st.session_state.get("cli_f_cif") or None,
        "codigocuenta": st.session_state.get("cli_f_codcta") or None,
        "codigoclienteoproveedor": st.session_state.get("cli_f_codcp") or None,
        "page": page,
        "page_size": page_size,
        "sort_field": st.session_state["cli_sort_field"],
        "sort_dir": st.session_state["cli_sort_dir"],
    }

    grupo_filtro = st.session_state.get("cli_grupo_filtro", "Todos")
    if grupo_filtro != "Todos":
        params["idgrupo"] = grupos.get(grupo_filtro)

    payload = _api_get_cached("/api/clientes", params=params)
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
            width="stretch",
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
            elegido = st.selectbox("Detalle de cliente", options=list(label_map.keys()))
            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
            if st.button("🔍", key="cli_table_open"):
                st.session_state.update({"cliente_detalle_id": label_map[elegido], "cli_compare_mode": False})
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("Comparar", key="cli_table_buy"):
                cid = label_map[elegido]
                label = elegido
                cif = next((c.get("cifdni") for c in clientes if c.get("clienteid") == cid), "")
                _compare_add(cid, label, _safe(cif, ""))
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
    _, action_col = st.columns([5, 1])
    with action_col:
        with st.popover("⋯", width="stretch"):
            if st.button("Ver detalle", key=f"cli_detalle_{cid}"):
                st.session_state.update({"cliente_detalle_id": cid, "cli_compare_mode": False})
                st.rerun()
            if st.button("Comparar", key=f"cli_cmp_{cid}"):
                label = c.get("razonsocial") or c.get("nombre") or "Cliente"
                cif = c.get("cifdni") or ""
                _compare_add(cid, label, _safe(cif, ""))


def _render_detalle_panel(clienteid: int):
    top1, top2, top3 = st.columns([2, 1, 1])
    with top1:
        if st.button("Crear presupuesto para este cliente", key=f"cli_pres_{clienteid}", width="stretch"):
            st.session_state["pres_cli_prefill"] = int(clienteid)
            st.session_state["show_creator"] = True
            st.session_state["menu_principal"] = "💼 Gestion de presupuestos"
            st.rerun()
    with top2:
        if st.button("Editar cliente", key=f"cli_edit_top_{clienteid}", width="stretch"):
            st.session_state["cli_show_form"] = "cliente"
            st.session_state["cliente_actual"] = clienteid
            st.rerun()
        if st.button("Agregar a comparar", key=f"cli_cmp_add_{clienteid}", width="stretch"):
            label = f"Cliente {clienteid}"
            _compare_add(clienteid, label, "")
    with top3:
        if st.button("Cerrar detalle", key=f"cerrar_cli_top_{clienteid}", width="stretch"):
            st.session_state.update({"cliente_detalle_id": None, "cli_compare_mode": False})
            st.rerun()

    with st.container(border=True):
        c1, _ = st.columns([4, 1])
        with c1:
            st.subheader(f"Detalle cliente {clienteid}")

        data = _fetch_cliente_detalle(clienteid)
        if data.get("_error"):
            st.error(f"Error cargando detalle: {data['_error']}")
            if st.button("Cerrar", key=f"cerrar_cli_err_{clienteid}"):
                st.session_state.update({"cliente_detalle_id": None, "cli_compare_mode": False})
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

    _render_compare_panel(clienteid)



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
        width="stretch",
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

