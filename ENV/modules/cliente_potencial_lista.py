import os

from datetime import date

from typing import Any, Dict, List, Optional



import pandas as pd

import requests

import streamlit as st

from streamlit.components.v1 import html as st_html



from modules.orbe_theme import apply_orbe_theme

from modules.cliente_form_api import render_cliente_form

from modules.cliente_direccion import render_direccion_form

from modules.cliente_contacto import render_contacto_form

from modules.cliente_observacion import render_observaciones_form
from modules.cliente_crm import render_crm_form
from modules.historial import render_historial



try:

    from streamlit_modal import Modal  # type: ignore

except Exception:

    # Minimal fallback to avoid hard failure if the dependency is missing

    class Modal:  # type: ignore

        def __init__(self, *args, **kwargs):

            pass



        def is_open(self):

            return True



        def open(self):

            return None



        def close(self):

            return None





# =========================================================

# Helpers

# =========================================================

def _safe(v: Any, default: str = "-") -> str:

    return default if v in (None, "", "null") else str(v)





def _bool(v: Any) -> bool:

    if isinstance(v, bool):

        return v

    if isinstance(v, str):

        return v.lower() in ("true", "1", "yes")

    return bool(v)





def _normalize_id(v: Any):

    if isinstance(v, float) and v.is_integer():

        return int(v)

    return v





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

        r = requests.get(f"{_api_base()}{path}", params=params, timeout=25)

        r.raise_for_status()

        return r.json()

    except Exception as e:

        st.error(f"Error API: {e}")

        return {}





def _api_post(path: str, json: Optional[dict] = None) -> Optional[dict]:

    try:

        r = requests.post(f"{_api_base()}{path}", json=json, timeout=25)

        r.raise_for_status()

        return r.json()

    except Exception as e:

        st.error(f"Error API: {e}")

        return None





# =========================================================

# UI principal

# =========================================================

def render_cliente_potencial_lista():

    apply_orbe_theme()



    st.header("Clientes potenciales")

    st.caption("Leads en fase previa. La conversion y las reglas viven en FastAPI.")



    # Formulario de alta

    ctop1, ctop2 = st.columns(2)

    with ctop1:

        if st.button("+ Nuevo potencial"):

            st.session_state["cli_show_form"] = "potencial"

            st.rerun()

    with ctop2:

        if st.button("+ Nuevo cliente"):

            st.session_state["cli_show_form"] = "cliente"

            st.rerun()



    modo_form = st.session_state.get("cli_show_form")

    if modo_form in ("cliente", "potencial"):

        render_cliente_form(modo=modo_form)

        return
    defaults = {
        "pot_page": 1,
        "pot_sort_field": "razonsocial",
        "pot_sort_dir": "ASC",
        "pot_view": "Tarjetas",
        "pot_result_count": 0,
        "pot_table_cols": ["clienteid", "razonsocial", "nombre", "cifdni"],
    }

    for k, v in defaults.items():

        st.session_state.setdefault(k, v)



    # Buscador

    c1, c2 = st.columns([3, 1])

    with c1:

        q = st.text_input(

            "Buscar potencial",

            placeholder="Razon social o CIF/DNI",

            key="pot_q",

        )

        if st.session_state.get("last_pot_q") != q:

            st.session_state["pot_page"] = 1

            st.session_state["last_pot_q"] = q

    with c2:

        st.metric("Resultados", st.session_state["pot_result_count"])



    st.markdown("---")



    # Opciones

    with st.expander("Opciones", expanded=False):
        o1, o2 = st.columns(2)
        with o1:
            st.session_state["pot_view"] = st.radio(
                "Vista",
                ["Tarjetas", "Tabla"],

                horizontal=True,

            )

        with o2:

            st.session_state["pot_sort_field"] = st.selectbox(

                "Ordenar por",

                ["razonsocial", "nombre", "cifdni", "codigocuenta", "codigoclienteoproveedor"],

            )

            st.session_state["pot_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
            )
        if st.session_state["pot_view"] == "Tabla":
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
            st.session_state["pot_table_cols"] = st.multiselect(
                "Columnas a mostrar",
                options=all_cols,
                default=st.session_state.get("pot_table_cols", defaults["pot_table_cols"]),
            )
            st.session_state["pot_sort_field"] = st.selectbox(
                "Ordenar tabla por",
                options=st.session_state["pot_table_cols"] or all_cols,
                key="pot_sort_field_table",
            )
            st.session_state["pot_sort_dir"] = st.radio(
                "Direccion",
                ["ASC", "DESC"],
                horizontal=True,
                key="pot_sort_dir_table",
            )


    # Params API

    page = st.session_state["pot_page"]

    page_size = 30

    params = {

        "tipo": "potencial",

        "q": q or None,

        "page": page,

        "page_size": page_size,

        "sort_field": st.session_state["pot_sort_field"],

        "sort_dir": st.session_state["pot_sort_dir"],

    }



    payload = _api_get("/api/clientes", params=params)

    potenciales: List[Dict[str, Any]] = payload.get("data", [])

    total = payload.get("total", 0)

    total_pages = payload.get("total_pages", 1)

    st.session_state["pot_result_count"] = len(potenciales)



    # Metricas

    m1, m2, m3 = st.columns(3)

    m1.metric("Total", total)

    m2.metric("Pagina", f"{page}/{max(1, total_pages)}")

    m3.metric("Hoy", date.today().strftime("%d/%m/%Y"))



    st.markdown("---")



    if not potenciales:

        st.info("No se encontraron clientes potenciales.")

        return



    # Listado

    if st.session_state["pot_view"] == "Tabla":

        cols_sel = st.session_state.get("pot_table_cols") or defaults["pot_table_cols"]

        rows = []

        for c in potenciales:

            row = {}

            for col in cols_sel:

                val = c.get(col)

                row[col] = val

            rows.append(row)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    else:

        cols = st.columns(3)

        for i, c in enumerate(potenciales):

            with cols[i % 3]:

                _render_potencial_card(c)



    # Paginacion

    st.markdown("---")

    p1, p2, p3 = st.columns(3)

    with p1:

        if st.button("Anterior", disabled=page <= 1):

            st.session_state["pot_page"] = page - 1

            st.rerun()

    with p2:

        st.write(f"Pagina {page} / {max(1, total_pages)}  -  Total: {total}")

    with p3:

        if st.button("Siguiente", disabled=page >= total_pages):

            st.session_state["pot_page"] = page + 1

            st.rerun()



    # Modal detalle

    sel = st.session_state.get("pot_detalle_id")

    if sel:

        _render_modal_detalle_potencial(sel)





# =========================================================

# Cards y modal

# =========================================================

def _render_potencial_card(c: Dict[str, Any]):
    cid = c.get("clienteid")
    razon = _safe(c.get("razonsocial") or c.get("nombre"))
    cif = _safe(c.get("cifdni"))
    tipo = c.get("clienteoproveedor") or "potencial"
    grupo = c.get("idgrupo") or "-"
    codcta = _safe(c.get("codigocuenta"))
    codcp = _safe(c.get("codigoclienteoproveedor"))

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:14px;
                    background:#f9fafb;padding:14px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:1.05rem;font-weight:700;">{razon}</div>
                    <div style="color:#6b7280;font-size:.9rem;">{cif}</div>
                </div>
                <div style="font-weight:700;color:#3b82f6;">{tipo}</div>
            </div>
            <div style="margin-top:10px;font-size:.9rem;">
                <b>ID:</b> {cid}<br>
                <b>Grupo:</b> {grupo}<br>
                <b>Codigo cuenta:</b> {codcta}<br>
                <b>Codigo cliente/proveedor:</b> {codcp}<br>
            </div>
        </div>
        """,
        height=210,
    )

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Ficha", key=f"pot_ficha_{cid}", use_container_width=True):
            st.session_state["pot_detalle_id"] = cid
            st.rerun()

    with b2:
        if st.button(
            "Convertir",
            disabled=tipo != "potencial",
            key=f"pot_convert_{cid}",
            use_container_width=True,
        ):
            with st.spinner("Convirtiendo..."):
                res = _api_post(f"/api/clientes/{cid}/convertir")
            if res:
                st.success(res.get("mensaje", "Cliente convertido"))
                st.rerun()


def _render_modal_detalle_potencial(clienteid: int):
    modal = Modal(key=f"modal_pot_{clienteid}", title=f"Ficha potencial {clienteid}", max_width=900)

    if modal.is_open():
        try:
            res = requests.get(f"{_api_base()}/api/clientes/{clienteid}", timeout=20)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            st.error(f"Error cargando ficha: {e}")
            if st.button("Cerrar", key=f"cerrar_pot_err_{clienteid}"):
                st.session_state["pot_detalle_id"] = None
                modal.close()
                st.rerun()
            modal.close()
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

        with tabs[1]:
            render_direccion_form(clienteid, key_prefix="pot_modal_")
        with tabs[2]:
            render_contacto_form(clienteid, key_prefix="pot_modal_")
        with tabs[3]:
            render_observaciones_form(clienteid, key_prefix="pot_modal_")
        with tabs[4]:
            render_crm_form(int(clienteid))
        with tabs[5]:
            supa = st.session_state.get("supa")
            if not supa:
                st.warning("No hay conexion a base de datos.")
            else:
                st.session_state["cliente_actual"] = int(clienteid)
                render_historial(supa)

        if st.button("Cerrar ficha", key=f"cerrar_pot_{clienteid}", use_container_width=True):
            st.session_state["pot_detalle_id"] = None
            modal.close()
            st.rerun()

    modal.open()


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
