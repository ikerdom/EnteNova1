# ============================================================
# 🧭 ADMINISTRACIÓN DE TARIFAS (vía API FastAPI)
# ============================================================
import pandas as pd
import streamlit as st
from datetime import date

from modules.tarifa_api import (
    catalogos,
    listar_reglas,
    crear_regla,
    actualizar_regla,
    borrar_regla,
    asignar_cliente_tarifa,
)

# ============================================================
# Utilidades
# ============================================================
PAGE_SIZE = 50


def _safe(v, d="-"):
    return v if v not in ("", None, "null") else d


def _label_from(catalog: dict, id_val) -> str:
    if not id_val:
        return "-"
    for k, v in (catalog or {}).items():
        if v == id_val:
            return k
    return "-"


def _enrich_reglas_for_table(reglas, *, tarifas, clientes, grupos, productos, familias):
    out = []
    for r in reglas:
        out.append(
            {
                "ID": r.get("tarifa_reglaid"),
                "Tarifa": _label_from(tarifas, r.get("tarifaid")),
                "Cliente": _label_from(clientes, r.get("clienteid")),
                "Grupo": _label_from(grupos, r.get("grupoid")),
                "Producto": _label_from(productos, r.get("productoid")),
                "Familia": _label_from(familias, r.get("familia_productoid")),
                "Desde": _safe(r.get("fecha_inicio")),
                "Hasta": _safe(r.get("fecha_fin")),
                "Habilitada": bool(r.get("habilitada", True)),
            }
        )
    return out


# ============================================================
# UI principal
# ============================================================
def render_tarifa_admin():
    st.header("🧮 Administración de Tarifas")
    st.caption("Consulta, habilita/deshabilita y gestiona reglas de tarifas por cliente, grupo o familia usando FastAPI.")

    # ----------------------------
    # Catálogos
    # ----------------------------
    try:
        cats = catalogos()
    except Exception as e:
        st.error(f"❌ No se pudieron cargar catálogos: {e}")
        return

    def to_map(items):
        return {i["label"]: i["id"] for i in items or []}

    tarifas = to_map(cats.get("tarifas", []))
    clientes = to_map(cats.get("clientes", []))
    grupos = to_map(cats.get("grupos", []))
    productos = to_map(cats.get("productos", []))
    familias = to_map(cats.get("familias", []))

    # ----------------------------
    # Filtros
    # ----------------------------
    with st.expander("🔎 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cli_sel = st.selectbox("Cliente", ["(Todos)"] + list(clientes.keys()))
        with c2:
            grp_sel = st.selectbox("Grupo", ["(Todos)"] + list(grupos.keys()))
        with c3:
            tar_sel = st.selectbox("Tarifa", ["(Todas)"] + list(tarifas.keys()))

        c4, c5 = st.columns(2)
        with c4:
            prod_sel = st.selectbox("Producto", ["(Todos)"] + list(productos.keys()))
        with c5:
            fam_sel = st.selectbox("Familia de producto", ["(Todas)"] + list(familias.keys()))

        show_disabled = st.toggle("👁️ Mostrar también deshabilitadas", value=False)

        clienteid = clientes.get(cli_sel) if cli_sel != "(Todos)" else None
        grupoid = grupos.get(grp_sel) if grp_sel != "(Todos)" else None
        tarifaid_fil = tarifas.get(tar_sel) if tar_sel != "(Todas)" else None
        productoid = productos.get(prod_sel) if prod_sel != "(Todos)" else None
        familiaid = familias.get(fam_sel) if fam_sel != "(Todas)" else None

    # ----------------------------
    # Carga de reglas vía API
    # ----------------------------
    try:
        payload = listar_reglas(
            {
                "clienteid": clienteid,
                "grupoid": grupoid,
                "productoid": productoid,
                "familiaid": familiaid,
                "tarifaid": tarifaid_fil,
                "incluir_deshabilitadas": show_disabled,
            }
        )
        reglas = payload.get("data", [])
    except Exception as e:
        st.error(f"❌ Error cargando reglas: {e}")
        reglas = []

    rows = _enrich_reglas_for_table(
        reglas,
        tarifas=tarifas,
        clientes=clientes,
        grupos=grupos,
        productos=productos,
        familias=familias,
    )

    st.markdown("---")
    st.subheader("📋 Reglas aplicables")

    if not rows:
        st.info("No hay reglas que coincidan con los filtros seleccionados.")
    else:
        df = pd.DataFrame(rows)
        edited = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["ID", "Tarifa", "Cliente", "Grupo", "Producto", "Familia", "Desde", "Hasta"],
            key="tabla_tarifas_editor",
        )

        # Toggle habilitada
        for idx, row in edited.iterrows():
            orig = reglas[idx]
            if bool(row["Habilitada"]) != bool(orig.get("habilitada", True)):
                try:
                    actualizar_regla(int(orig["tarifa_reglaid"]), {"habilitada": bool(row["Habilitada"])})
                    st.toast(f"✅ Regla {orig['tarifa_reglaid']} actualizada.")
                except Exception as e:
                    st.error(f"❌ No se pudo actualizar la regla: {e}")

        habil = len([r for r in reglas if r.get("habilitada")])
        total = len(reglas)
        st.caption(f"✅ {habil} habilitadas · 🔕 {total - habil} deshabilitadas · Total {total}")

        # ----------------------------
        # Mantenimiento
        # ----------------------------
        with st.expander("🛠️ Mantenimiento de reglas", expanded=False):
            st.caption("Modifica la vigencia de una regla o elimínala permanentemente.")

            opciones = []
            for r in reglas:
                t = _label_from(tarifas, r.get("tarifaid"))
                c = _label_from(clientes, r.get("clienteid"))
                g = _label_from(grupos, r.get("grupoid"))
                p = _label_from(productos, r.get("productoid"))
                f = _label_from(familias, r.get("familia_productoid"))
                vig = f"{_safe(r.get('fecha_inicio'))} → {_safe(r.get('fecha_fin'))}"
                etiqueta = f"[{r['tarifa_reglaid']}] {t} · C:{c} · G:{g} · P:{p} · F:{f} · {vig}"
                opciones.append((etiqueta, r["tarifa_reglaid"]))

            if not opciones:
                st.info("No hay reglas disponibles.")
            else:
                choice_label = st.selectbox("Selecciona una regla", [lbl for (lbl, _) in opciones])
                regla_sel = next(v for (lbl, v) in opciones if lbl == choice_label)
                regla_obj = next(r for r in reglas if r["tarifa_reglaid"] == regla_sel)

                try:
                    default_fin = (
                        date.fromisoformat(regla_obj["fecha_fin"])
                        if regla_obj.get("fecha_fin")
                        else date(2999, 12, 31)
                    )
                except Exception:
                    default_fin = date(2999, 12, 31)

                nueva_fin = st.date_input(
                    "Nueva fecha fin",
                    value=default_fin,
                    key=f"new_fin_{regla_sel}",
                )

                colA, colB = st.columns(2)
                with colA:
                    if st.button("💾 Guardar vigencia", use_container_width=True):
                        try:
                            actualizar_regla(int(regla_sel), {"fecha_fin": nueva_fin.isoformat()})
                            st.success("✅ Vigencia actualizada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error guardando: {e}")
                with colB:
                    if st.button("🗑️ Eliminar regla", use_container_width=True):
                        try:
                            borrar_regla(int(regla_sel))
                            st.success("🗑️ Regla eliminada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error eliminando: {e}")

    # ----------------------------
    # Asignar tarifa
    # ----------------------------
    st.markdown("---")
    st.subheader("🧭 Asignar tarifa")
    st.caption(
        "La tarifa se aplicará automáticamente según la jerarquía:\n"
        "1) Prod+Cliente = Tarifa 25 · 2) Fam+Cliente = Tarifa 20 · "
        "3) Prod+Grupo = Tarifa 15 · 4) Fam+Grupo = Tarifa 10 · 5) General = Tarifa 5"
    )

    jerarquias = [
        "1) Producto + Cliente",
        "2) Familia + Cliente",
        "3) Producto + Grupo",
        "4) Familia + Grupo",
        "5) General (cliente_tarifa)",
    ]
    pat = st.selectbox("Jerarquía", jerarquias)

    TARIFA_BY_JERARQUIA = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
    }
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

    if st.button("💾 Guardar asignación", type="primary", use_container_width=True):
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
            st.success("✅ Asignación registrada correctamente.")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error guardando asignación: {e}")

    # ----------------------------
    # Crear tarifa (placeholder)
    # ----------------------------
    with st.expander("🆕 Crear NUEVA tarifa (bloqueado)", expanded=False):
        st.info("Funcionalidad deshabilitada por política interna.")
