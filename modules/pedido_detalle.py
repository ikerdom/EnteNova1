import streamlit as st
import pandas as pd
from modules.pedido_api import detalle, lineas, totales, observaciones
from modules.incidencia_lista import render_incidencia_lista


def render_pedido_detalle(_supabase_unused, pedido_id: int):
    """Muestra el detalle completo de un pedido (solo API)."""
    try:
        pedido = detalle(pedido_id)
        if not pedido:
            st.error("❌ Pedido no encontrado.")
            return
    except Exception as e:
        st.error(f"Error cargando pedido: {e}")
        return

    st.subheader(f"📋 Pedido #{pedido.get('pedido_id')} — Detalle completo")

    tabs = st.tabs(["🧾 Resumen", "📦 Líneas", "💰 Totales y observaciones"])

    st.markdown("## 🚨 Incidencias relacionadas")
    render_incidencia_lista(None)

    # -----------------------------------------------------
    # TAB 1 — Resumen
    # -----------------------------------------------------
    with tabs[0]:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Cliente:** {pedido.get('cliente') or pedido.get('clienteid') or '-'}")
            st.markdown(f"**Estado:** {pedido.get('pedido_estado_nombre') or pedido.get('pedido_estadoid') or '-'}")
            st.markdown(f"**Procedencia:** {pedido.get('pedido_procedencia') or '-'}")
        with col2:
            st.markdown(f"**Fecha pedido:** {pedido.get('fecha_pedido')}")
            st.markdown(f"**Fecha completado:** {pedido.get('fecha_completado')}")
        st.divider()
        st.markdown(f"**Referencia cliente:** {pedido.get('referencia_cliente') or '-'}")

    # -----------------------------------------------------
    # TAB 2 — Líneas del pedido
    # -----------------------------------------------------
    with tabs[1]:
        try:
            lineas_data = lineas(pedido_id) or []
            if not lineas_data:
                st.info("📭 No hay líneas registradas para este pedido.")
            else:
                df = pd.DataFrame(lineas_data)
                st.dataframe(df, width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Error cargando líneas: {e}")

    # -----------------------------------------------------
    # TAB 3 — Totales y observaciones
    # -----------------------------------------------------
    with tabs[2]:
        col1, col2 = st.columns([1, 1])
        with col1:
            tot = None
            try:
                tot = totales(pedido_id)
            except Exception:
                tot = None
            st.metric("Base imponible", f"{float((tot or {}).get('total_base_imponible') or 0):.2f} €")
            st.metric("Impuestos", f"{float((tot or {}).get('total_impuestos') or 0):.2f} €")
            st.metric("Recargos", f"{float((tot or {}).get('total_recargos') or 0):.2f} €")
            st.metric("Gastos envío", f"{float((tot or {}).get('total_base_gastos_envios') or 0):.2f} €")
            st.metric("Total", f"{float((tot or {}).get('total') or 0):.2f} €")
        with col2:
            try:
                obs = observaciones(pedido_id) or []
            except Exception:
                obs = []
            if not obs:
                st.info("🗒️ No hay observaciones registradas.")
            else:
                for o in obs:
                    st.markdown(f"**{o.get('tipo','pedido')}** · {o.get('fecha','-')} · {o.get('usuario','-')}\n\n> {o.get('comentario','')}")
