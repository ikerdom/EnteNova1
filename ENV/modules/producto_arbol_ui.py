import math
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from modules.orbe_theme import apply_orbe_theme


def _price(v: Any) -> str:
    try:
        return f"{float(v):.2f} EUR"
    except Exception:
        return "-"


@st.cache_data(ttl=300)
def _load_tree_data(_supabase) -> Tuple[List[dict], List[dict], List[dict]]:
    categorias = (
        _supabase.table("producto_categoria")
        .select("producto_categoriaid, nombre, habilitado")
        .eq("habilitado", True)
        .order("nombre")
        .execute()
        .data
        or []
    )

    familias = (
        _supabase.table("producto_familia")
        .select("producto_familiaid, nombre, habilitado, categoria_nombre_raw")
        .eq("habilitado", True)
        .order("nombre")
        .execute()
        .data
        or []
    )

    productos = (
        _supabase.table("producto")
        .select(
            "catalogo_productoid, titulo_automatico, idproducto, "
            "idproductoreferencia, portada_url, pvp, "
            "producto_categoriaid, producto_familiaid"
        )
        .order("titulo_automatico")
        .execute()
        .data
        or []
    )

    return categorias, familias, productos


def _match_any(q: str, *values: Optional[str]) -> bool:
    if not q:
        return True
    ql = q.lower()
    for v in values:
        if v and ql in str(v).lower():
            return True
    return False


def _render_producto_row(p: Dict[str, Any]):
    titulo = p.get("titulo_automatico") or "(Sin titulo)"
    ref = p.get("idproductoreferencia") or p.get("idproducto") or "-"
    pid = p.get("catalogo_productoid")
    precio = _price(p.get("pvp"))
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    c1, c2 = st.columns([1, 4])
    with c1:
        if portada:
            st.image(portada, width=60)
        else:
            st.caption("Sin portada")
    with c2:
        st.write(titulo)
        st.caption(f"Ref: {ref} | ID: {pid} | PVP: {precio}")

    if st.button("Ver ficha en catalogo", key=f"tree_ficha_{pid}", use_container_width=True):
        st.session_state["modo_producto"] = "Catalogo"
        st.session_state["prod_show_form"] = False
        st.session_state["prod_detalle_id"] = pid
        st.rerun()


def render_arbol_productos(supabase):
    apply_orbe_theme()

    st.subheader("Catalogo de productos - Vista arbol")
    st.caption("Navega por categorias y familias. Usa el buscador para filtrar.")

    q = st.text_input(
        "Buscar categoria, familia o producto",
        placeholder="Ej: ciclos formativos, acceso, enfermeria",
        key="prod_tree_q",
    ).strip()

    step_size = st.number_input(
        "Mostrar por pagina",
        min_value=5,
        max_value=50,
        value=15,
        step=5,
    )

    try:
        categorias, familias, productos = _load_tree_data(supabase)
    except Exception as e:
        st.error(f"Error cargando datos del arbol: {e}")
        return

    if not categorias and not productos:
        st.info("No hay categorias ni productos disponibles.")
        return

    cat_name = {c["producto_categoriaid"]: c["nombre"] for c in categorias}
    fam_name = {f["producto_familiaid"]: f["nombre"] for f in familias}

    productos_por_cat: Dict[Optional[int], List[dict]] = {}
    for p in productos:
        cat_id = p.get("producto_categoriaid")
        productos_por_cat.setdefault(cat_id, []).append(p)

    categorias_ordenadas: List[Tuple[Optional[int], str]] = [
        (cid, cat_name.get(cid, f"Categoria {cid}"))
        for cid in sorted(cat_name.keys(), key=lambda k: cat_name.get(k, ""))
    ]

    if None in productos_por_cat:
        categorias_ordenadas.append((None, "Sin categoria"))

    for cat_id, cat_label in categorias_ordenadas:
        prods_cat = productos_por_cat.get(cat_id, [])

        def _cat_match() -> bool:
            if _match_any(q, cat_label):
                return True
            for p in prods_cat:
                if _match_any(
                    q,
                    p.get("titulo_automatico"),
                    p.get("idproducto"),
                    p.get("idproductoreferencia"),
                ):
                    return True
                fam_id = p.get("producto_familiaid")
                if _match_any(q, fam_name.get(fam_id)):
                    return True
            return False

        if q and not _cat_match():
            continue

        total_cat = len(prods_cat)
        fams_cat: Dict[Optional[int], List[dict]] = {}
        for p in prods_cat:
            fam_id = p.get("producto_familiaid")
            fams_cat.setdefault(fam_id, []).append(p)

        label = f"{cat_label} ({total_cat})"
        with st.expander(label, expanded=False):
            if not fams_cat:
                st.info("No hay familias para esta categoria.")
                continue

            fam_items = sorted(
                fams_cat.items(),
                key=lambda x: (fam_name.get(x[0]) or "Sin familia"),
            )

            fam_limit_key = f"tree_fam_limit_{cat_id}"
            st.session_state.setdefault(fam_limit_key, int(step_size))
            fam_limit = st.session_state[fam_limit_key]

            for fam_id, fam_products in fam_items[:fam_limit]:
                fam_label = fam_name.get(fam_id) or "Sin familia"
                if q and not _match_any(q, fam_label) and all(
                    not _match_any(
                        q,
                        p.get("titulo_automatico"),
                        p.get("idproducto"),
                        p.get("idproductoreferencia"),
                    )
                    for p in fam_products
                ):
                    continue

                fam_title = f"Familia: {fam_label} ({len(fam_products)})"
                with st.expander(fam_title, expanded=False):
                    if fam_id:
                        if st.button(
                            "Ver catalogo filtrado",
                            key=f"tree_cat_{cat_id}_fam_{fam_id}",
                            use_container_width=True,
                        ):
                            st.session_state["modo_producto"] = "Catalogo"
                            st.session_state["prod_show_form"] = False
                            st.session_state["prod_familia"] = fam_label
                            st.session_state["prod_page"] = 1
                            st.rerun()

                    q_local = st.text_input(
                        "Buscar productos en esta familia",
                        key=f"tree_q_{cat_id}_{fam_id}",
                    ).strip()

                    limit_key = f"tree_limit_{cat_id}_{fam_id}"
                    st.session_state.setdefault(limit_key, int(step_size))
                    limit = st.session_state[limit_key]

                    if q_local:
                        fam_products = [
                            p
                            for p in fam_products
                            if _match_any(
                                q_local,
                                p.get("titulo_automatico"),
                                p.get("idproducto"),
                                p.get("idproductoreferencia"),
                            )
                        ]

                    for p in fam_products[:limit]:
                        _render_producto_row(p)

                    if len(fam_products) > limit:
                        if st.button(
                            "Mostrar mas",
                            key=f"tree_more_{cat_id}_{fam_id}",
                            use_container_width=True,
                        ):
                            st.session_state[limit_key] = min(
                                len(fam_products),
                                limit + int(step_size),
                            )
                            st.rerun()

            if len(fam_items) > fam_limit:
                if st.button(
                    "Mostrar mas familias",
                    key=f"tree_more_fam_{cat_id}",
                    use_container_width=True,
                ):
                    st.session_state[fam_limit_key] = min(
                        len(fam_items),
                        fam_limit + int(step_size),
                    )
                    st.rerun()

    st.markdown("---")
    if st.button("Volver al catalogo", key="tree_back_catalog", use_container_width=True):
        st.session_state["modo_producto"] = "Catalogo"
        st.session_state["prod_show_form"] = False
        st.rerun()
