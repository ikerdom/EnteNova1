import math
import os
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

from modules.orbe_theme import apply_orbe_theme
from modules.producto_arbol_ui import render_arbol_productos
from modules.producto_form import render_producto_form


def _api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def _api_get(path: str, params: Optional[dict] = None, show_error: bool = True) -> dict:
    try:
        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if show_error:
            st.error(f"Error API: {e}")
        return {}


@st.cache_data(ttl=60)
def _api_get_cached(path: str, params: Optional[dict] = None) -> dict:
    return _api_get(path, params=params, show_error=False)


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


def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def _price(v: Any):
    try:
        return f"{float(v):.2f} EUR"
    except Exception:
        return "-"


def _as_int(v: Any) -> Optional[int]:
    try:
        if v in (None, "", "null"):
            return None
        return int(v)
    except Exception:
        return None


def _on_filter_change():
    st.session_state["prod_page"] = 1


def _clear_prod_filters():
    st.session_state["prod_q"] = ""
    st.session_state["prod_familia"] = "Todas"
    st.session_state["prod_tipo"] = "Todos"
    st.session_state["prod_categoria"] = "Todas"
    st.session_state["prod_f_titulo"] = ""
    st.session_state["prod_f_idproducto"] = ""
    st.session_state["prod_f_ref"] = ""
    st.session_state["prod_f_isbn"] = ""
    st.session_state["prod_f_ean"] = ""
    st.session_state["prod_page"] = 1


def _prod_compare_add(pid: Any, label: str):
    items = st.session_state.setdefault("prod_compare", [])
    if any(i["id"] == pid for i in items):
        return
    if len(items) >= 3:
        st.session_state["prod_compare_full"] = True
        return
    items.append({"id": pid, "label": label})
    st.session_state["prod_compare"] = items
    st.session_state["prod_compare_last"] = label
    if len(items) >= 2:
        st.session_state["prod_compare_mode"] = True
        st.session_state["prod_detalle_id"] = items[0]["id"]
        st.rerun()


def _prod_compare_remove(pid: Any):
    items = st.session_state.get("prod_compare", [])
    st.session_state["prod_compare"] = [i for i in items if i["id"] != pid]


@st.cache_data(ttl=120)
def _fetch_producto_detalle_cached(productoid: int) -> dict:
    try:
        res = requests.get(f"{_api_base()}/api/productos/{productoid}", timeout=15)
        res.raise_for_status()
        return res.json() or {}
    except Exception as e:
        return {"_error": str(e)}


def _fetch_producto_detalle(productoid: int) -> dict:
    return _fetch_producto_detalle_cached(productoid)


def _render_compare_card_producto(data: dict, title: str):
    p = data.get("producto", data)
    nombre = p.get("titulo_automatico") or title
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""
    with st.container(border=True):
        top_l, top_r = st.columns([3, 1])
        with top_l:
            st.markdown(f"### {nombre}")
            st.caption(title)
        with top_r:
            st.markdown(f"**{_price(p.get('pvp'))}**")
        left, right = st.columns([1, 2])
        with left:
            if portada:
                st.image(portada, width=160)
            else:
                st.info("Sin portada")
        with right:
            k1, k2, k3 = st.columns(3)
            k1.metric("Familia", p.get("familia") or "-")
            k2.metric("Tipo", p.get("tipo") or "-")
            k3.metric("Categoría", p.get("categoria") or "-")
            st.markdown("**Identificadores**")
            d1, d2, d3 = st.columns(3)
            d1.write(f"**ID catálogo:** {p.get('catalogo_productoid') or '-'}")
            d2.write(f"**ID producto:** {p.get('idproducto') or '-'}")
            d3.write(f"**Ref. producto (Cloudia):** {p.get('idproductoreferencia') or '-'}")
            d4, d5 = st.columns(2)
            d4.write(f"**ISBN:** {p.get('isbn') or '-'}")
            d5.write(f"**EAN:** {p.get('ean') or '-'}")
            st.markdown("**Detalles**")
            d6, d7 = st.columns(2)
            d6.write(f"**Proveedor:** {p.get('proveedor') or '-'}")
            d7.write(f"**Cuerpo certificado:** {p.get('cuerpo_certificado') or '-'}")
            d8, d9 = st.columns(2)
            autor = " ".join([x for x in [p.get('autor_nombre'), p.get('autor_apellidos')] if x])
            d8.write(f"**Autor:** {autor or '-'}")
            d9.write(f"**Páginas:** {p.get('total_paginas') or '-'}")
            d10, d11 = st.columns(2)
            d10.write(f"**Tipo producto:** {p.get('tipo_producto') or '-'}")
            d11.write(f"**Categoría raíz:** {p.get('categoria_raiz') or '-'}")


def _render_compare_panel_producto(main_productoid: int):
    compare_items = [i for i in st.session_state.get("prod_compare", []) if i["id"] != main_productoid]
    st.markdown("---")
    st.subheader("Vista comparativa")
    st.caption("Coloca productos a la izquierda y derecha para verlos a la vez.")
    q_cmp = st.text_input("Buscar producto para comparar", key=f"cmp_prod_q_{main_productoid}")

    options = []
    if q_cmp and len(q_cmp.strip()) >= 2:
        payload = _api_get_cached("/api/productos", params={"q": q_cmp, "page": 1, "page_size": 10})
        for p in payload.get("data", []):
            label = p.get("titulo_automatico") or f"Producto {p.get('catalogo_productoid')}"
            options.append((f"{label} · {p.get('idproductoreferencia') or '-'}", p.get("catalogo_productoid")))
    if options:
        label_map = {label: pid for label, pid in options}
        elegido = st.selectbox("Resultados", options=list(label_map.keys()), key=f"cmp_prod_pick_{main_productoid}")
        if st.button("Añadir a comparar", key=f"cmp_prod_add_{main_productoid}"):
            pid = label_map[elegido]
            label = elegido.split(" · ")[0]
            _prod_compare_add(pid, label)

    if not compare_items:
        st.info("No hay productos añadidos para comparar. Usa el botón Comparar o la búsqueda arriba.")
        return

    layout = st.radio(
        "Diseño",
        ["Izquierda/Derecha", "Tabla"],
        horizontal=True,
        key=f"cmp_prod_layout_{main_productoid}",
    )
    entries = [{"id": main_productoid, "label": "Producto actual"}] + compare_items
    payloads = []
    for item in entries:
        data = _fetch_producto_detalle(int(item["id"]))
        payloads.append((item, data))

    if layout == "Tabla":
        rows = [
            ("Nombre", "titulo_automatico"),
            ("Ref. (Cloudia)", "idproductoreferencia"),
            ("ID producto", "idproducto"),
            ("ISBN", "isbn"),
            ("EAN", "ean"),
            ("Familia", "familia"),
            ("Tipo", "tipo"),
            ("Categoría", "categoria"),
            ("Categoría raíz", "categoria_raiz"),
            ("Cuerpo certificado", "cuerpo_certificado"),
            ("Proveedor", "proveedor"),
            ("Autor", "autor_nombre"),
            ("Apellidos autor", "autor_apellidos"),
            ("Páginas", "total_paginas"),
            ("Tipo producto", "tipo_producto"),
            ("Precio", "pvp"),
            ("Público", "publico"),
            ("Publicación", "fecha_publicacion"),
        ]
        table = {}
        for item, data in payloads:
            label = item["label"]
            if data.get("_error"):
                table[label] = {k: f"Error: {data['_error']}" for k, _ in rows}
                continue
            p = data.get("producto", data)
            table[label] = {
                label_name: _safe(p.get(field))
                for label_name, field in rows
            }
        df = pd.DataFrame(table)
        st.dataframe(df, width="stretch")
        return

    main_payloads = payloads[:2]
    extra_payloads = payloads[2:]
    cols = st.columns(2)
    for idx, (item, data) in enumerate(main_payloads):
        with cols[idx]:
            if data.get("_error"):
                st.error(f"Error cargando detalle: {data['_error']}")
                continue
            _render_compare_card_producto(data, item["label"])
    if extra_payloads:
        st.markdown("---")
        st.caption("Más productos añadidos")
        for item, data in extra_payloads:
            if data.get("_error"):
                st.error(f"Error cargando detalle: {data['_error']}")
                continue
            _render_compare_card_producto(data, item["label"])


def _chunked(items: Sequence[int], size: int = 200) -> Iterable[List[int]]:
    for i in range(0, len(items), size):
        yield list(items[i : i + size])


def _load_albaran_ids_since(supa, since: date) -> List[int]:
    try:
        res = (
            supa.table("albaran")
            .select("albaran_id, fecha_albaran")
            .gte("fecha_albaran", str(since))
            .execute()
        )
        return [r.get("albaran_id") for r in res.data or [] if r.get("albaran_id")]
    except Exception as e:
        st.warning(f"No se pudieron cargar albaranes recientes: {e}")
        return []


def _load_albaran_fecha_map(supa, since: date) -> Dict[int, str]:
    try:
        res = (
            supa.table("albaran")
            .select("albaran_id, fecha_albaran")
            .gte("fecha_albaran", str(since))
            .execute()
        )
        out: Dict[int, str] = {}
        for r in res.data or []:
            alb_id = r.get("albaran_id")
            fecha = r.get("fecha_albaran")
            if alb_id and fecha:
                out[int(alb_id)] = str(fecha)[:10]
        return out
    except Exception as e:
        st.warning(f"No se pudieron cargar fechas de albarán: {e}")
        return {}


def _load_albaran_lineas_for_producto(supa, product_id: int, albaran_ids: List[int]) -> List[dict]:
    if not albaran_ids:
        return []

    rows: List[dict] = []
    for chunk in _chunked(albaran_ids, size=200):
        q = (
            supa.table("albaran_linea")
            .select("albaran_id, cantidad, subtotal, precio, descuento_pct, idproducto, producto_id, producto_id_origen")
            .in_("albaran_id", chunk)
        )
        try:
            q = q.or_(
                f"idproducto.eq.{product_id},producto_id.eq.{product_id},producto_id_origen.eq.{product_id}"
            )
            res = q.execute()
        except Exception:
            try:
                res = q.eq("idproducto", product_id).execute()
            except Exception as e:
                st.warning(f"No se pudieron cargar líneas de albarán: {e}")
                return rows
    rows.extend(res.data or [])
    return rows


def _load_pedido_lineas_for_producto(supa, product_id: int, since: date) -> List[dict]:
    q = (
        supa.table("pedido_linea")
        .select("pedido_id, cantidad, subtotal, precio, descuento_pct, producto_id, producto_ref_origen, created_at")
        .gte("created_at", str(since))
    )
    try:
        q = q.or_(f"producto_id.eq.{product_id},producto_ref_origen.eq.{product_id}")
        res = q.execute()
    except Exception:
        try:
            res = q.eq("producto_id", product_id).execute()
        except Exception as e:
            st.warning(f"No se pudieron cargar líneas de pedidos: {e}")
            return []
    return res.data or []


# ======================================================
# LISTA DE PRODUCTOS (UI -> FastAPI)
# ======================================================
def render_producto_lista(supabase=None):
    apply_orbe_theme()
    _ensure_icon_css()

    st.header("Gestion de productos")
    st.caption("Listado, filtros y acceso rapido al detalle del producto.")
    last_added = st.session_state.pop("prod_compare_last", None)
    if last_added:
        with st.container(border=True):
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f"**Añadido a comparativa:** {last_added}")
                st.caption("Abre un producto para ver la comparativa izquierda/derecha.")
            with c2:
                st.button("OK", key="prod_cmp_ok")

    st.session_state.setdefault("prod_show_form", False)
    if st.session_state.get("prod_detalle_id"):
        st.session_state["prod_show_form"] = False
    # Modo catalogo / arbol
    st.session_state.setdefault("modo_producto", "Catalogo")
    st.session_state["modo_producto"] = st.selectbox(
        "Vista de productos",
        ["Catalogo", "Arbol"],
        index=0 if st.session_state.get("modo_producto") == "Catalogo" else 1,
        key="modo_prod_selector",
    )

    # Alta producto (solo catalogo)
    if st.session_state.get("modo_producto") == "Catalogo":
        if st.button("Nuevo producto", key="btn_nuevo_prod", width="stretch"):
            st.session_state["prod_show_form"] = True
            st.rerun()

    if st.session_state.get("prod_show_form"):
        supa = supabase or st.session_state.get("supa")
        if not supa:
            st.error("Necesito Supabase para usar el formulario de producto.")
            return
        render_producto_form(supa)
        return

    # Vista arbol
    if st.session_state.get("modo_producto") == "Arbol":
        supa = supabase or st.session_state.get("supa")
        if not supa:
            st.error("Necesito el cliente supabase para mostrar el arbol de productos.")
            return
        render_arbol_productos(supa)
        return

    # estado UI
    defaults = {
        "prod_page": 1,
        "prod_sort_field": "titulo_automatico",
        "prod_sort_dir": "ASC",
        "prod_view": "Tarjetas",
        "prod_result_count": 0,
        "prod_table_cols": ["catalogo_productoid", "titulo_automatico", "idproducto", "idproductoreferencia", "familia", "tipo", "categoria", "isbn", "ean", "pvp"],
        "prod_compact": st.session_state.get("pref_compact", True),
        "prod_compare": [],
        "prod_f_titulo": "",
        "prod_f_idproducto": "",
        "prod_f_ref": "",
        "prod_f_isbn": "",
        "prod_f_ean": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Catalogos
    cats = _api_get_cached("/api/productos/catalogos")
    familias = {c["label"]: c["id"] for c in cats.get("familias", [])}
    tipos = {c["label"]: c["id"] for c in cats.get("tipos", [])}
    categorias = {c["label"]: c["id"] for c in cats.get("categorias", [])}

    # Filtros
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        q = st.text_input("Buscar", placeholder="Nombre, referencia, ISBN, EAN...", key="prod_q")
        if st.session_state.get("prod_last_q") != q:
            st.session_state["prod_page"] = 1
            st.session_state["prod_last_q"] = q
    with c2:
        st.metric("Resultados", st.session_state["prod_result_count"])
    with c3:
        st.button("Limpiar filtros", on_click=_clear_prod_filters)

    with st.expander("Opciones y filtros", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            st.session_state["prod_view"] = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True)
            st.session_state["prod_sort_field"] = st.selectbox("Ordenar por", ["titulo_automatico", "idproducto", "idproductoreferencia", "isbn", "ean", "pvp"])
            st.session_state["prod_sort_dir"] = st.radio("Direccion", ["ASC", "DESC"], horizontal=True)
        with f2:
            st.session_state["prod_f_titulo"] = st.text_input(
                "Nombre / título",
                value=st.session_state.get("prod_f_titulo", ""),
                on_change=_on_filter_change,
            )
            st.session_state["prod_f_idproducto"] = st.text_input(
                "ID producto",
                value=st.session_state.get("prod_f_idproducto", ""),
                on_change=_on_filter_change,
            )
            st.session_state["prod_f_ref"] = st.text_input(
                "Referencia",
                value=st.session_state.get("prod_f_ref", ""),
                on_change=_on_filter_change,
            )
        with f3:
            st.session_state["prod_f_isbn"] = st.text_input(
                "ISBN",
                value=st.session_state.get("prod_f_isbn", ""),
                on_change=_on_filter_change,
            )
            st.session_state["prod_f_ean"] = st.text_input(
                "EAN",
                value=st.session_state.get("prod_f_ean", ""),
                on_change=_on_filter_change,
            )
            fam_labels = ["Todas"] + list(familias.keys())
            tipo_labels = ["Todos"] + list(tipos.keys())
            cat_labels = ["Todas"] + list(categorias.keys())
            st.session_state["prod_familia"] = st.selectbox(
                "Familia",
                fam_labels,
                index=fam_labels.index(st.session_state.get("prod_familia", "Todas"))
                if st.session_state.get("prod_familia") in fam_labels
                else 0,
            )
            st.session_state["prod_tipo"] = st.selectbox("Tipo", tipo_labels)
            st.session_state["prod_categoria"] = st.selectbox("Categoria", cat_labels)

    st.subheader("Comparar productos (max 3)")
    compare_items = st.session_state.get("prod_compare", [])
    if st.session_state.pop("prod_compare_full", False):
        st.warning("Puedes comparar hasta 3 productos.")
    if compare_items:
        cols_cmp = st.columns(min(3, len(compare_items)))
        for i, item in enumerate(compare_items):
            label = item["label"]
            if cols_cmp[i % len(cols_cmp)].button(f"✕ {label}", key=f"prod_cmp_rm_{item['id']}"):
                _prod_compare_remove(item["id"])
                st.rerun()
        if len(compare_items) == 1:
            st.caption("Comparativa pendiente: elige otro producto.")
        else:
            st.caption("Abre un producto para ver la comparativa izquierda/derecha.")
        st.button("Limpiar comparativa", key="prod_cmp_clear", on_click=lambda: st.session_state.update({"prod_compare": []}))
    else:
        st.caption("Selecciona productos con el botón Comparar en la lista.")
        if st.session_state["prod_view"] == "Tabla":
            all_cols = [
                "catalogo_productoid",
                "titulo_automatico",
                "idproducto",
                "idproductoreferencia",
                "familia",
                "tipo",
                "categoria",
                "isbn",
                "ean",
                "pvp",
            ]
            st.session_state["prod_table_cols"] = st.multiselect(
                "Columnas a mostrar",
                options=all_cols,
                default=st.session_state.get("prod_table_cols", defaults["prod_table_cols"]),
            )
            st.session_state["prod_sort_field"] = st.selectbox(
                "Ordenar tabla por",
                options=st.session_state["prod_table_cols"] or all_cols,
                key="prod_sort_field_table",
            )
            st.session_state["prod_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
                key="prod_sort_dir_table",
            )

    # Params API
    page = st.session_state["prod_page"]
    page_size = 30
    params = {
        "q": q or None,
        "page": page,
        "page_size": page_size,
        "sort_field": st.session_state["prod_sort_field"],
        "sort_dir": st.session_state["prod_sort_dir"],
    }
    fam_sel = st.session_state.get("prod_familia")
    if fam_sel and fam_sel != "Todas":
        params["familiaid"] = familias.get(fam_sel)
    tipo_sel = st.session_state.get("prod_tipo")
    if tipo_sel and tipo_sel != "Todos":
        params["tipoid"] = tipos.get(tipo_sel)
    cat_sel = st.session_state.get("prod_categoria")
    if cat_sel and cat_sel != "Todas":
        params["categoriaid"] = categorias.get(cat_sel)

    params.update(
        {
            "titulo": st.session_state.get("prod_f_titulo") or None,
            "idproducto": st.session_state.get("prod_f_idproducto") or None,
            "idproductoreferencia": st.session_state.get("prod_f_ref") or None,
            "isbn": st.session_state.get("prod_f_isbn") or None,
            "ean": st.session_state.get("prod_f_ean") or None,
        }
    )

    payload = _api_get_cached("/api/productos", params=params)
    productos: List[Dict[str, Any]] = payload.get("data", [])
    total = payload.get("total", 0)
    total_pages = payload.get("total_pages", 1)
    st.session_state["prod_result_count"] = len(productos)

    # Detalle prioritario si seleccionado
    sel = st.session_state.get("prod_detalle_id")
    if sel:
        if st.session_state.get("prod_compare_mode"):
            if st.button("Ver ficha completa", key="prod_cmp_full"):
                st.session_state["prod_compare_mode"] = False
                st.rerun()
            _render_compare_panel_producto(int(sel))
        else:
            _render_modal_producto(sel, supabase or st.session_state.get("supa"))
        st.markdown("---")

    if not productos:
        st.info("No hay productos con esos filtros.")
        return

    if st.session_state["prod_view"] == "Tarjetas":
        cols = st.columns(3)
        for i, p in enumerate(productos):
            with cols[i % 3]:
                _render_card_producto(p)
    else:
        _render_tabla_productos(productos)

    # paginacion
    st.markdown("---")
    total_pages = max(1, math.ceil(total / page_size))
    p1, _, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1):
            st.session_state["prod_page"] = page - 1
            st.rerun()
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages):
            st.session_state["prod_page"] = page + 1
            st.rerun()
    st.caption(f"Pagina {page}/{total_pages} - Total: {total}")


def _render_card_producto(p: dict):
    nombre = _safe(p.get("titulo_automatico"))
    ref = _safe(p.get("idproductoreferencia"))
    familia = _safe(p.get("familia"))
    tipo = _safe(p.get("tipo"))
    categoria = _safe(p.get("categoria"))
    precio = _price(p.get("pvp"))
    isbn = _safe(p.get("isbn"))
    ean = _safe(p.get("ean"))
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    W, H = 80, 110
    portada_html = (
        f"<img src='{portada}' style='width:100%;height:100%;object-fit:cover;display:block;' />"
        if portada
        else "<div style='display:flex;align-items:center;justify-content:center;width:100%;height:100%;color:#94a3b8;'>Sin portada</div>"
    )
    compact = st.session_state.get("prod_compact", False)
    min_h = "150px" if compact else "165px"
    clamp = "1" if compact else "2"
    pad = "10px" if compact else "12px"

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;
                    background:#f9fafb;padding:{pad};margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);min-height:{min_h};">
            <div style="display:flex;gap:12px;">
                <div style="width:{W}px;height:{H}px;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff;">
                    {portada_html}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:1.05rem;font-weight:700;line-height:1.1;
                                display:-webkit-box;-webkit-line-clamp:{clamp};-webkit-box-orient:vertical;overflow:hidden;">
                        {nombre}
                    </div>
                    <div style="color:#6b7280;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        Ref: {ref}
                    </div>
                    <div style="margin-top:6px;font-size:.9rem;">
                        <b>Familia:</b> {familia}<br>
                        <b>Tipo:</b> {tipo}<br>
                        <b>Categoria:</b> {categoria}<br>
                        <b>Precio:</b> {precio}
                    </div>
                    <div style="margin-top:6px;color:#6b7280;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        ISBN: {isbn} | EAN: {ean}
                    </div>
                </div>
            </div>
        </div>
        """,
        height=175,
    )
    pid = p.get("catalogo_productoid")
    st.markdown('<div class="card-actions"><div class="icon-btn">', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)
    _, action_col = st.columns([5, 1])
    with action_col:
        with st.popover("⋯", width="stretch"):
            if st.button("Ver detalle", key=f"prod_detalle_{pid}"):
                st.session_state.update({"prod_detalle_id": pid, "prod_compare_mode": False})
                st.rerun()
            if st.button("Comparar", key=f"prod_cmp_{pid}"):
                label = p.get("titulo_automatico") or f"Producto {pid}"
                _prod_compare_add(pid, label)


def _render_tabla_productos(productos: list):
    cols_sel = st.session_state.get("prod_table_cols") or []
    if not cols_sel:
        st.info("Selecciona al menos una columna para mostrar.")
        return
    rows = []
    for p in productos:
        row = {}
        for col in cols_sel:
            row[col] = p.get(col)
        rows.append(row)
    st.dataframe(rows, width="stretch", hide_index=True)

    # Selector rapido para abrir detalle desde la tabla
    opciones = [
        (f"{p.get('catalogo_productoid')} - {p.get('titulo_automatico')}", p.get("catalogo_productoid"))
        for p in productos
        if p.get("catalogo_productoid") is not None
    ]
    if opciones:
        label_map = {label: pid for label, pid in opciones}
        elegido = st.selectbox(
            "Detalle de producto",
            options=list(label_map.keys()),
            index=0,
            key="prod_sel_detalle",
        )
        st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
        if st.button("🔍", key="prod_sel_btn"):
            st.session_state.update({"prod_detalle_id": label_map[elegido], "prod_compare_mode": False})
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("Comparar", key="prod_sel_cmp"):
            pid = label_map[elegido]
            label = elegido.split(" - ", 1)[-1] if " - " in elegido else elegido
            _prod_compare_add(pid, label)


def _render_modal_producto(productoid: int, supabase=None):
    try:
        res = requests.get(f"{_api_base()}/api/productos/{productoid}", timeout=15)
        res.raise_for_status()
        data = res.json() or {}
    except Exception as e:
        st.error(f"Error cargando detalle de producto: {e}")
        if st.button("Cerrar", key=f"cerrar_prod_err_{productoid}", width="stretch"):
            st.session_state.update({"prod_detalle_id": None, "prod_compare_mode": False})
            st.rerun()
        return

    p = data.get("producto", data)

    titulo = p.get("titulo_automatico") or "Producto sin titulo"
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    st.markdown("---")
    top1, top2 = st.columns([3, 1])
    with top1:
        st.subheader(titulo)
    with top2:
        if st.button("Agregar a comparar", key=f"prod_cmp_add_{productoid}", width="stretch"):
            _prod_compare_add(productoid, titulo)

    left, right = st.columns([1, 2])
    with left:
        if portada:
            st.image(portada, width=260)
        else:
            st.info("Sin portada")
    with right:
        k1, k2, k3 = st.columns(3)
        k1.metric("Precio", _price(p.get("pvp")))
        k2.metric("Familia", p.get("familia") or "-")
        k3.metric("Tipo", p.get("tipo") or "-")

        k4, k5, k6 = st.columns(3)
        k4.metric("Categoría", p.get("categoria") or "-")
        k5.metric("Público", "Sí" if p.get("publico") else "No")
        k6.metric("Publicación", p.get("fecha_publicacion") or "-")

        st.markdown("**Identificadores**")
        d1, d2, d3 = st.columns(3)
        d1.write(f"**ID catálogo:** {p.get('catalogo_productoid') or '-'}")
        d2.write(f"**ID producto:** {p.get('idproducto') or '-'}")
        d3.write(f"**Ref. producto:** {p.get('idproductoreferencia') or '-'}")

        d4, d5 = st.columns(2)
        d4.write(f"**ISBN:** {p.get('isbn') or '-'}")
        d5.write(f"**EAN:** {p.get('ean') or '-'}")

        st.markdown("**Descripción**")
        st.write(p.get("descripcion") or "Sin descripción.")

    st.markdown("### Ventas en pedidos")
    if not supabase:
        st.info("Conecta Supabase para ver métricas de ventas.")
    else:
        years_opts = [1, 2, 3, 5]
        years = st.selectbox(
            "Periodo",
            options=years_opts,
            index=1,
            key=f"prod_sales_years_{productoid}",
        )
        since = date.today() - timedelta(days=365 * int(years))
        pid = (
            _as_int(p.get("idproducto"))
            or _as_int(p.get("productoid"))
            or _as_int(p.get("catalogo_productoid"))
        )
        if not pid:
            st.info("No se encontró un ID de producto válido para cruzar pedidos.")
        else:
            lineas = _load_pedido_lineas_for_producto(supabase, pid, since)
            total_qty = sum(float(r.get("cantidad") or 0) for r in lineas)
            total_imp = 0.0
            for r in lineas:
                subtotal = r.get("subtotal")
                if subtotal is not None:
                    total_imp += float(subtotal or 0)
                else:
                    qty = float(r.get("cantidad") or 0)
                    precio = r.get("precio") or 0
                    total_imp += float(precio) * qty
            total_ped = len({r.get("pedido_id") for r in lineas if r.get("pedido_id")})
            m1, m2, m3 = st.columns(3)
            m1.metric("Pedidos", total_ped)
            m2.metric("Unidades", f"{total_qty:,.0f}".replace(",", "."))
            m3.metric("Importe", f"{total_imp:,.2f} EUR".replace(",", "."))
            st.caption(f"Totales desde {since.isoformat()}")

    if st.button("Cerrar detalle", key=f"cerrar_prod_{productoid}", width="stretch"):
        st.session_state.update({"prod_detalle_id": None, "prod_compare_mode": False})
        st.rerun()

    _render_compare_panel_producto(productoid)


