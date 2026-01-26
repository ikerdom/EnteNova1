import os
import requests
import streamlit as st


def _api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def _api_get(path: str, params=None):
    r = requests.get(f"{_api_base()}{path}", params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def _api_post(path: str, json=None):
    r = requests.post(f"{_api_base()}{path}", json=json, timeout=40)
    r.raise_for_status()
    return r.json()


def _api_put(path: str, json=None):
    r = requests.put(f"{_api_base()}{path}", json=json, timeout=40)
    r.raise_for_status()
    return r.json()


def _init_value(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value if value is not None else ""


def render_cliente_form(modo: str = "cliente"):
    """Formulario de alta de cliente/potencial (schema nuevo)."""
    is_potencial = modo == "potencial"
    cliente_id = st.session_state.get("cliente_actual") if not is_potencial else None
    is_edit = bool(cliente_id)
    key_prefix = f"{modo}_edit_{cliente_id}" if is_edit else modo

    st.title("Editar cliente" if is_edit else ("Nuevo cliente potencial" if is_potencial else "Nuevo cliente"))
    st.caption(
        "Alta rapida de cliente potencial (perfil incompleto permitido)."
        if is_potencial
        else ("Actualiza los datos del cliente seleccionado." if is_edit else "Alta completa del cliente en el sistema.")
    )

    try:
        cats = _api_get("/api/clientes/catalogos")
    except Exception as e:
        st.error(f"No se pudieron cargar catalogos desde API: {e}")
        return

    grupos = {i["label"]: i["id"] for i in (cats.get("grupos") or [])}

    cliente_base = {}
    if is_edit:
        try:
            detalle = _api_get(f"/api/clientes/{cliente_id}")
            cliente_base = detalle.get("cliente") or {}
        except Exception as e:
            st.error(f"No se pudieron cargar los datos del cliente: {e}")
            cliente_base = {}

    with st.expander("Informacion general", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            _init_value(f"{key_prefix}_razon", cliente_base.get("razonsocial"))
            _init_value(f"{key_prefix}_nombre", cliente_base.get("nombre"))
            _init_value(f"{key_prefix}_cif", cliente_base.get("cifdni"))
            _init_value(f"{key_prefix}_codcta", cliente_base.get("codigocuenta"))
            _init_value(f"{key_prefix}_codcp", cliente_base.get("codigoclienteoproveedor"))
            razonsocial = st.text_input("Razon social", key=f"{key_prefix}_razon")
            nombre = st.text_input("Nombre", key=f"{key_prefix}_nombre")
            cifdni = st.text_input("CIF/DNI", key=f"{key_prefix}_cif")
            codigocuenta = st.text_input("Codigo cuenta", key=f"{key_prefix}_codcta")
            codigoclienteoproveedor = st.text_input(
                "Codigo cliente/proveedor", key=f"{key_prefix}_codcp"
            )
        with c2:
            tipo_opts = ["", "cliente", "proveedor", "potencial"]
            tipo_default = "potencial" if is_potencial else "cliente"
            tipo_default = cliente_base.get("clienteoproveedor") or tipo_default
            tipo_index = tipo_opts.index(tipo_default) if tipo_default in tipo_opts else 0
            clienteoproveedor = st.selectbox(
                "Tipo", tipo_opts, index=tipo_index
            )
            grupo_labels = ["(Sin grupo)"] + list(grupos.keys())
            grupo_default = "(Sin grupo)"
            if cliente_base.get("idgrupo") is not None:
                for label, gid in grupos.items():
                    if gid == cliente_base.get("idgrupo"):
                        grupo_default = label
                        break
            grupo_index = grupo_labels.index(grupo_default) if grupo_default in grupo_labels else 0
            grupo_nombre = st.selectbox(
                "Grupo", grupo_labels, key=f"{key_prefix}_grupo", index=grupo_index
            )
            _init_value(f"{key_prefix}_tel", cliente_base.get("telefono"))
            _init_value(f"{key_prefix}_tel2", cliente_base.get("telefono2"))
            _init_value(f"{key_prefix}_tel3", cliente_base.get("telefono3"))
            _init_value(f"{key_prefix}_fax", cliente_base.get("fax"))
            telefono = st.text_input("Telefono", key=f"{key_prefix}_tel")
            telefono2 = st.text_input("Telefono 2", key=f"{key_prefix}_tel2")
            telefono3 = st.text_input("Telefono 3", key=f"{key_prefix}_tel3")
            fax = st.text_input("Fax", key=f"{key_prefix}_fax")

    with st.expander("Direccion", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            _init_value(f"{key_prefix}_via", cliente_base.get("viapublica"))
            _init_value(f"{key_prefix}_dom", cliente_base.get("domicilio"))
            _init_value(f"{key_prefix}_mun", cliente_base.get("municipio"))
            viapublica = st.text_input("Via publica", key=f"{key_prefix}_via")
            domicilio = st.text_input("Domicilio", key=f"{key_prefix}_dom")
            municipio = st.text_input("Municipio", key=f"{key_prefix}_mun")
        with d2:
            _init_value(f"{key_prefix}_cp", cliente_base.get("codigopostal"))
            _init_value(f"{key_prefix}_prov", cliente_base.get("provincia"))
            _init_value(f"{key_prefix}_pais", cliente_base.get("idpais") or "ES")
            codigopostal = st.text_input("Codigo postal", key=f"{key_prefix}_cp")
            provincia = st.text_input("Provincia", key=f"{key_prefix}_prov")
            idpais = st.text_input("Pais (ID)", key=f"{key_prefix}_pais")

    with st.expander("Contacto principal", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            _init_value(f"{key_prefix}_c_nom", "")
            _init_value(f"{key_prefix}_c_mail", "")
            contacto_nombre = st.text_input("Nombre contacto", key=f"{key_prefix}_c_nom")
            contacto_email = st.text_input("Email contacto", key=f"{key_prefix}_c_mail")
        with c2:
            _init_value(f"{key_prefix}_c_tel", "")
            contacto_tel = st.text_input("Telefono contacto", key=f"{key_prefix}_c_tel")

    if not is_potencial:
        with st.expander("Datos bancarios", expanded=False):
            _init_value(f"{key_prefix}_iban", cliente_base.get("iban"))
            _init_value(f"{key_prefix}_banco", cliente_base.get("codigobanco"))
            _init_value(f"{key_prefix}_agencia", cliente_base.get("codigoagencia"))
            _init_value(f"{key_prefix}_dc", cliente_base.get("dc"))
            _init_value(f"{key_prefix}_ccc", cliente_base.get("ccc"))
            iban = st.text_input("IBAN", key=f"{key_prefix}_iban")
            codigobanco = st.text_input("Codigo banco", key=f"{key_prefix}_banco")
            codigoagencia = st.text_input("Codigo agencia", key=f"{key_prefix}_agencia")
            dc = st.text_input("DC", key=f"{key_prefix}_dc")
            ccc = st.text_input("CCC", key=f"{key_prefix}_ccc")
    else:
        iban = codigobanco = codigoagencia = dc = ccc = None

    with st.expander("Efectos", expanded=False):
        _init_value(f"{key_prefix}_cte", cliente_base.get("codigotipoefecto"))
        _init_value(f"{key_prefix}_cce", cliente_base.get("codigocuentaefecto"))
        _init_value(f"{key_prefix}_cci", cliente_base.get("codigocuentaimpagado"))
        _init_value(f"{key_prefix}_remesa", cliente_base.get("remesahabitual"))
        codigotipoefecto = st.text_input("Codigo tipo efecto", key=f"{key_prefix}_cte")
        codigocuentaefecto = st.text_input("Codigo cuenta efecto", key=f"{key_prefix}_cce")
        codigocuentaimpagado = st.text_input("Codigo cuenta impagado", key=f"{key_prefix}_cci")
        remesahabitual = st.text_input("Remesa habitual", key=f"{key_prefix}_remesa")

    colg, colx = st.columns([3, 1])
    guardar_label = "Guardar cambios" if is_edit else "Guardar"
    guardar = colg.button(guardar_label, use_container_width=True, key=f"{key_prefix}_guardar")
    cancelar = colx.button("Salir", use_container_width=True, key=f"{key_prefix}_cancelar")

    if cancelar:
        st.session_state["cli_show_form"] = None
        st.rerun()

    if guardar:
        if not (razonsocial or nombre):
            st.warning("Razon social o nombre son obligatorios.")
            return

        body = {
            "codigocuenta": codigocuenta or None,
            "codigoclienteoproveedor": codigoclienteoproveedor or None,
            "clienteoproveedor": clienteoproveedor or None,
            "razonsocial": razonsocial or None,
            "nombre": nombre or None,
            "cifdni": cifdni or None,
            "viapublica": viapublica or None,
            "domicilio": domicilio or None,
            "codigopostal": codigopostal or None,
            "provincia": provincia or None,
            "municipio": municipio or None,
            "telefono": telefono or None,
            "telefono2": telefono2 or None,
            "telefono3": telefono3 or None,
            "fax": fax or None,
            "iban": iban or None,
            "codigobanco": codigobanco or None,
            "codigoagencia": codigoagencia or None,
            "dc": dc or None,
            "ccc": ccc or None,
            "codigotipoefecto": codigotipoefecto or None,
            "codigocuentaefecto": codigocuentaefecto or None,
            "codigocuentaimpagado": codigocuentaimpagado or None,
            "remesahabitual": remesahabitual or None,
            "idgrupo": None if grupo_nombre == "(Sin grupo)" else grupos.get(grupo_nombre),
        }

        contactos = []
        if contacto_tel:
            contactos.append({"tipo": "TELEFONO", "valor": contacto_tel, "principal": True})
        if contacto_email:
            contactos.append({"tipo": "EMAIL", "valor": contacto_email, "principal": False})
        if fax:
            contactos.append({"tipo": "FAX", "valor": fax, "principal": False})

        direcciones = []
        if any([domicilio, codigopostal, provincia, municipio, idpais]):
            direcciones.append({
                "razonsocial": razonsocial,
                "direccionfiscal": domicilio,
                "direccion": domicilio,
                "idpais": (idpais or None),
                "idprovincia": provincia,
                "municipio": municipio,
                "codigopostal": codigopostal,
            })

        try:
            with st.spinner("Guardando..."):
                if is_edit:
                    res = _api_put(f"/api/clientes/{cliente_id}", json=body)
                else:
                    if contactos:
                        body["contactos"] = contactos
                    if direcciones:
                        body["direcciones"] = direcciones
                    res = _api_post("/api/clientes", json=body)
            st.toast(res.get("mensaje", "Guardado"), icon="OK")
            if not is_edit:
                st.session_state["cliente_actual"] = res.get("clienteid")
            st.session_state["cli_show_form"] = None
            st.rerun()
        except requests.HTTPError as e:
            try:
                st.error(f"Error: {e.response.json()}")
            except Exception:
                st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error creando cliente: {e}")
