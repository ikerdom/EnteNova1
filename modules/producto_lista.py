import math
import os
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests
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


def _api_get(path: str, params: Optional[dict] = None) -> dict:
    try:
        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return {}


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
            .select("albaran_id, cantidad, importe_total_linea, idproducto, producto_id, producto_id_origen")
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


# ======================================================
# LISTA DE PRODUCTOS (UI -> FastAPI)
# ======================================================
def render_producto_lista(supabase=None):
    apply_orbe_theme()

    st.header("Gestion de productos")
    st.caption("Listado, filtros y acceso rapido a la ficha del producto.")

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
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Catalogos
    cats = _api_get("/api/productos/catalogos")
    familias = {c["label"]: c["id"] for c in cats.get("familias", [])}
    tipos = {c["label"]: c["id"] for c in cats.get("tipos", [])}
    categorias = {c["label"]: c["id"] for c in cats.get("categorias", [])}

    # Filtros
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar", placeholder="Nombre, referencia, ISBN, EAN...", key="prod_q")
        if st.session_state.get("prod_last_q") != q:
            st.session_state["prod_page"] = 1
            st.session_state["prod_last_q"] = q
    with c2:
        st.metric("Resultados", st.session_state["prod_result_count"])

    with st.expander("Opciones y filtros", expanded=False):
        f1, f2 = st.columns(2)
        with f1:
            st.session_state["prod_view"] = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True)
            st.session_state["prod_sort_field"] = st.selectbox("Ordenar por", ["titulo_automatico", "idproducto", "idproductoreferencia", "isbn", "ean", "pvp"])
            st.session_state["prod_sort_dir"] = st.radio("Direccion", ["ASC", "DESC"], horizontal=True)
        with f2:
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

    payload = _api_get("/api/productos", params=params)
    productos: List[Dict[str, Any]] = payload.get("data", [])
    total = payload.get("total", 0)
    total_pages = payload.get("total_pages", 1)
    st.session_state["prod_result_count"] = len(productos)

    # Ficha prioritaria si seleccionada
    sel = st.session_state.get("prod_detalle_id")
    if sel:
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

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;
                    background:#f9fafb;padding:12px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;gap:12px;">
                <div style="width:{W}px;height:{H}px;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff;">
                    {portada_html}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:1.05rem;font-weight:700;">{nombre}</div>
                    <div style="color:#6b7280;font-size:.9rem;">Ref: {ref}</div>
                    <div style="margin-top:6px;font-size:.9rem;">
                        <b>Familia:</b> {familia}<br>
                        <b>Tipo:</b> {tipo}<br>
                        <b>Categoria:</b> {categoria}<br>
                        <b>Precio:</b> {precio}
                    </div>
                    <div style="margin-top:6px;color:#6b7280;font-size:.85rem;">
                        ISBN: {isbn} | EAN: {ean}
                    </div>
                </div>
            </div>
        </div>
        """,
        height=170,
    )
    pid = p.get("catalogo_productoid")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Ficha", key=f"prod_ficha_{pid}", width="stretch"):
            st.session_state["prod_detalle_id"] = pid
            st.rerun()


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
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Selector rapido para abrir ficha desde la tabla
    opciones = [
        (f"{p.get('catalogo_productoid')} - {p.get('titulo_automatico')}", p.get("catalogo_productoid"))
        for p in productos
        if p.get("catalogo_productoid") is not None
    ]
    if opciones:
        label_map = {label: pid for label, pid in opciones}
        elegido = st.selectbox(
            "Abrir ficha de producto",
            options=list(label_map.keys()),
            index=0,
            key="prod_sel_ficha",
        )
        if st.button("Ver ficha seleccionada", key="prod_sel_btn", width="stretch"):
            st.session_state["prod_detalle_id"] = label_map[elegido]
            st.rerun()


def _render_modal_producto(productoid: int, supabase=None):
    try:
        res = requests.get(f"{_api_base()}/api/productos/{productoid}", timeout=15)
        res.raise_for_status()
        data = res.json() or {}
    except Exception as e:
        st.error(f"Error cargando ficha de producto: {e}")
        if st.button("Cerrar", key=f"cerrar_prod_err_{productoid}", width="stretch"):
            st.session_state["prod_detalle_id"] = None
            st.rerun()
        return

    p = data.get("producto", data)

    titulo = p.get("titulo_automatico") or "Producto sin titulo"
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    st.markdown("---")
    st.subheader(titulo)

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

    st.markdown("### Ventas en albaranes")
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
            st.info("No se encontró un ID de producto válido para cruzar albaranes.")
        else:
            alb_ids = _load_albaran_ids_since(supabase, since)
            fecha_map = _load_albaran_fecha_map(supabase, since)
            lineas = _load_albaran_lineas_for_producto(supabase, pid, alb_ids)
            total_qty = sum(float(r.get("cantidad") or 0) for r in lineas)
            total_imp = sum(float(r.get("importe_total_linea") or 0) for r in lineas)
            total_alb = len({r.get("albaran_id") for r in lineas if r.get("albaran_id")})
            m1, m2, m3 = st.columns(3)
            m1.metric("Líneas", len(lineas))
            m2.metric("Albaranes", total_alb)
            m3.metric("Unidades", f"{total_qty:,.0f}".replace(",", "."))
            st.caption(f"Importe total: {total_imp:,.2f} EUR desde {since.isoformat()}")

            if lineas and fecha_map:
                st.markdown("#### Evolución mensual")
                by_month: Dict[str, float] = {}
                for r in lineas:
                    alb_id = r.get("albaran_id")
                    fecha = fecha_map.get(int(alb_id)) if alb_id else None
                    if not fecha:
                        continue
                    month = fecha[:7]
                    by_month[month] = by_month.get(month, 0.0) + float(r.get("cantidad") or 0)

                months = sorted(by_month.keys())
                data = [{"Mes": m, "Unidades": by_month[m]} for m in months]
                try:
                    import pandas as pd

                    df = pd.DataFrame(data).set_index("Mes")
                    st.line_chart(df, height=220)
                except Exception:
                    st.table(data)

    if st.button("Cerrar ficha", key=f"cerrar_prod_{productoid}", width="stretch"):
        st.session_state["prod_detalle_id"] = None
        st.rerun()


