# modules/ui/section.py
import streamlit as st
from contextlib import contextmanager

@contextmanager
def section(title: str, icon: str | None = None):
    """
    Sección visual dentro de una página.
    """

    if icon:
        st.markdown(f"### {icon} {title}")
    else:
        st.markdown(f"### {title}")

    st.markdown("")  # pequeño aire

    try:
        yield
    finally:
        st.markdown("---")
