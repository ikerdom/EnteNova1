import streamlit as st

# ======================================================
# 📦 Importación de vistas del módulo Campañas
# ======================================================
from modules.campania import campania_lista
from modules.campania import campania_form
from modules.campania import campania_progreso
from modules.campania import campania_detalle
from modules.campania import campania_informes
from modules.campania.campania_supervision import render_supervision


# ======================================================
# 🚦 ROUTER PRINCIPAL DEL MÓDULO DE CAMPAÑAS
# ======================================================
def render_campania_router(supa):
    """
    Router interno del módulo de campañas.
    Gestiona TODAS las vistas:
      - lista
      - form
      - detalle
      - progreso
      - informes
      - supervision
    """

    # --------------------------------------------------
    # Inicialización de estado segura
    # --------------------------------------------------
    st.session_state.setdefault("campania_view", "lista")
    st.session_state.setdefault("campania_step", 1)     # wizard de creación
    st.session_state.setdefault("campaniaid", None)
    st.session_state.setdefault("supa", supa)

    view = st.session_state["campania_view"]
    campaniaid = st.session_state.get("campaniaid")

    # Helper para error sin campaña seleccionada
    def require_selected():
        st.error("❗ No hay ninguna campaña seleccionada.")
        if st.button("⬅️ Volver al listado"):
            st.session_state["campania_view"] = "lista"
            st.session_state["campaniaid"] = None
            st.rerun()

    # ======================================================
    # 🧭 RUTEO
    # ======================================================

    # ------------------------------------------------------
    # LISTADO
    # ------------------------------------------------------
    if view == "lista":
        return campania_lista.render(supa)

    # ------------------------------------------------------
    # FORMULARIO
    # ------------------------------------------------------
    elif view == "form":
        return campania_form.render(supa)

    # ------------------------------------------------------
    # DETALLE
    # ------------------------------------------------------
    elif view == "detalle":
        if not campaniaid:
            return require_selected()
        return campania_detalle.render(campaniaid)

    # ------------------------------------------------------
    # PROGRESO
    # ------------------------------------------------------
    elif view == "progreso":
        if not campaniaid:
            return require_selected()
        return campania_progreso.render()

    # ------------------------------------------------------
    # INFORMES
    # ------------------------------------------------------
    elif view == "informes":
        if not campaniaid:
            return require_selected()
        return campania_informes.render(supa, campaniaid)

    # ------------------------------------------------------
    # SUPERVISIÓN
    # ------------------------------------------------------
    elif view == "supervision":
        return render_supervision(supa)

    # ------------------------------------------------------
    # Fallback — vista desconocida (nunca debería pasar)
    # ------------------------------------------------------
    else:
        st.warning(f"Vista desconocida: {view}. Volviendo al listado.")
        st.session_state["campania_view"] = "lista"
        st.rerun()
