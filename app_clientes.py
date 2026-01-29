# ======================================================
# 👥 ERP EnteNova Gnosis · Orbe — MODO CLIENTES
# ======================================================

import streamlit as st
import os
from dotenv import load_dotenv

# ======================================================
# 🌱 ENV
# ======================================================
load_dotenv()

API_URL = os.getenv("ORBE_API_URL")
if not API_URL:
    st.error("❌ Falta ORBE_API_URL en el .env")
    st.stop()

# ======================================================
# ⚙️ CONFIGURACIÓN STREAMLIT
# ======================================================
st.set_page_config(
    page_title="ERP EnteNova · Clientes",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================
# 🎨 TEMA
# ======================================================
from modules.orbe_theme import apply_orbe_theme
apply_orbe_theme()

# ======================================================
# 🔗 SUPABASE (SOLO PARA MÓDULOS NO MIGRADOS)
# ======================================================
from modules.supa_client import get_supabase_client

try:
    supabase = get_supabase_client()
    supabase.table("cliente").select("clienteid").limit(1).execute()
    st.session_state["supa"] = supabase
    st.sidebar.success("✅ Conectado a Supabase")
except Exception as e:
    st.sidebar.error("❌ Error de conexión con Supabase")
    st.sidebar.caption(str(e))
    st.stop()

# ======================================================
# 🔐 LOGIN
# ======================================================
from modules.login import render_login

if "user_email" not in st.session_state:
    st.sidebar.warning("🔒 Inicia sesión para continuar")
    render_login()
    st.stop()

st.session_state.setdefault("rol_usuario", "Editor")
st.session_state.setdefault("tipo_usuario", "trabajador")

# ======================================================
# 🧭 MENÚ
# ======================================================
st.sidebar.title("👥 Clientes")

opcion = st.sidebar.radio(
    "Selecciona vista:",
    [
        "📋 Lista de clientes",
        "🧾 Clientes potenciales",
    ]
)

# ======================================================
# 📦 MÓDULOS
# ======================================================
from modules.cliente_lista import render_cliente_lista
from modules.cliente_potencial_lista import render_cliente_potencial_lista

if opcion == "📋 Lista de clientes":
    st.header("👥 Gestión de clientes")
    render_cliente_lista(API_URL)

elif opcion == "🧾 Clientes potenciales":
    st.header("🧾 Clientes potenciales / Leads")
    render_cliente_potencial_lista()

# ======================================================
# 📋 PIE
# ======================================================
st.markdown("---")
st.caption("© 2025 EnteNova Gnosis · Orbe — Modo pruebas Clientes")
