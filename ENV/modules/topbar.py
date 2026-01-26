import streamlit as st
from datetime import datetime, timedelta
from modules.crm_api import listar as crm_listar


def render_topbar(_supabase_unused):
    """
    Barra superior ligera. Muestra alertas CRM próximas y mensajes pendientes (placeholder).
    Se apoya en la API de CRM, no en Supabase directo.
    """
    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")
    tipo = st.session_state.get("tipo_usuario", "Invitado").capitalize()

    hay_alertas = False
    try:
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=7)
        payload = {
            "trabajador_asignadoid": trabajadorid,
            "estado": None,
            "canal": None,
            "buscar": None,
        }
        acciones = crm_listar(payload).get("data", [])
        acciones = [a for a in acciones if a.get("fecha_vencimiento") and hoy <= datetime.fromisoformat(a["fecha_vencimiento"]).date() <= limite and a.get("estado") != "Completada"]
        hay_alertas = bool(acciones)
    except Exception:
        hay_alertas = False

    st.markdown(
        """
        <style>
        .topbar {
            position: sticky;
            top: 0;
            z-index: 100;
            background: linear-gradient(90deg, #0f172a, #1e293b);
            color: white;
            padding: 0.7rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.25);
            font-family: 'Inter', sans-serif;
        }
        .topbar .left { font-weight: 700; font-size: 1rem; letter-spacing: 0.3px; }
        .topbar .right { display: flex; align-items: center; gap: 0.6rem; }
        .pill { background:#ef4444; color:#fff; padding:2px 8px; border-radius:999px; font-size:0.75rem; }
        .btn { background:#2563eb; border:none; color:#fff; padding:6px 10px; border-radius:8px; cursor:pointer; }
        .btn:hover { background:#1d4ed8; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown('<div class="left">🧭 ERP EnteNova Gnosis</div>', unsafe_allow_html=True)

    with col2:
        c1, c2, c3 = st.columns([0.25, 0.25, 0.5])
        with c1:
            if st.button("➕", key="btn_add_action", help="Nueva acción CRM"):
                st.session_state["crear_accion_crm"] = True
        with c2:
            notif_label = "🔔"
            if hay_alertas:
                notif_label += " •"
            if st.button(notif_label, key="btn_notif_topbar", help="Ver próximas acciones"):
                st.session_state["mostrar_acciones_crm"] = not st.session_state.get("mostrar_acciones_crm", False)
        with c3:
            st.markdown(f"<div class='right'><span>{user} ({tipo})</span></div>", unsafe_allow_html=True)
            if st.button("Cerrar sesión", key="btn_logout_topbar", use_container_width=True):
                for key in ["cliente_actual", "cliente_creado", "user_email", "user_nombre", "tipo_usuario", "trabajadorid"]:
                    st.session_state.pop(key, None)
                st.success("Sesión cerrada correctamente.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
