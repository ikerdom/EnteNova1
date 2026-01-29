# modules/ui/empty.py
import streamlit as st

def empty_state(text: str, icon: str = "📭"):
    st.info(f"{icon} {text}")
