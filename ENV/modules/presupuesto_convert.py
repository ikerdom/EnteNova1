# =========================================================
# 🔄 Conversión de Presupuestos a Pedidos (vía API)
# =========================================================
import streamlit as st
from modules.presupuesto_api import convertir_a_pedido


def convertir_presupuesto_a_pedido(presupuestoid: int):
    """
    Convierte un presupuesto en pedido usando el endpoint FastAPI.
    """
    try:
        resp = convertir_a_pedido(presupuestoid)
        if resp.get("ya_existia"):
            st.info(f"ℹ️ Ya existe un pedido asociado: #{resp.get('numero')}")
        else:
            st.success(f"✅ Presupuesto convertido a pedido {resp.get('numero')}")
        return resp.get("pedidoid")
    except Exception as e:
        st.error(f"❌ Error convirtiendo presupuesto: {e}")
        return None
