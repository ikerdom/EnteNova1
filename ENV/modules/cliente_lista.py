from typing import Any, Dict, Optional, List


import math


import pandas as pd


import requests


import streamlit as st







from modules.orbe_theme import apply_orbe_theme


from modules.cliente_form_api import render_cliente_form


from modules.cliente_direccion import render_direccion_form


from modules.cliente_contacto import render_contacto_form


from modules.cliente_observacion import render_observaciones_form
from modules.cliente_albaran_form import render_albaran_form
from modules.cliente_crm import render_crm_form
from modules.historial import render_historial





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


    try:


        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]


    except Exception:


        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"








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





    # Lanzar formularios de alta


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
        "cli_table_cols": ["clienteid", "razonsocial", "nombre", "cifdni"],
    }

    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    cli_catalogos = _api_get("/api/clientes/catalogos")
    grupos = {c["label"]: c["id"] for c in cli_catalogos.get("grupos", [])}


    # Buscador





    c1, c2 = st.columns([3, 1])


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


        st.metric("Resultados", st.session_state["cli_result_count"])





    st.markdown("---")





    # Ficha seleccionada arriba


    sel = st.session_state.get("cliente_detalle_id")


    if sel:


        _render_ficha_panel(sel)


        st.markdown("---")





    # Opciones
    with st.expander("Opciones", expanded=False):
        o1, o2 = st.columns(2)
        with o1:
            st.session_state["cli_view"] = st.radio(
                "Vista",
                ["Tarjetas", "Tabla"],
                horizontal=True,
            )
        with o2:
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar por",
                ["razonsocial", "nombre", "cifdni", "codigocuenta", "codigoclienteoproveedor"],
            )
            st.session_state["cli_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
            )

        f3, f4 = st.columns(2)
        with f3:
            st.session_state["cli_tipo_filtro"] = st.selectbox(
                "Tipo cliente/proveedor",
                ["Todos", "CLIENTE", "PROVEEDOR", "AMBOS"],
            )
        with f4:
            grupo_labels = ["Todos"] + list(grupos.keys())
            st.session_state["cli_grupo_filtro"] = st.selectbox("Grupo", grupo_labels)

        if st.session_state["cli_view"] == "Tabla":
            all_cols = [
                "clienteid",
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


    # Carga API



    page = st.session_state["cli_page"]


    page_size = 30


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





    # Tabla / Tarjetas


    if st.session_state["cli_view"] == "Tabla":


        cols_sel = st.session_state.get("cli_table_cols") or defaults["cli_table_cols"]


        rows = []


        for c in clientes:


            row = {}


            for col in cols_sel:


                val = c.get(col)


                row[col] = val


            rows.append(row)


        df = pd.DataFrame(rows)


        st.dataframe(df, use_container_width=True, hide_index=True)


    else:


        cols = st.columns(3)


        for i, c in enumerate(clientes):


            with cols[i % 3]:


                _render_card(c)





    # Paginacion


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





    # Detalle modal si seleccionado





def _render_card(c: Dict[str, Any]):
    razon = _safe(c.get("razonsocial") or c.get("nombre"))
    ident = _safe(c.get("cifdni"))
    grupo = c.get("idgrupo", "-")
    tipo = c.get("clienteoproveedor") or "-"
    codcta = _safe(c.get("codigocuenta"))
    codcp = _safe(c.get("codigoclienteoproveedor"))

    with st.container(border=True):
        st.write(f"Cliente: {razon}")
        st.caption(ident)
        st.write(f"Tipo: {tipo}")
        st.write(f"Grupo ID: {grupo}")
        st.write(f"Codigo cuenta: {codcta}")
        st.write(f"Codigo cliente/proveedor: {codcp}")

    cid = c.get("clienteid")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Ficha", key=f"cli_ficha_{cid}", use_container_width=True):
            st.session_state["cliente_detalle_id"] = cid
            st.rerun()
    with b2:
        if st.button("Editar", key=f"cli_edit_{cid}", use_container_width=True):
            st.session_state["cli_show_form"] = "cliente"
            st.session_state["cliente_actual"] = cid
            st.rerun()
    st.caption(f"ID {cid}")


def _render_ficha_panel(clienteid: int):
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.subheader(f"Ficha cliente {clienteid}")
        with c2:
            if st.button("Cerrar ficha", key=f"cerrar_cli_top_{clienteid}", use_container_width=True):
                st.session_state["cliente_detalle_id"] = None
                st.rerun()

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
                "Albaranes",
                "CRM",
                "Historial",
            ]
        )
        with tabs[0]:
            st.write(f"**Razon social:** {cli.get('razonsocial') or cli.get('nombre') or '-'}")
            st.write(f"**CIF/DNI:** {cli.get('cifdni') or '-'}")
            st.write(f"**Codigo cuenta:** {cli.get('codigocuenta') or '-'}")
            st.write(f"**Codigo cliente/proveedor:** {cli.get('codigoclienteoproveedor') or '-'}")
            st.write(f"**Tipo:** {cli.get('clienteoproveedor') or '-'}")
            st.write(f"**Grupo ID:** {cli.get('idgrupo') or '-'}")
            with st.expander("Direccion", expanded=False):
                _render_dir_summary(df)
            with st.expander("Contacto principal", expanded=False):
                st.write(cp or {})

        st.markdown("---")
        if st.button("Crear presupuesto para este cliente", key=f"cli_pres_{clienteid}", use_container_width=True):
            st.session_state["pres_cli_prefill"] = int(clienteid)
            st.session_state["show_creator"] = True
            st.session_state["menu_principal"] = "?? Gestion de presupuestos"
            st.rerun()
        with tabs[1]:
            render_direccion_form(clienteid, key_prefix="panel_")
        with tabs[2]:
            render_contacto_form(clienteid, key_prefix="panel_")
        with tabs[3]:
            render_observaciones_form(clienteid, key_prefix="panel_")
        with tabs[4]:
            supa = st.session_state.get("supa")
            render_albaran_form(supa, int(clienteid))
        with tabs[5]:
            render_crm_form(int(clienteid))
        with tabs[6]:
            supa = st.session_state.get("supa")
            if not supa:
                st.warning("No hay conexion a base de datos.")
            else:
                st.session_state["cliente_actual"] = int(clienteid)
                render_historial(supa)

        if st.button("Cerrar ficha", key=f"cerrar_cli_{clienteid}", use_container_width=True):
            st.session_state["cliente_detalle_id"] = None
            st.rerun()


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

