import requests
import streamlit as st
from datetime import date

from modules.api_base import get_api_base


def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def _api_get(path: str, params: dict | None = None):
    r = requests.get(f"{get_api_base()}{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def render_albaran_form(_supabase_unused, clienteid: int):
    st.markdown("### Albaranes del cliente")
    st.caption("Listado paginado con buscador y filtros básicos (vía API).")

    st.session_state.setdefault(f"alb_page_size_{clienteid}", 10)
    st.session_state.setdefault(f"alb_last_q_{clienteid}", "")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        q = st.text_input(
            "Buscar",
            placeholder="Numero, serie, estado, forma de pago, cliente, CIF...",
            key=f"alb_q_{clienteid}",
        )
    with c2:
        use_desde = st.checkbox("Desde", key=f"alb_use_desde_{clienteid}")
        fecha_desde = st.date_input(
            "Fecha desde",
            key=f"alb_desde_{clienteid}",
            value=date.today(),
            disabled=not use_desde,
            label_visibility="collapsed",
        )
    with c3:
        use_hasta = st.checkbox("Hasta", key=f"alb_use_hasta_{clienteid}")
        fecha_hasta = st.date_input(
            "Fecha hasta",
            key=f"alb_hasta_{clienteid}",
            value=date.today(),
            disabled=not use_hasta,
            label_visibility="collapsed",
        )

    f1, f2, f3 = st.columns(3)
    with f1:
        filtro_estado = st.text_input(
            "Estado",
            placeholder="Ej: pendiente",
            key=f"alb_estado_{clienteid}",
        )
    with f2:
        filtro_tipo = st.text_input(
            "Tipo doc",
            placeholder="Ej: ALB",
            key=f"alb_tipo_{clienteid}",
        )
    with f3:
        ordenar_por = st.selectbox(
            "Ordenar por",
            ["fecha_albaran", "numero", "albaran_id"],
            key=f"alb_sort_{clienteid}",
        )

    page_size = st.selectbox(
        "Ver por página",
        options=[10, 30, 50],
        index=[10, 30, 50].index(st.session_state[f"alb_page_size_{clienteid}"]),
        key=f"alb_page_size_sel_{clienteid}",
    )
    st.session_state[f"alb_page_size_{clienteid}"] = page_size

    page_key = f"alb_page_{clienteid}"
    st.session_state.setdefault(page_key, 1)
    page = st.session_state.get(page_key, 1)

    try:
        params = {
            "q": q or None,
            "fecha_desde": str(fecha_desde) if use_desde else None,
            "fecha_hasta": str(fecha_hasta) if use_hasta else None,
            "estado": filtro_estado or None,
            "tipo_documento": filtro_tipo or None,
            "ordenar_por": ordenar_por,
            "page": page,
            "page_size": page_size,
        }
        payload = _api_get(f"/api/clientes/{clienteid}/albaranes", params=params)
        rows = payload.get("data", [])
        total = payload.get("total", 0)
    except Exception as e:
        st.error(f"Error cargando albaranes: {e}")
        return

    if not rows:
        st.info("No hay albaranes para este cliente.")
        return

    total_pages = max(1, int((total + page_size - 1) / page_size)) if total else 1

    total_alb = len(rows)
    total_imp = sum([r.get("total_general") or 0 for r in rows if isinstance(r.get("total_general"), (int, float))])
    m1, m2, m3 = st.columns(3)
    m1.metric("Albaranes", total_alb)
    m2.metric("Importe total (visible)", f"{total_imp:,.2f}")
    if rows:
        m3.metric("Última fecha", str(rows[0].get("fecha_albaran") or "-")[:10])

    col_options = [
        "albaran_id",
        "numero",
        "serie",
        "tipo_documento",
        "estado",
        "fecha_albaran",
        "total_general",
        "cliente",
        "cif_cliente",
        "cuenta_cliente_proveedor",
        "empresa_nombre",
        "forma_pago_nombre",
    ]
    st.session_state.setdefault(
        f"alb_cols_{clienteid}",
        ["albaran_id", "numero", "serie", "fecha_albaran", "estado", "total_general"],
    )
    cols_sel = st.multiselect(
        "Columnas albaran",
        options=col_options,
        default=st.session_state[f"alb_cols_{clienteid}"],
        key=f"alb_cols_sel_{clienteid}",
    )
    st.session_state[f"alb_cols_{clienteid}"] = cols_sel

    table_rows = []
    for r in rows:
        table_rows.append(
            {
                "albaran_id": r.get("albaran_id"),
                "numero": r.get("numero"),
                "serie": r.get("serie"),
                "tipo_documento": r.get("tipo_documento"),
                "estado": (r.get("albaran_estado") or {}).get("estado") or r.get("estado"),
                "fecha_albaran": r.get("fecha_albaran"),
                "total_general": r.get("total_general"),
                "cliente": r.get("cliente"),
                "cif_cliente": r.get("cif_cliente"),
                "cuenta_cliente_proveedor": r.get("cuenta_cliente_proveedor"),
                "empresa_nombre": (r.get("empresa") or {}).get("empresa_nombre"),
                "forma_pago_nombre": (r.get("forma_pago") or {}).get("forma_pago_nombre"),
            }
        )

    if cols_sel:
        import pandas as pd

        df = pd.DataFrame(table_rows)
        st.dataframe(df[cols_sel], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Líneas de albarán")
    line_cols = [
        "linea_id",
        "albaran_id",
        "descripcion",
        "cantidad",
        "precio",
        "descuento_pct",
        "precio_tras_dto",
        "subtotal",
        "tasa_impuesto",
        "cuota_impuesto",
        "tasa_recargo",
        "cuota_recargo",
        "producto_id_origen",
        "producto_ref_origen",
        "idproducto",
        "producto_id",
    ]
    st.session_state.setdefault(
        f"alb_line_cols_{clienteid}",
        ["descripcion", "cantidad", "precio", "subtotal"],
    )
    line_cols_sel = st.multiselect(
        "Columnas líneas",
        options=line_cols,
        default=st.session_state[f"alb_line_cols_{clienteid}"],
        key=f"alb_line_cols_sel_{clienteid}",
    )
    st.session_state[f"alb_line_cols_{clienteid}"] = line_cols_sel
    line_q = st.text_input(
        "Buscar en líneas",
        placeholder="Descripción o referencia de producto...",
        key=f"alb_line_q_{clienteid}",
    )

    for r in rows:
        alb_id = r.get("albaran_id")
        numero = _safe(r.get("numero"))
        serie = _safe(r.get("serie"))
        fecha = _safe(r.get("fecha_albaran"))
        with st.expander(f"Albarán {numero} {serie} | {fecha}"):
            try:
                lineas = _api_get(f"/api/albaranes/{alb_id}/lineas", params={"q": line_q or None})
            except Exception as e:
                st.error(f"Error cargando líneas del albarán {alb_id}: {e}")
                continue

            if not lineas:
                st.info("Sin líneas.")
                continue

            if line_cols_sel:
                import pandas as pd

                df_lines = pd.DataFrame(lineas)
                st.dataframe(df_lines[line_cols_sel], use_container_width=True, hide_index=True)

    st.markdown("---")
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1, key=f"alb_prev_{clienteid}"):
            st.session_state[page_key] = page - 1
            st.rerun()
    with p2:
        st.write(f"Página {page} / {total_pages} · Total: {total}")
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages, key=f"alb_next_{clienteid}"):
            st.session_state[page_key] = page + 1
            st.rerun()
