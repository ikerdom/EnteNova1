import requests
from datetime import date

import streamlit as st

from modules.presupuesto_api import (
    actualizar_presupuesto,
    cliente_basico,
    crear_presupuesto,
    get_catalogos,
    get_presupuesto,
)
from modules.presupuesto_api import _base_url


def _pick(row: dict, *keys, default=None):
    for k in keys:
        if row.get(k) not in (None, "", "null"):
            return row.get(k)
    return default


def _load_direcciones(clienteid: int):
    """Devuelve (envio_options, env_by_id, fiscal_row)."""
    try:
        r = requests.get(f"{_base_url()}/api/clientes/{clienteid}/direcciones", timeout=20)
        r.raise_for_status()
        rows = r.json() or []
    except Exception:
        return {}, {}, None

    envio_labels = {}
    envio_by_id = {}
    fiscal = None

    for r in rows:
        tipo = (r.get("tipo") or "").lower()
        dir_id = _pick(r, "clientes_direccionid", "cliente_direccionid")
        label = f"{_pick(r,'direccion','') or '(sin direccion)'} - {_pick(r,'cp','codigopostal','')} {_pick(r,'ciudad','municipio','')} ({_pick(r,'provincia','')})"
        if tipo == "envio" and dir_id:
            envio_labels[label] = dir_id
            envio_by_id[dir_id] = r
        if tipo == "fiscal":
            fiscal = r

    return envio_labels, envio_by_id, fiscal


def _index(d: dict, val):
    """Indice para selectbox con opcion vacia inicial."""
    if not d or val is None:
        return 0
    keys = list(d.keys())
    for i, k in enumerate(keys):
        if d[k] == val:
            return i + 1
    return 0


def render_presupuesto_form(presupuestoid=None, bloqueado=False, on_saved_rerun=True):
    """
    Formulario de cabecera del presupuesto (API FastAPI).
    - Si presupuestoid es None, crea; si existe, actualiza.
    """
    st.subheader("Datos del presupuesto")

    # Catalogos
    catalogos = get_catalogos()
    estados = {c["label"]: c["id"] for c in catalogos.get("estados", [])}
    formas_pago = {c["label"]: c["id"] for c in catalogos.get("formas_pago", [])}
    clientes_cat = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}
    trabajadores = {c["label"]: c["id"] for c in catalogos.get("trabajadores", [])}

    # Presupuesto (si existe)
    presupuesto = {}
    if presupuestoid:
        try:
            presupuesto = get_presupuesto(presupuestoid)
        except Exception as e:
            st.error(f"No se pudo cargar el presupuesto: {e}")
            return

    clienteid = presupuesto.get("clienteid")
    cliente_info = cliente_basico(clienteid) if clienteid else {}
    direcciones_env_labels, direcciones_env_by_id, direccion_fiscal = (
        _load_direcciones(clienteid) if clienteid else ({}, {}, None)
    )

    with st.form(f"form_presupuesto_{presupuestoid or 'new'}"):
        c1, c2 = st.columns(2)
        with c1:
            cliente_sel = st.selectbox(
                "Cliente",
                ["(sin cliente)"] + list(clientes_cat.keys()),
                index=_index(clientes_cat, presupuesto.get("clienteid")),
                disabled=bool(presupuestoid),
            )
        with c2:
            trab_sel = st.selectbox(
                "Comercial",
                ["(sin comercial)"] + list(trabajadores.keys()),
                index=_index(trabajadores, presupuesto.get("trabajadorid")),
                disabled=bloqueado,
            )

        if not presupuestoid and cliente_sel != "(sin cliente)":
            clienteid = clientes_cat.get(cliente_sel)
            cliente_info = cliente_basico(clienteid) if clienteid else {}
            direcciones_env_labels, direcciones_env_by_id, direccion_fiscal = _load_direcciones(clienteid)

        with st.expander("Datos fiscales del cliente", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.text_input(
                    "Cliente",
                    value=_pick(cliente_info, "razonsocial", "razon_social", "nombre") or "",
                    disabled=True,
                )
            with col_b:
                st.text_input(
                    "CIF/NIF",
                    value=_pick(cliente_info, "cifdni", "cif", "cif_nif") or "",
                    disabled=True,
                )

            if direccion_fiscal:
                st.markdown("**Direccion fiscal**")
                st.write(
                    f"{_pick(direccion_fiscal,'direccion','')}\n\n"
                    f"{_pick(direccion_fiscal,'cp','codigopostal','')} "
                    f"{_pick(direccion_fiscal,'ciudad','municipio','')} "
                    f"({_pick(direccion_fiscal,'provincia','')}) "
                    f"{_pick(direccion_fiscal,'pais','ES')}"
                )
            else:
                st.info("Este cliente no tiene direccion fiscal definida.")

        with st.expander("Direccion de envio", expanded=True):
            if direcciones_env_labels:
                direccion_sel = st.selectbox(
                    "Direccion de envio",
                    list(direcciones_env_labels.keys()),
                    index=_index(direcciones_env_labels, presupuesto.get("direccion_envioid")),
                    disabled=bloqueado,
                )
            else:
                direccion_sel = None
                st.info("No hay direcciones de envio. Se usara la fiscal.")

            if direccion_sel:
                env_id = direcciones_env_labels.get(direccion_sel)
                env = direcciones_env_by_id.get(env_id, {})
                st.markdown("**Resumen direccion de envio**")
                st.write(
                    f"{_pick(env,'direccion','')}\n\n"
                    f"{_pick(env,'cp','codigopostal','')} "
                    f"{_pick(env,'ciudad','municipio','')} "
                    f"({_pick(env,'provincia','')}) {_pick(env,'pais','ES')}"
                )

        numero = st.text_input("Numero de presupuesto", presupuesto.get("numero", ""), disabled=bloqueado)
        referencia = st.text_input("Referencia cliente", presupuesto.get("referencia_cliente", ""), disabled=bloqueado)

        c3, c4 = st.columns(2)
        with c3:
            fecha = st.date_input(
                "Fecha del presupuesto",
                value=(
                    date.fromisoformat(presupuesto["fecha_presupuesto"])
                    if presupuesto.get("fecha_presupuesto")
                    else date.today()
                ),
                disabled=bloqueado,
            )
        with c4:
            fecha_validez = st.date_input(
                "Validez hasta",
                value=(
                    date.fromisoformat(presupuesto["fecha_validez"])
                    if presupuesto.get("fecha_validez")
                    else date.today()
                ),
                disabled=bloqueado,
            )

        c7, c8 = st.columns(2)
        with c7:
            ambito_impuesto = st.selectbox(
                "Ambito impuesto",
                ["ES", "ES-CN", "ES-CE", "ES-ML", "EXT"],
                index=["ES", "ES-CN", "ES-CE", "ES-ML", "EXT"].index(
                    presupuesto.get("ambito_impuesto") or "ES"
                ),
                disabled=bloqueado,
            )
        with c8:
            st.caption("El ambito define IVA/IGIC/IPSI.")

        c5, c6 = st.columns(2)
        with c5:
            contacto_att = st.text_input(
                "Persona de contacto (ATT.)",
                presupuesto.get("contacto_att", ""),
                disabled=bloqueado,
            )
        with c6:
            telefono_contacto = st.text_input(
                "Telefono contacto",
                presupuesto.get("telefono_contacto", ""),
                disabled=bloqueado,
            )

        formapago_sel = st.selectbox(
            "Forma de pago",
            ["(sin forma de pago)"] + list(formas_pago.keys()),
            index=_index(formas_pago, presupuesto.get("formapagoid")),
            disabled=bloqueado,
        )

        observaciones = st.text_area(
            "Observaciones",
            presupuesto.get("observaciones", ""),
            height=100,
            disabled=bloqueado,
        )

        estado_sel = st.selectbox(
            "Estado del presupuesto",
            ["(sin estado)"] + list(estados.keys()),
            index=_index(estados, presupuesto.get("estado_presupuestoid")),
            disabled=bloqueado,
        )

        facturar = st.checkbox(
            "Facturar individualmente",
            value=bool(presupuesto.get("facturar_individual", False)),
            disabled=bloqueado,
        )

        guardar = st.form_submit_button("Guardar presupuesto", disabled=bloqueado, use_container_width=True)

    if guardar:
        try:
            payload = {
                "numero": numero or None,
                "clienteid": clienteid,
                "trabajadorid": trabajadores.get(trab_sel),
                "referencia_cliente": referencia or None,
                "fecha_presupuesto": fecha.isoformat(),
                "fecha_validez": fecha_validez.isoformat(),
                "ambito_impuesto": ambito_impuesto,
                "observaciones": observaciones or None,
                "facturar_individual": facturar,
                "contacto_att": contacto_att or None,
                "telefono_contacto": telefono_contacto or None,
                "direccion_envioid": direcciones_env_labels.get(direccion_sel) if direccion_sel else None,
            }

            payload["formapagoid"] = formas_pago.get(formapago_sel) if formapago_sel in formas_pago else None
            if estado_sel in estados:
                payload["estado_presupuestoid"] = estados[estado_sel]

            if presupuestoid:
                actualizar_presupuesto(presupuestoid, payload)
                st.toast("Presupuesto actualizado.")
            else:
                creado = crear_presupuesto(payload)
                presupuestoid = creado.get("presupuestoid")
                st.toast("Presupuesto creado.")

            if on_saved_rerun:
                st.rerun()
        except Exception as e:
            st.error(f"Error al guardar el presupuesto: {e}")
