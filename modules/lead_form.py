import streamlit as st
from modules.supa_client import get_supabase_client


def render_lead_form():
    """
    Alta rápida de lead (cliente potencial).
    Usa el cliente Supabase desde modules.supa_client para evitar dependencias antiguas.
    """
    supabase = get_supabase_client()

    st.header("📞 Nuevo lead")
    st.caption("Registra un cliente potencial con los datos mínimos. Luego podrás convertirlo en cliente.")

    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del lead *", key="lead_nombre")
        email = st.text_input("Email", key="lead_email")
    with col2:
        telefono = st.text_input("Teléfono", key="lead_telefono")
        descripcion = st.text_area("Descripción / notas", key="lead_desc", height=80)

    # Estado por defecto: 'Nuevo' si existe
    estado_leadid = None
    try:
        est = supabase.table("crm_estado").select("estado_leadid").eq("nombre", "Nuevo").limit(1).execute()
        if est.data:
            estado_leadid = est.data[0]["estado_leadid"]
    except Exception:
        pass  # si no existe, se inserta sin estado

    # Procedencia opcional (si tienes maestra cargada)
    procedencias = []
    try:
        resp = supabase.table("crm_procedencia").select("procedenciaid, nombre").order("nombre").execute()
        procedencias = resp.data or []
    except Exception:
        procedencias = []

    procedencia_map = {p["nombre"]: p["procedenciaid"] for p in procedencias}
    procedencia_sel = st.selectbox(
        "Procedencia (opcional)",
        ["(sin especificar)"] + list(procedencia_map.keys()),
        key="lead_procedencia"
    )
    procedenciaid = procedencia_map.get(procedencia_sel)

    crear = st.button("➕ Crear lead", key="btn_crear_lead")

    if crear:
        if not nombre.strip():
            st.error("El nombre es obligatorio.")
            return
        try:
            payload = {
                "nombre": nombre.strip(),
                "email": email.strip() or None,
                "telefono": telefono.strip() or None,
                "descripcion": descripcion.strip() or None,
            }
            if estado_leadid:
                payload["estado_leadid"] = estado_leadid
            if procedenciaid:
                payload["procedenciaid"] = procedenciaid

            ins = supabase.table("crm_lead").insert(payload).execute()
            if ins.data:
                lead = ins.data[0]
                st.success(f"✅ Lead creado (ID {lead['leadid']}).")
            else:
                st.success("✅ Lead creado.")
        except Exception as e:
            st.error(f"❌ Error al crear el lead: {e}")
