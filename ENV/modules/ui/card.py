# modules/ui/card.py
import streamlit as st
from contextlib import contextmanager

@contextmanager
def card():
    """
    Card visual estándar Orbe.
    Sustituye HTML inline con estilos repetidos.
    """

    st.markdown(
        """
        <div style="
            border:1px solid #e5e7eb;
            border-radius:12px;
            background:#f9fafb;
            padding:14px;
            margin-bottom:14px;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);
        ">
        """,
        unsafe_allow_html=True,
    )

    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)
