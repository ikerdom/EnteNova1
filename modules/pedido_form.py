# ======================================================
# 🧾 FORMULARIO DE PEDIDO — Alta y edición vía API FastAPI
# ======================================================
import streamlit as st
from datetime import date
from modules.pedido_api import catalogos, detalle, crear_pedido, actualizar_pedido


def _to_map(items):
    return {i["label"]: i["id"] for i in items or []}


def _sel_index(diccionario, id_actual):
    if not id_actual:
        return 0
    for i, (k, v) in enumerate(diccionario.items()):
        if v == id_actual:
            return i + 1
    return 0


def _as_date(value: str | None):
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value.split("T")[0])
    except Exception:
        return date.today()


def render_pedido_form(_supabase_unused, pedidoid: int | None = None, on_saved_rerun: bool = True):
    """Formulario de alta/edición de pedidos usando la API."""
    modo = "✏️ Editar pedido" if pedidoid else "🆕 Nuevo pedido"
    st.subheader(modo)

    try:
        cats = catalogos()
    except Exception as e:
        st.error(f"❌ No se pudieron cargar catálogos: {e}")
        return

    clientes = _to_map(cats.get("clientes", []))
    estados = _to_map(cats.get("estados", []))
    formas_pago = _to_map(cats.get("formas_pago", []))
    tipos_doc = _to_map(cats.get("tipos_documento", []))

    pedido = {}
    if pedidoid:
        try:
            pedido = detalle(pedidoid)
        except Exception as e:
            st.error(f"❌ Error cargando pedido: {e}")
            return

    with st.expander("📋 Datos generales", expanded=True):
        with st.form(f"form_pedido_{pedidoid or 'new'}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                cliente_sel = st.selectbox(
                    "Cliente (catálogo)",
                    ["(sin cliente)"] + list(clientes.keys()),
                    index=_sel_index(clientes, pedido.get("clienteid")),
                )
            with c2:
                cliente_txt = st.text_input("Cliente (texto)", pedido.get("cliente") or "")
            with c3:
                cif_txt = st.text_input("CIF cliente", pedido.get("cif_cliente") or "")

            cA, cB, cC = st.columns(3)
            with cA:
                est_sel = st.selectbox(
                    "Estado",
                    ["(sin estado)"] + list(estados.keys()),
                    index=_sel_index(estados, pedido.get("pedido_estadoid")),
                )
            with cB:
                pago_sel = st.selectbox(
                    "Forma de pago",
                    ["(sin forma de pago)"] + list(formas_pago.keys()),
                    index=_sel_index(formas_pago, pedido.get("forma_pagoid")),
                )
            with cC:
                tipo_doc_sel = st.selectbox(
                    "Tipo documento",
                    ["(sin tipo)"] + list(tipos_doc.keys()),
                    index=_sel_index(tipos_doc, pedido.get("pedido_tipo_documentoid")),
                )

            cD, cE, cF = st.columns(3)
            with cD:
                fecha_pedido = st.date_input("Fecha pedido", value=_as_date(pedido.get("fecha_pedido")))
            with cE:
                procedencia = st.text_input("Procedencia", pedido.get("pedido_procedencia") or "")
            with cF:
                referencia = st.text_input("Referencia cliente", pedido.get("referencia_cliente") or "")

            obs = st.text_area("Observaciones", pedido.get("observaciones") or "", height=120)
            obs_log = st.text_area("Obs. logística", pedido.get("obs_logistica") or "", height=120)

            enviar = st.form_submit_button("💾 Guardar pedido", use_container_width=True)

        if enviar:
            payload = {
                "clienteid": clientes.get(cliente_sel) if cliente_sel != "(sin cliente)" else None,
                "cliente": cliente_txt.strip() or None,
                "cif_cliente": cif_txt.strip() or None,
                "pedido_estadoid": estados.get(est_sel) if est_sel != "(sin estado)" else None,
                "forma_pagoid": formas_pago.get(pago_sel) if pago_sel != "(sin forma de pago)" else None,
                "pedido_tipo_documentoid": tipos_doc.get(tipo_doc_sel) if tipo_doc_sel != "(sin tipo)" else None,
                "fecha_pedido": fecha_pedido.isoformat(),
                "pedido_procedencia": procedencia.strip() or None,
                "referencia_cliente": referencia.strip() or None,
                "observaciones": obs.strip() or None,
                "obs_logistica": obs_log.strip() or None,
            }

            try:
                if pedidoid:
                    actualizar_pedido(pedidoid, payload)
                    st.toast("✅ Pedido actualizado correctamente.", icon="✅")
                else:
                    res = crear_pedido(payload)
                    nuevo_id = res.get("pedido_id")
                    st.toast(f"✅ Pedido creado (ID {nuevo_id}).", icon="✅")
                if on_saved_rerun:
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando pedido: {e}")
