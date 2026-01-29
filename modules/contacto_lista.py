import streamlit as st


def render_contactos_lista(supabase):
    st.header("Contactos de cliente")
    st.caption("Busca y gestiona contactos asociados a clientes.")

    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("Buscar (tipo o valor)", key="ctos_q")
    with c2:
        solo_principales = st.toggle("Solo principales", value=False, key="ctos_principales")

    st.markdown("---")

    try:
        base = (
            supabase.table("cliente_contacto")
            .select("cliente_contactoid, tipo, valor, clienteid, principal")
        )
        if q:
            q = q.strip()
            base = base.or_(f"tipo.ilike.%{q}%,valor.ilike.%{q}%")

        if solo_principales:
            base = base.eq("principal", True)

        contactos = base.order("tipo").execute().data or []
        if not contactos:
            st.info("No hay contactos que coincidan.")
            return

        ids = sorted({c["clienteid"] for c in contactos if c.get("clienteid")})
        cliente_map = {}
        if ids:
            rows = (
                supabase.table("cliente")
                .select("clienteid, razonsocial, nombre")
                .in_("clienteid", ids)
                .execute()
                .data or []
            )
            cliente_map = {r["clienteid"]: r.get("razonsocial") or r.get("nombre", "-") for r in rows}

        for cto in contactos:
            razon = cliente_map.get(cto.get("clienteid"), "-")
            estrella = "*" if cto.get("principal") else ""
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;background:#f9fafb;">
                  <div style="display:flex;justify-content:space-between;gap:10px;">
                    <div>
                      <b>{cto.get('tipo','(Sin tipo)')}</b> {estrella}<br>
                      <span style="color:#6b7280;">{cto.get('valor','-')}</span>
                    </div>
                    <div style="text-align:right;color:#6b7280;">
                      Cliente: {razon}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"Error cargando contactos: {e}")
