import streamlit as st
from datetime import date


def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def render_albaran_form(supabase, clienteid: int):
    st.markdown("### Albaranes del cliente")
    st.caption("Listado paginado con buscador y filtros basicos.")

    supa = supabase or st.session_state.get("supa")
    if not supa:
        st.warning("No hay conexion a base de datos.")
        return

    st.session_state.setdefault(f"alb_page_size_{clienteid}", 10)
    st.session_state.setdefault(f"alb_limit_{clienteid}", st.session_state[f"alb_page_size_{clienteid}"])
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

    if q != st.session_state[f"alb_last_q_{clienteid}"]:
        st.session_state[f"alb_limit_{clienteid}"] = st.session_state[f"alb_page_size_{clienteid}"]
        st.session_state[f"alb_last_q_{clienteid}"] = q

    page_size = st.selectbox(
        "Ver por defecto",
        options=[10, 30, 50],
        index=[10, 30, 50].index(st.session_state[f"alb_page_size_{clienteid}"]),
        key=f"alb_page_size_sel_{clienteid}",
    )
    if page_size != st.session_state[f"alb_page_size_{clienteid}"]:
        st.session_state[f"alb_page_size_{clienteid}"] = page_size
        st.session_state[f"alb_limit_{clienteid}"] = page_size

    limit = st.session_state[f"alb_limit_{clienteid}"]

    try:
        query = (
            supa.table("albaran")
            .select(
                "albaran_id, numero, serie, estado, fecha_albaran, total_general, "
                "empresa_id, empresa(empresa_nombre), forma_pagoid, forma_pago(forma_pago_nombre), "
                "albaran_estadoid, albaran_estado(estado), tipo_documento, cliente, cif_cliente, "
                "cuenta_cliente_proveedor"
            )
            .eq("clienteid", int(clienteid))
            .order("fecha_albaran", desc=True)
        )

        if q:
            q_safe = q.replace(",", " ")
            if q_safe.isdigit():
                query = query.or_(
                    f"numero.eq.{q_safe},serie.ilike.%{q_safe}%,"
                    f"estado.ilike.%{q_safe}%,forma_de_pago.ilike.%{q_safe}%,"
                    f"cliente.ilike.%{q_safe}%,cif_cliente.ilike.%{q_safe}%,"
                    f"cuenta_cliente_proveedor.ilike.%{q_safe}%"
                )
            else:
                query = query.or_(
                    f"serie.ilike.%{q_safe}%,estado.ilike.%{q_safe}%,"
                    f"forma_de_pago.ilike.%{q_safe}%,cliente.ilike.%{q_safe}%,"
                    f"cif_cliente.ilike.%{q_safe}%,cuenta_cliente_proveedor.ilike.%{q_safe}%"
                )

        if use_desde:
            query = query.gte("fecha_albaran", str(fecha_desde))
        if use_hasta:
            query = query.lte("fecha_albaran", str(fecha_hasta))

        res = query.range(0, limit - 1).execute()
        rows = res.data or []
    except Exception as e:
        st.error(f"Error cargando albaranes: {e}")
        return

    if not rows:
        st.info("No hay albaranes para este cliente.")
        return

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
    st.subheader("Lineas de albaran")
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
        "Columnas lineas",
        options=line_cols,
        default=st.session_state[f"alb_line_cols_{clienteid}"],
        key=f"alb_line_cols_sel_{clienteid}",
    )
    st.session_state[f"alb_line_cols_{clienteid}"] = line_cols_sel
    line_q = st.text_input(
        "Buscar en lineas",
        placeholder="Descripcion o referencia de producto...",
        key=f"alb_line_q_{clienteid}",
    )

    for r in rows:
        alb_id = r.get("albaran_id")
        numero = _safe(r.get("numero"))
        serie = _safe(r.get("serie"))
        fecha = _safe(r.get("fecha_albaran"))
        with st.expander(f"Albaran {numero} {serie} | {fecha}"):
            try:
                lineas = (
                    supa.table("albaran_linea")
                    .select(
                        "linea_id, albaran_id, descripcion, cantidad, precio, descuento_pct, "
                        "precio_tras_dto, subtotal, tasa_impuesto, cuota_impuesto, tasa_recargo, "
                        "cuota_recargo, producto_id_origen, producto_ref_origen, idproducto, producto_id"
                    )
                    .eq("albaran_id", alb_id)
                    .order("linea_id")
                    .execute()
                    .data
                    or []
                )
            except Exception as e:
                st.error(f"Error cargando lineas del albaran {alb_id}: {e}")
                continue

            if not lineas:
                st.info("Sin lineas.")
                continue
            if line_q:
                q_low = line_q.lower()

                def _match(linea):
                    for k in [
                        "descripcion",
                        "producto_ref_origen",
                        "producto_id_origen",
                        "idproducto",
                        "producto_id",
                    ]:
                        if q_low in str(linea.get(k, "")).lower():
                            return True
                    return False

                lineas = [l for l in lineas if _match(l)]
                if not lineas:
                    st.info("Sin lineas que coincidan con el filtro.")
                    continue

            if line_cols_sel:
                import pandas as pd

                df_lines = pd.DataFrame(lineas)
                st.dataframe(df_lines[line_cols_sel], use_container_width=True, hide_index=True)

    if len(rows) >= limit:
        if st.button("Ver mas", key=f"alb_more_{clienteid}"):
            st.session_state[f"alb_limit_{clienteid}"] = (
                limit + st.session_state[f"alb_page_size_{clienteid}"]
            )
            st.rerun()
