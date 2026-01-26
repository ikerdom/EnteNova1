import pandas as pd
import requests
import streamlit as st

from modules.presupuesto_api import agregar_linea, listar_lineas, _base_url


def _productos_options():
    try:
        r = requests.get(
            f"{_base_url()}/api/productos",
            params={"page": 1, "page_size": 200, "sort_field": "nombre"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        st.warning(f"No se pudieron cargar productos: {e}")
        return []


def _pick(row: dict, *keys):
    for k in keys:
        if row.get(k) is not None:
            return row.get(k)
    return None


def anadir_linea_presupuesto(presupuestoid: int):
    st.subheader("Anadir linea al presupuesto")

    productos = _productos_options()
    nombres = [p.get("nombre") for p in productos]

    producto_sel = st.selectbox("Producto", ["(selecciona)"] + nombres)
    if producto_sel == "(selecciona)":
        return

    prod = next((p for p in productos if p.get("nombre") == producto_sel), None)
    if not prod:
        st.warning("Producto no encontrado.")
        return

    cantidad = st.number_input("Cantidad", min_value=1.0, step=1.0, value=1.0)

    if st.button("Anadir linea", use_container_width=True):
        try:
            payload = {
                "productoid": int(prod["productoid"]),
                "cantidad": float(cantidad),
                "descripcion": prod.get("nombre"),
            }
            agregar_linea(presupuestoid, payload)
            st.success(f"Linea anadida: {cantidad} x {prod['nombre']}")
            st.rerun()
        except Exception as e:
            st.error(f"Error anadiendo linea: {e}")


def render_presupuesto_detalle(presupuestoid: int, bloqueado: bool = False):
    st.subheader("Detalle de lineas del presupuesto")

    try:
        lineas = listar_lineas(presupuestoid)
    except Exception as e:
        st.error(f"Error cargando lineas del presupuesto: {e}")
        return

    if not lineas:
        st.info("No hay lineas en este presupuesto.")
    else:
        rows = []
        total_base = total_iva = total_total = 0.0
        por_tarifa = {}
        por_iva = {}
        for ln in lineas:
            base = _pick(ln, "base_linea", "importe_base") or 0.0
            iva_pct = _pick(ln, "iva_pct") or 0.0
            iva_importe = _pick(ln, "iva_importe")
            if iva_importe is None:
                iva_importe = float(base) * float(iva_pct) / 100.0
            total_linea = _pick(ln, "total_linea", "importe_total_linea")
            if total_linea is None:
                total_linea = float(base) + float(iva_importe)

            total_base += float(base)
            total_iva += float(iva_importe)
            total_total += float(total_linea)

            nivel = ln.get("nivel_tarifa") or "-"
            bucket = por_tarifa.get(nivel, {"base": 0.0, "total": 0.0})
            bucket["base"] += float(base)
            bucket["total"] += float(total_linea)
            por_tarifa[nivel] = bucket

            iva_key = f"{iva_pct:.2f}%"
            por_iva[iva_key] = por_iva.get(iva_key, 0.0) + float(iva_importe)

            rows.append(
                {
                    "Descripcion": ln.get("descripcion"),
                    "Cantidad": ln.get("cantidad"),
                    "P. Unit (EUR)": ln.get("precio_unitario"),
                    "Dto (%)": ln.get("descuento_pct"),
                    "Base (EUR)": base,
                    "IVA (%)": iva_pct,
                    "IVA imp (EUR)": iva_importe,
                    "Total linea (EUR)": total_linea,
                    "Tarifa": ln.get("tarifa_aplicada"),
                    "Nivel tarifa": ln.get("nivel_tarifa"),
                }
            )

        df = pd.DataFrame(rows)
        for col in ["P. Unit (EUR)", "Base (EUR)", "IVA imp (EUR)", "Total linea (EUR)"]:
            df[col] = df[col].map(lambda x: f"{x:,.2f} EUR" if x is not None else "-")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Base imponible", f"{total_base:,.2f} EUR")
        c2.metric("IVA/IGIC/IPSI", f"{total_iva:,.2f} EUR")
        c3.metric("Total documento", f"{total_total:,.2f} EUR")

        st.markdown("---")
        c4, c5 = st.columns(2)
        with c4:
            st.markdown("Resumen por nivel tarifa")
            if por_tarifa:
                df_tar = pd.DataFrame(
                    [
                        {"Nivel": k, "Base (EUR)": v["base"], "Total (EUR)": v["total"]}
                        for k, v in por_tarifa.items()
                    ]
                )
                st.dataframe(df_tar, use_container_width=True, hide_index=True)
            else:
                st.caption("Sin datos de tarifas.")
        with c5:
            st.markdown("IVA por tipo")
            if por_iva:
                df_iva = pd.DataFrame(
                    [{"IVA %": k, "Importe (EUR)": v} for k, v in por_iva.items()]
                )
                st.dataframe(df_iva, use_container_width=True, hide_index=True)
            else:
                st.caption("Sin datos de IVA.")

    st.divider()

    if bloqueado:
        st.info("Este presupuesto esta bloqueado y no permite cambios.")
        return

    anadir_linea_presupuesto(presupuestoid)
