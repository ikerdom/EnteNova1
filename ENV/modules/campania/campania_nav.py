import streamlit as st


# ==========================================================
# 📌 Barra de navegación superior — Módulo Campañas
# ==========================================================
def render_campania_nav(active_view: str, campaniaid: int | None):
    """
    Navegación superior unificada para todas las vistas del módulo de campañas.
    Controla:
    - Lista de campañas
    - Formulario (crear / editar)
    - Detalle
    - Progreso
    - Informes
    - Supervisión (solo para admin/editor)
    """

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    def go(view: str):
        """Cambia la vista y hace un rerun limpio."""
        st.session_state["campania_view"] = view

        # Si pedimos volver al listado → limpiar campaña seleccionada
        if view == "lista":
            st.session_state["campaniaid"] = None

        st.rerun()

    # Roles con acceso a supervisión
    rol = (st.session_state.get("rol_usuario") or "").lower()

    # ======================================================
    # Layout superior
    # ======================================================
    with st.container():
        st.markdown(
            """
            <style>
                .btn-nav-camp {
                    padding: 6px 16px;
                    border-radius: 8px;
                    font-weight: 600 !important;
                    margin-right: 4px;
                }
                .btn-nav-active {
                    background: #2563eb !important;
                    color: white !important;
                }
                .btn-nav-inactive {
                    background: #e5e7eb;
                    color: #374151;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([2, 8])

        # --------------------------------------------------
        # TÍTULO
        # --------------------------------------------------
        with col1:
            st.markdown("### 📣 Campañas")

        # --------------------------------------------------
        # BOTONERA
        # --------------------------------------------------
        with col2:
            btns = st.columns([1.3, 1.3, 1.3, 1.3, 1.5, 1.6])

            # LISTADO
            with btns[0]:
                if st.button(
                    "📋 Listado",
                    key="nav_lista",
                    help="Ver todas las campañas",
                    type="primary" if active_view == "lista" else "secondary",
                ):
                    go("lista")

            # FORM
            with btns[1]:
                if st.button(
                    "➕ Nueva / Editar",
                    key="nav_form",
                    help="Crear nueva campaña o editar la actual",
                    type="primary" if active_view == "form" else "secondary",
                ):
                    go("form")

            # DETALLE
            with btns[2]:
                if st.button(
                    "🔎 Detalle",
                    key="nav_detalle",
                    help="Ver resumen y configuración de la campaña",
                    disabled=(campaniaid is None),
                    type="primary" if active_view == "detalle" else "secondary",
                ):
                    if campaniaid:
                        go("detalle")

            # PROGRESO
            with btns[3]:
                if st.button(
                    "📈 Progreso",
                    key="nav_progreso",
                    help="Ver métricas y estado de todas las actuaciones",
                    disabled=(campaniaid is None),
                    type="primary" if active_view == "progreso" else "secondary",
                ):
                    if campaniaid:
                        go("progreso")

            # INFORMES (siempre disponible con campaña activa)
            with btns[4]:
                if st.button(
                    "📊 Informes",
                    key="nav_informes",
                    help="Gráficas, rendimiento, comparativas y KPI",
                    disabled=(campaniaid is None),
                    type="primary" if active_view == "informes" else "secondary",
                ):
                    if campaniaid:
                        go("informes")

            # SUPERVISIÓN
            with btns[5]:
                if rol in ("admin", "editor"):
                    if st.button(
                        "🕵️ Supervisión",
                        key="nav_supervision",
                        help="Vista global con alertas del CRM y riesgos",
                        type="primary" if active_view == "supervision" else "secondary",
                    ):
                        go("supervision")

    st.divider()
