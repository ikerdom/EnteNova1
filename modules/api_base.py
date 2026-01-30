import os
import streamlit as st


def get_api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        base = (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )
        return str(base).rstrip("/")
