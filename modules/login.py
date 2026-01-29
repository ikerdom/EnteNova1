import streamlit as st
from modules.supa_client import get_supabase_client

def render_login():
    """
    🔐 Inicio de sesión para trabajadores del ERP EnteNova Gnosis.
    - Autentica por correo (sin contraseña).
    - Carga automáticamente el trabajador, su ID y rol (si lo tiene).
    """

    st.title("🧱 ERP EnteNova Gnosis")
    st.caption("Sistema interno Orbe · módulo de trabajadores")

    # Si ya hay sesión activa, no volvemos a consultar Supabase
    if st.session_state.get("trabajadorid"):
        st.success(f"Sesión activa: {st.session_state.get('user_nombre', st.session_state.get('user_email',''))}")
        if st.button("Cerrar sesión"):
            for key in [
                "cliente_actual",
                "cliente_creado",
                "user_email",
                "user_nombre",
                "tipo_usuario",
                "rol_usuario",
                "trabajadorid",
            ]:
                st.session_state.pop(key, None)
            st.success("✅ Sesión cerrada correctamente.")
            st.rerun()
        return

    # -------------------------------------------------------
    # 🧍 FORMULARIO DE INICIO
    # -------------------------------------------------------
    st.subheader("🔐 Iniciar sesión como trabajador")

    with st.form("form_login_trabajador"):
        email = st.text_input("📧 Correo corporativo *", placeholder="Ej: iker@entenova.com")
        submitted = st.form_submit_button("Entrar ➜")

    if submitted:
        if not email.strip():
            st.error("⚠️ El correo es obligatorio.")
            return

        try:
            supabase = get_supabase_client()
            # Buscar trabajador por correo
            trab = (
                supabase.table("trabajador")
                .select("trabajadorid, nombre, apellidos, telefono, email, trabajador_rolid, trabajador_rol(nombre)")
                .eq("email", email.strip())
                .limit(1)
                .execute()
            )

            if trab.data:
                t = trab.data[0]

                # Limpiar posible sesión previa
                for key in ["cliente_actual", "cliente_creado"]:
                    st.session_state.pop(key, None)

                # Guardar sesión
                st.session_state["user_email"] = email.strip()
                st.session_state["user_nombre"] = f"{t['nombre']} {t['apellidos']}"
                st.session_state["tipo_usuario"] = "trabajador"
                st.session_state["trabajadorid"] = t["trabajadorid"]
                rol_nombre = None
                if isinstance(t.get("trabajador_rol"), dict):
                    rol_nombre = t["trabajador_rol"].get("nombre")
                st.session_state["rol_usuario"] = rol_nombre or "Editor"

                st.success(f"✅ Bienvenido {t['nombre']} ({email})")
                st.info("Acceso habilitado a gestión de clientes, CRM y comunicación interna.")
                st.rerun()
                return

            else:
                st.error("❌ No se encontró ningún trabajador con ese correo.")

        except Exception as e:
            st.error(f"❌ Error al iniciar sesión: {e}")

    # -------------------------------------------------------
    # 🚪 CIERRE DE SESIÓN
    # -------------------------------------------------------
    if "user_email" in st.session_state:
        st.markdown("---")
        st.subheader("🚪 Cerrar sesión")
        if st.button("Cerrar sesión"):
            for key in [
                "cliente_actual",
                "cliente_creado",
                "user_email",
                "user_nombre",
                "tipo_usuario",
                "rol_usuario",
                "trabajadorid",
            ]:
                st.session_state.pop(key, None)
            st.success("✅ Sesión cerrada correctamente.")
            st.rerun()

    # -------------------------------------------------------
    # 👣 PIE DE PÁGINA
    # -------------------------------------------------------
    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe · Desarrollado por Iker Domínguez Ibáñez")
