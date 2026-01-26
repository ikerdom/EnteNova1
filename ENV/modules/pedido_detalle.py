import streamlit as st
import pandas as pd
from modules.pedido_models import load_estados_pedido, load_clientes, load_trabajadores
from modules.incidencia_lista import render_incidencia_lista


def render_pedido_detalle(supabase, pedidoid: int):
    """Muestra la ficha completa de un pedido con tabs."""
    try:
        pedido = (
            supabase.table("pedido")
            .select("*")
            .eq("pedidoid", pedidoid)
            .single()
            .execute()
            .data
        )
        if not pedido:
            st.error("❌ Pedido no encontrado.")
            return
    except Exception as e:
        st.error(f"Error cargando pedido: {e}")
        return

    st.subheader(f"📋 Pedido #{pedido['numero']} — Detalle completo")

    tabs = st.tabs(["🧾 Resumen", "📦 Líneas", "💰 Totales y observaciones"])

    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    estados = load_estados_pedido(supabase)

    cliente_nombre = next((k for k, v in clientes.items() if v == pedido.get("clienteid")), "-")
    trabajador_nombre = next((k for k, v in trabajadores.items() if v == pedido.get("trabajadorid")), "-")
    estado_nombre = next((k for k, v in estados.items() if v == pedido.get("estado_pedidoid")), "-")

    st.markdown("## 🚨 Incidencias relacionadas")
    render_incidencia_lista(supabase)


    # -----------------------------------------------------
    # 🧾 TAB 1 — Resumen
    # -----------------------------------------------------
    with tabs[0]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Cliente:** {cliente_nombre}")
            st.markdown(f"**Vendedor:** {trabajador_nombre}")
            st.markdown(f"**Estado:** {estado_nombre}")
            st.markdown(f"**Tipo:** {pedido.get('tipo_pedidoid', '-')}")
            st.markdown(f"**Procedencia:** {pedido.get('procedencia_pedidoid', '-')}")
        with col2:
            st.markdown(f"**Fecha pedido:** {pedido.get('fecha_pedido')}")
            st.markdown(f"**Confirmada:** {pedido.get('fecha_confirmada')}")
            st.markdown(f"**Entrega prevista:** {pedido.get('fecha_entrega_prevista')}")
            st.markdown(f"**Facturar individual:** {'✅ Sí' if pedido.get('facturar_individual') else '❌ No'}")
        st.divider()
        st.markdown(f"**Referencia cliente:** {pedido.get('referencia_cliente') or '-'}")
        if pedido.get("justificante_pago_url"):
            st.markdown(f"[📄 Ver justificante de pago]({pedido['justificante_pago_url']})")

    # -----------------------------------------------------
    # 📦 TAB 2 — Líneas del pedido
    # -----------------------------------------------------
    with tabs[1]:
        try:
            res = (
                supabase.table("pedido_detalle")
                .select("pedido_detalleid, nombre_producto, cantidad, precio_unitario, descuento_pct, importe_total_linea")
                .eq("pedidoid", pedidoid)
                .execute()
            )
            lineas = res.data or []
            if not lineas:
                st.info("📭 No hay líneas registradas para este pedido.")
            else:
                df = pd.DataFrame(lineas)
                df["importe_total_linea"] = df["importe_total_linea"].fillna(
                    df["cantidad"] * df["precio_unitario"]
                )
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error cargando líneas: {e}")

    # -----------------------------------------------------
    # 💰 TAB 3 — Totales y observaciones
    # -----------------------------------------------------
    with tabs[2]:
        col1, col2 = st.columns([1, 1])
        with col1:
            try:
                tot = (
                    supabase.table("pedido_totales")
                    .select("*")
                    .eq("pedidoid", pedidoid)
                    .single()
                    .execute()
                    .data
                )
                if not tot:
                    st.warning("⚠️ No hay totales calculados para este pedido.")
                else:
                    st.metric("Base imponible", f"{tot['base_imponible']:.2f} €")
                    st.metric("IVA", f"{tot['iva_importe']:.2f} €")
                    st.metric("Total", f"{tot['total_importe']:.2f} €")
                    st.metric("Gastos de envío", f"{tot['gastos_envio']:.2f} €")
            except Exception as e:
                st.error(f"Error cargando totales: {e}")
        with col2:
            try:
                obs = (
                    supabase.table("pedido_observacion")
                    .select("comentario, tipo, fecha, usuario")
                    .eq("pedidoid", pedidoid)
                    .order("fecha", desc=True)
                    .execute()
                    .data
                )
                if not obs:
                    st.info("🗒️ No hay observaciones registradas.")
                else:
                    for o in obs:
                        st.markdown(
                            f"**{o['tipo']}** — {o['fecha']} · {o.get('usuario','-')}\n\n> {o['comentario']}"
                        )
            except Exception as e:
                st.error(f"Error cargando observaciones: {e}")
