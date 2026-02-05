# ======================================================
# 🧱 ERP EnteNova Gnosis · Orbe
# ======================================================

import streamlit as st
import os
from datetime import date
from dotenv import load_dotenv
load_dotenv(override=True)

# API base para servicios FastAPI (tolerante si no hay secrets.toml)
try:
    secret_api_url = st.secrets["ORBE_API_URL"]
except Exception:
    secret_api_url = None

API_URL = secret_api_url or os.getenv("ORBE_API_URL") or "http://127.0.0.1:8000"
st.session_state["ORBE_API_URL"] = API_URL

# ======================================================
# ⚙️ CONFIGURACIÓN GLOBAL
# ======================================================
st.set_page_config(
    page_title="ERP EnteNova Gnosis",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================
# 🎨 TEMA CORPORATIVO ORBE
# ======================================================
from modules.orbe_theme import apply_orbe_theme
apply_orbe_theme()

# ======================================================
# 🔗 CONEXIÓN A SUPABASE
# ======================================================
from modules.supa_client import get_supabase_client
supabase = get_supabase_client()

try:
    supabase.table("cliente").select("clienteid").limit(1).execute()
    st.sidebar.success("✅ Conectado a Supabase")
    st.session_state["supa"] = supabase
except Exception as e:
    st.sidebar.error("❌ Error de conexión con Supabase")
    st.sidebar.caption(str(e))

# ======================================================
# 🌐 CORE UI / NAVEGACIÓN
# ======================================================
from modules.topbar import render_topbar
from modules.login import render_login
from modules.diagramas import render_diagramas

# ======================================================
# 📦 MÓDULOS PRINCIPALES
# ======================================================
from modules.cliente_lista import render_cliente_lista
from modules.cliente_potencial_lista import render_cliente_potencial_lista
from modules.producto_lista import render_producto_lista
from modules.pedido_lista import render_pedido_lista
from modules.presupuesto_lista import render_presupuesto_lista
from modules.crm_acciones import render_crm_acciones
from modules.historial import render_historial
from modules.lead_form import render_lead_form
from modules.impuesto_lista import render_impuesto_lista
from modules.tarifa_admin import render_tarifa_admin
from modules.incidencia_lista import render_incidencia_lista
from modules.otros import render_otros

# Campañas
from modules.campania.campania_router import render_campania_router

# ======================================================
# 🧩 CONTROL DE SESIÓN
# ======================================================
if "user_email" not in st.session_state:
    st.sidebar.warning("🔒 Inicia sesión para continuar")
    render_login()
    st.stop()

st.session_state.setdefault("menu_principal", "📊 Panel general")
st.session_state.setdefault("rol_usuario", "Editor")
st.session_state.setdefault("tipo_usuario", "trabajador")

# ======================================================
# 🎨 TOPBAR GLOBAL
# ======================================================
render_topbar(supabase)

# ======================================================
# 🧭 MENÚ LATERAL
# ======================================================
st.sidebar.title("📂 Menú principal")

if "user_email" in st.session_state:
    tipo = st.session_state.get("tipo_usuario", "Trabajador").capitalize()
    rol = st.session_state.get("rol_usuario", "Editor").capitalize()
    st.sidebar.markdown(
        f"**👤 Sesión:** {st.session_state['user_email']}  \n"
        f"**Rol:** {rol} ({tipo})"
    )
    st.sidebar.markdown("---")
    st.sidebar.subheader("Preferencias UI")
    st.session_state.setdefault("pref_compact", False)
    st.session_state["pref_compact"] = st.sidebar.checkbox(
        "Vista compacta por defecto",
        value=st.session_state.get("pref_compact", False),
        help="Activa la vista compacta en listados con tarjetas.",
    )
else:
    st.sidebar.markdown("**No hay sesión iniciada.**")
    st.sidebar.markdown("---")

tipo_usuario = st.session_state.get("tipo_usuario")

# ======================================================
# 🧩 MENÚ DINÁMICO
# ======================================================
if tipo_usuario == "trabajador":
    menu_principal = [
        "📊 Panel general",
        "👥 Catalogo de clientes",
        "🧾 Clientes potenciales",
        "📦 Catalogo de productos",
        "💼 Gestion de presupuestos",
        "🧾 Gestion de pedidos",
        "🏷️ Gestion de tarifas",
        "🗓️ Calendario CRM",
        "📣 Campanas",
        "💬 Historial / Comunicacion",
        "⚠️ Incidencias",
        "🧩 Otros",
        "🚪 Cerrar sesion",
    ]

elif tipo_usuario == "cliente":
    menu_principal = [
        "👥 Catalogo de clientes",
        "💬 Historial de contacto",
        "🗓️ Acciones / Calendario",
        "🧩 Otros",
        "🚪 Cerrar sesion",
    ]

else:
    menu_principal = [
        "🔐 Iniciar sesion"
    ]

if st.session_state.get("menu_principal") not in menu_principal:
    st.session_state["menu_principal"] = menu_principal[0] if menu_principal else None

opcion = st.sidebar.radio("Selecciona modulo:", menu_principal, key="menu_principal")

rol_usuario = (st.session_state.get("rol_usuario") or "").strip().lower()
if rol_usuario == "lector" and (
    "presupuesto" in opcion.lower()
    or "pedido" in opcion.lower()
    or "devoluci" in opcion.lower()
):
    st.warning("Tu rol no tiene acceso a este módulo.")
    st.stop()

# ======================================================
# ======================================================
# ======================================================
# ROUTER PRINCIPAL
# ======================================================
if opcion == "🔐 Iniciar sesion":
    render_login()

elif opcion == "🚪 Cerrar sesion":
    for key in [
        "cliente_actual", "cliente_creado", "user_email", "user_nombre",
        "tipo_usuario", "rol_usuario", "trabajadorid",
        "pedido_tipo_filtro", "modo_incidencias"
    ]:
        st.session_state.pop(key, None)

    st.success("Sesion cerrada correctamente.")
    st.rerun()

elif opcion == "📊 Panel general":
    try:
        from modules.dashboard_general import render_dashboard
        render_dashboard(supabase)
    except Exception as e:
        st.warning(f"No se pudo cargar el dashboard general: {e}")

elif opcion == "👥 Catalogo de clientes":
    st.sidebar.subheader("👥 Catalogo de clientes")
    render_cliente_lista(API_URL)

elif opcion == "🧾 Clientes potenciales":
    st.sidebar.subheader("🧾 Clientes potenciales / Leads")
    render_cliente_potencial_lista()

elif opcion == "📦 Catalogo de productos":
    st.sidebar.subheader("📦 Catalogo de productos")
    render_producto_lista(supabase)

elif opcion == "💼 Gestion de presupuestos":
    st.sidebar.subheader("💼 Gestion de presupuestos")
    render_presupuesto_lista(API_URL)

elif opcion == "🧾 Gestion de pedidos":
    st.sidebar.subheader("🧾 Gestion de pedidos")
    render_pedido_lista(API_URL)

elif opcion == "🏷️ Gestion de tarifas":
    st.sidebar.subheader("🏷️ Administracion de tarifas")
    render_tarifa_admin()

elif opcion == "🗓️ Calendario CRM":
    st.sidebar.subheader("🗓️ Acciones y calendario")
    render_crm_acciones(supabase)

elif opcion == "📣 Campanas":
    st.sidebar.subheader("📣 Campanas comerciales")
    render_campania_router(supabase)

elif opcion == "💬 Historial / Comunicacion":
    st.sidebar.subheader("💬 Historial de mensajes")
    render_historial(supabase)

elif opcion == "⚠️ Incidencias":
    st.sidebar.subheader("⚠️ Gestion de incidencias")
    try:
        render_incidencia_lista(supabase)
    except Exception as e:
        st.warning(f"No se pudo cargar el modulo de incidencias: {e}")

elif opcion == "🧩 Otros":
    st.sidebar.subheader("🧩 Otros")
    render_otros(supabase)

elif opcion == "Nuevo lead":
    render_lead_form()

# 📋 PIE DE PÁGINA
# ======================================================
st.markdown("---")
st.caption(
    "© 2025 **EnteNova Gnosis · Orbe**  |  "
    "Desarrollado por *Iker Domínguez Ibáñez*  |  "
    "Versión interna de desarrollo · build 1.0.0"
)
