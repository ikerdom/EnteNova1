import streamlit as st
import os

def render_ai_page(launch_dataquerybot=None):
    st.title("🤖 Consultas Inteligentes (DataQueryBot)")

    # ============================================================
    # 🔍 DEBUG: Mostrar estado del entorno (solo para desarrollo)
    # ============================================================
    openai_key_ok = "Sí" if os.getenv("OPENAI_API_KEY") else "❌ NO"
    supa_ok = "Sí" if os.getenv("URL_SUPABASE") else "❌ NO"

    with st.expander("🔧 Diagnóstico (debug)", expanded=False):
        st.write("**OPENAI_API_KEY cargada:**", openai_key_ok)
        st.write("**URL_SUPABASE cargada:**", supa_ok)
        st.caption("Si algo aparece en rojo, el DataQueryBot no se abrirá correctamente.")

    st.markdown("""
    Bienvenido al panel de **Consultas Inteligentes**.

    Desde aquí puedes abrir el **DataQueryBot completo**, que incluye:
    - Generación automática de SQL
    - Interpretación de resultados
    - Gráficos dinámicos
    - Modelos de análisis avanzados

    Usa el botón inferior para abrirlo en una nueva ventana.
    """)

    # ============================================================
    # 🔐 Validación antes de habilitar el botón
    # ============================================================
    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ Falta la clave OPENAI_API_KEY. Configúrala en el ERP.")
        return

    if not os.getenv("URL_SUPABASE"):
        st.error("❌ Falta URL_SUPABASE. El ERP no ha enviado la cadena de conexión.")
        return

    st.success("Todo listo para lanzar el DataQueryBot 🚀")

    # Mostrar quién va a acceder
    st.info(f"Usuario actual: **{st.session_state.get('user_email', 'desconocido')}**")

    # ============================================================
    # 🚀 Botón para lanzar DataQueryBot
    # ============================================================
    if launch_dataquerybot:
        if st.button("🔗 Abrir DataQueryBot Completo", type="primary", use_container_width=True):
            st.toast("Iniciando DataQueryBot...", icon="🚀")
            launch_dataquerybot()

    else:
        st.error("⚠️ DataQueryBot no está disponible. No se encontró el lanzador.")
