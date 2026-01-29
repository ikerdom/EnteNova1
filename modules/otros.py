import streamlit as st

from modules.impuesto_lista import render_impuesto_lista
from modules.diagramas import render_diagramas


def _table_exists(supabase, table: str) -> bool:
    if not supabase:
        return False
    try:
        supabase.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _render_empresas(supabase):
    st.subheader("Empresas")
    if not _table_exists(supabase, "empresa"):
        st.info("No hay tabla empresa.")
        return
    try:
        rows = (
            supabase.table("empresa")
            .select("empresa_id,empresa_nombre")
            .order("empresa_nombre")
            .execute()
            .data
            or []
        )
    except Exception as e:
        st.error(f"Error cargando empresas: {e}")
        return

    if not rows:
        st.info("No hay empresas.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_proveedores(supabase):
    st.subheader("Proveedores")
    if not _table_exists(supabase, "proveedor"):
        st.info("No hay tabla proveedor.")
        return
    buscar = st.text_input("Buscar proveedor", placeholder="Nombre del proveedor")
    try:
        q = supabase.table("proveedor").select("proveedorid,nombre,habilitado")
        if buscar:
            q = q.ilike("nombre", f"%{buscar}%")
        rows = q.order("nombre").execute().data or []
    except Exception as e:
        st.error(f"Error cargando proveedores: {e}")
        return

    if not rows:
        st.info("No hay proveedores.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_otros(supabase):
    st.header("Otros")
    st.caption("Utilidades, catalogos y analitica general.")

    opciones = [
        "Impuestos",
        "Diagramas y metricas",
        "Empresas",
        "Proveedores",
    ]
    vista = st.selectbox("Seccion", opciones)

    if vista == "Impuestos":
        render_impuesto_lista(supabase)
    elif vista == "Diagramas y metricas":
        render_diagramas()
    elif vista == "Empresas":
        _render_empresas(supabase)
    elif vista == "Proveedores":
        _render_proveedores(supabase)
