# modules/tarifa_manager.py
# Vista avanzada de tarifas usando la API (sin Supabase directo).

import streamlit as st
import pandas as pd
from datetime import date

from modules.tarifa_api import catalogos, listar_reglas, crear_regla, asignar_cliente_tarifa
from modules.simulador_pedido import render_simulador_pedido


def _to_map(items):
    return {i["label"]: i["id"] for i in items or []}


def render_tarifa_manager():
    st.header("🧭 Gestión de tarifas y jerarquías (API)")
    st.caption("Consulta y administra reglas de tarifas sin depender de Supabase en la UI.")

    try:
        cats = catalogos()
    except Exception as e:
        st.error(f"❌ No se pudieron cargar catálogos: {e}")
        return

    tarifas = _to_map(cats.get("tarifas", []))
    clientes = _to_map(cats.get("clientes", []))
    grupos = _to_map(cats.get("grupos", []))
    productos = _to_map(cats.get("productos", []))
    familias = _to_map(cats.get("familias", []))

    tabs = st.tabs(["📋 Reglas", "➕ Crear / asignar", "🧮 Simulador"])

    # ---------------------------
    # Reglas (listado + filtros)
    # ---------------------------
    with tabs[0]:
        st.subheader("📋 Reglas de tarifas")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            cli_sel = st.selectbox("Cliente", ["(Todos)"] + list(clientes.keys()))
        with c2:
            grp_sel = st.selectbox("Grupo", ["(Todos)"] + list(grupos.keys()))
        with c3:
            tar_sel = st.selectbox("Tarifa", ["(Todas)"] + list(tarifas.keys()))

        c4, c5 = st.columns([2, 2])
        with c4:
            prod_sel = st.selectbox("Producto", ["(Todos)"] + list(productos.keys()))
        with c5:
            fam_sel = st.selectbox("Familia", ["(Todas)"] + list(familias.keys()))

        show_disabled = st.toggle("👁️ Mostrar deshabilitadas", value=False)

        params = {
            "clienteid": clientes.get(cli_sel) if cli_sel != "(Todos)" else None,
            "grupoid": grupos.get(grp_sel) if grp_sel != "(Todos)" else None,
            "productoid": productos.get(prod_sel) if prod_sel != "(Todos)" else None,
            "familiaid": familias.get(fam_sel) if fam_sel != "(Todas)" else None,
            "tarifaid": tarifas.get(tar_sel) if tar_sel != "(Todas)" else None,
            "incluir_deshabilitadas": show_disabled,
        }

        try:
            payload = listar_reglas(params)
            reglas = payload.get("data", [])
        except Exception as e:
            st.error(f"❌ Error cargando reglas: {e}")
            reglas = []

        if not reglas:
            st.info("No hay reglas con los filtros actuales.")
        else:
            rows = []
            for r in reglas:
                rows.append(
                    {
                        "ID": r.get("tarifa_reglaid"),
                        "Tarifa": _label(tarifas, r.get("tarifaid")),
                        "Cliente": _label(clientes, r.get("clienteid")),
                        "Grupo": _label(grupos, r.get("grupoid")),
                        "Producto": _label(productos, r.get("productoid")),
                        "Familia": _label(familias, r.get("familia_productoid")),
                        "Desde": r.get("fecha_inicio"),
                        "Hasta": r.get("fecha_fin"),
                        "Habilitada": bool(r.get("habilitada", True)),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ---------------------------
    # Crear / asignar
    # ---------------------------
    with tabs[1]:
        st.subheader("➕ Crear regla o asignar tarifa")
        jerarquias = [
            "1) Producto + Cliente",
            "2) Familia + Cliente",
            "3) Producto + Grupo",
            "4) Familia + Grupo",
            "5) General (cliente_tarifa)",
        ]
        pat = st.selectbox("Jerarquía", jerarquias)

        TARIFA_BY_JERARQUIA = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
        numero = pat.split(")")[0]
        t_id = TARIFA_BY_JERARQUIA[numero]

        colA, colB = st.columns(2)
        with colA:
            fecha_desde = st.date_input("📅 Vigente desde", value=date.today())
        with colB:
            fecha_hasta = st.date_input("⏱️ Vigente hasta (opcional)", value=date.today())
        if st.checkbox("♾️ Sin fecha final", value=False):
            fecha_hasta = date(2999, 12, 31)

        sel_cliente = sel_grupo = sel_producto = sel_familia = None
        if numero == "1":
            sel_cliente = st.selectbox("Cliente", list(clientes.keys()))
            sel_producto = st.selectbox("Producto", list(productos.keys()))
        elif numero == "2":
            sel_cliente = st.selectbox("Cliente", list(clientes.keys()))
            sel_familia = st.selectbox("Familia", list(familias.keys()))
        elif numero == "3":
            sel_grupo = st.selectbox("Grupo", list(grupos.keys()))
            sel_producto = st.selectbox("Producto", list(productos.keys()))
        elif numero == "4":
            sel_grupo = st.selectbox("Grupo", list(grupos.keys()))
            sel_familia = st.selectbox("Familia", list(familias.keys()))
        elif numero == "5":
            sel_cliente = st.selectbox("Cliente", list(clientes.keys()))

        if st.button("💾 Guardar", type="primary", use_container_width=True):
            try:
                if numero == "5":
                    asignar_cliente_tarifa(
                        {
                            "clienteid": clientes[sel_cliente],
                            "tarifaid": t_id,
                            "fecha_desde": fecha_desde.isoformat(),
                            "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                        }
                    )
                    st.success("✅ Tarifa general asignada.")
                    st.rerun()

                payload = {
                    "tarifaid": t_id,
                    "habilitada": True,
                    "fecha_inicio": fecha_desde.isoformat(),
                    "fecha_fin": fecha_hasta.isoformat() if fecha_hasta else None,
                }
                if numero == "1":
                    payload["clienteid"] = clientes[sel_cliente]
                    payload["productoid"] = productos[sel_producto]
                elif numero == "2":
                    payload["clienteid"] = clientes[sel_cliente]
                    payload["familia_productoid"] = familias[sel_familia]
                elif numero == "3":
                    payload["grupoid"] = grupos[sel_grupo]
                    payload["productoid"] = productos[sel_producto]
                elif numero == "4":
                    payload["grupoid"] = grupos[sel_grupo]
                    payload["familia_productoid"] = familias[sel_familia]

                crear_regla(payload)
                st.success("✅ Regla creada/asignada correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    # ---------------------------
    # Simulador
    # ---------------------------
    with tabs[2]:
        render_simulador_pedido()


def _label(catalog: dict, val):
    for k, v in catalog.items():
        if v == val:
            return k
    return "-"
