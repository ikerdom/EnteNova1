import os
import math
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return []


def api_post(path: str, payload: Optional[dict] = None):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_put(path: str, payload: dict):
    try:
        r = requests.put(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{api_base()}{path}", timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def render_direccion_form(clienteid: int, key_prefix: str = ""):
    clienteid = int(clienteid)
    kp = key_prefix or ""

    st.subheader("Direcciones del cliente")
    st.caption("Direcciones fiscales y de envio asociadas al cliente.")

    direcciones: List[Dict[str, Any]] = api_get(
        f"/api/clientes/{clienteid}/direcciones"
    )

    with st.expander("Agregar nueva direccion"):
        _direccion_editor(clienteid, None, key_prefix=kp)

    if not direcciones:
        st.info("Este cliente no tiene direcciones registradas.")
        return

    search = st.text_input("Buscar direccion", key=f"{kp}buscar_dir_{clienteid}")
    if search:
        s = search.lower()
        campos = [
            "razonsocial",
            "nombrecomercial",
            "direccionfiscal",
            "direccion",
            "municipio",
            "codigopostal",
            "idprovincia",
            "idpais",
            "cif",
            "referenciacliente",
        ]

        def _match(d: Dict[str, Any]) -> bool:
            text = " ".join(str(d.get(c, "") or "") for c in campos)
            return s in text.lower()

        direcciones = [d for d in direcciones if _match(d)]

    page_key = f"{kp}dir_page_{clienteid}"
    page = int(st.session_state.get(page_key, 1))
    page_size = 10
    total = len(direcciones)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(max(page, 1), total_pages)
    st.session_state[page_key] = page

    start = (page - 1) * page_size
    end = start + page_size
    page_dirs = direcciones[start:end]

    for d in page_dirs:
        dir_id = d.get("clientes_direccionid")

        with st.container(border=True):
            st.write(f"Direccion: {_safe(d.get('direccion') or d.get('direccionfiscal'))}")
            st.write(f"Municipio: {_safe(d.get('municipio'))}")
            st.write(f"Codigo postal: {_safe(d.get('codigopostal'))}")
            st.write(f"Provincia: {_safe(d.get('idprovincia'))}")
            st.write(f"Pais: {_safe(d.get('idpais'))}")

            if d.get("razonsocial") or d.get("nombrecomercial"):
                st.write(
                    f"Razon social: {_safe(d.get('razonsocial'))} | "
                    f"Nombre comercial: {_safe(d.get('nombrecomercial'))}"
                )
            if d.get("cif"):
                st.write(f"CIF: {d.get('cif')}")
            if d.get("referenciacliente"):
                st.write(f"Referencia cliente: {d.get('referenciacliente')}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Editar", key=f"{kp}edit_dir_{dir_id}", use_container_width=True):
                st.session_state[f"{kp}edit_dir_{dir_id}"] = not st.session_state.get(
                    f"{kp}edit_dir_{dir_id}", False
                )
        with c2:
            if st.button("Eliminar", key=f"{kp}del_dir_{dir_id}", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/direcciones/{dir_id}")
                st.toast("Direccion eliminada.")
                st.rerun()

        if st.session_state.get(f"{kp}edit_dir_{dir_id}"):
            with st.expander("Editar direccion", expanded=True):
                _direccion_editor(clienteid, d, key_prefix=kp)

    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1, key=f"{kp}dir_prev_{clienteid}"):
            st.session_state[page_key] = page - 1
            st.rerun()
    with p2:
        st.write(f"Pagina {page} / {total_pages} - Total: {total}")
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages, key=f"{kp}dir_next_{clienteid}"):
            st.session_state[page_key] = page + 1
            st.rerun()


def _direccion_editor(
    clienteid: int,
    d: Optional[Dict[str, Any]] = None,
    key_prefix: str = "",
):
    is_new = d is None
    dir_id = (d or {}).get("clientes_direccionid")
    prefix = f"{key_prefix}dir_{dir_id or 'new'}"

    def field(key: str, label: str, default: str = ""):
        k = f"{prefix}_{key}"
        st.session_state.setdefault(k, (d or {}).get(key, default) or "")
        return st.text_input(label, key=k)

    razonsocial = field("razonsocial", "Razon social")
    nombrecomercial = field("nombrecomercial", "Nombre comercial")
    cif = field("cif", "CIF")
    direccionfiscal = field("direccionfiscal", "Direccion fiscal")
    direccion = field("direccion", "Direccion")
    municipio = field("municipio", "Municipio")
    codigopostal = field("codigopostal", "Codigo postal")
    idprovincia = field("idprovincia", "Provincia (codigo)")
    idpais = field("idpais", "Pais (codigo)")
    referenciacliente = field("referenciacliente", "Referencia cliente")

    # Buscar datos por codigo postal
    st.markdown("Buscar por codigo postal")
    cp_key = f"{prefix}_cp_search"
    res_key = f"{prefix}_cp_results"
    st.session_state.setdefault(cp_key, codigopostal or "")
    cp_search = st.text_input("Codigo postal a buscar", key=cp_key)
    if st.button("Buscar CP", key=f"{prefix}_cp_btn"):
        if not cp_search.strip():
            st.warning("Introduce un codigo postal.")
        else:
            results = api_get("/api/postal/buscar", params={"cp": cp_search.strip()})
            st.session_state[res_key] = results or []

    results = st.session_state.get(res_key) or []
    if results:
        options = []
        for r in results:
            cp = r.get("codigo_postal") or "-"
            muni = r.get("municipio") or "-"
            prov = r.get("provincia_nombre_raw") or "-"
            options.append(f"{cp} - {muni} ({prov})")
        sel = st.selectbox("Resultados", options=options, key=f"{prefix}_cp_sel")
        if st.button("Aplicar datos", key=f"{prefix}_cp_apply"):
            idx = options.index(sel)
            row = results[idx]
            st.session_state[f"{prefix}_codigopostal"] = row.get("codigo_postal") or ""
            st.session_state[f"{prefix}_municipio"] = row.get("municipio") or ""
            st.session_state[f"{prefix}_idprovincia"] = row.get("provincia_nombre_raw") or ""
            if not st.session_state.get(f"{prefix}_idpais"):
                st.session_state[f"{prefix}_idpais"] = "ES"

    payload = {
        "razonsocial": razonsocial.strip() or None,
        "nombrecomercial": nombrecomercial.strip() or None,
        "cif": cif.strip() or None,
        "direccionfiscal": direccionfiscal.strip() or None,
        "direccion": direccion.strip() or None,
        "municipio": municipio.strip() or None,
        "codigopostal": codigopostal.strip() or None,
        "idprovincia": idprovincia.strip() or None,
        "idpais": idpais.strip() or None,
        "referenciacliente": referenciacliente.strip() or None,
    }

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Guardar", key=f"{prefix}_save", use_container_width=True):
            if is_new:
                api_post(f"/api/clientes/{clienteid}/direcciones", payload)
                st.toast("Direccion creada.")
            else:
                api_put(f"/api/clientes/{clienteid}/direcciones/{dir_id}", payload)
                st.toast("Direccion guardada.")
            st.rerun()

    with c2:
        if not is_new:
            if st.button("Eliminar", key=f"{prefix}_delete", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/direcciones/{dir_id}")
                st.toast("Direccion eliminada.")
                st.rerun()
