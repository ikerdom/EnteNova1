# modules/ui/page.py
import streamlit as st
from contextlib import contextmanager

@contextmanager
def page(title: str, subtitle: str | None = None, icon: str | None = None):
    """
    Página ERP Orbe — visible, por bloques.
    Mantiene la estructura que ya usas: título + caption + separador.
    """

    st.markdown("")

    # Header principal
    if icon:
        st.markdown(f"## {icon} {title}")
    else:
        st.markdown(f"## {title}")

    if subtitle:
        st.caption(subtitle)

    # Separador fuerte de página
    st.markdown("---")

    try:
        yield
    finally:
        st.markdown("")  # aire final
