# modules/dashboard/utils.py

import streamlit as st
from datetime import datetime, date


# ==========================================================
# 🔧 Utilidades de fecha y hora
# ==========================================================
def safe_date(d):
    if not d:
        return "-"
    try:
        return date.fromisoformat(str(d)[:10]).strftime("%d/%m/%Y")
    except:
        return str(d)


def safe_time(t):
    if not t:
        return ""
    try:
        return datetime.fromisoformat(str(t)).strftime("%H:%M")
    except:
        return ""


# ==========================================================
# 🔎 Autocomplete cliente
# ==========================================================
def cliente_autocomplete(
    supabase,
    key_prefix,
    label="Cliente (opcional)",
    clienteid_inicial=None,
):
    """
    Autocomplete con Supabase. Si no hay Supabase, se ofrece un campo numérico sencillo.
    """
    if supabase is None:
        val = st.number_input(
            "ID cliente (opcional)",
            min_value=0,
            step=1,
            value=clienteid_inicial or 0,
            key=f"{key_prefix}_cli_id",
        )
        return val or None

    col1, col2 = st.columns([2, 2])

    with col1:
        search = st.text_input(
            "Buscar cliente",
            key=f"{key_prefix}_search",
            placeholder="nombre, comercial o CIF…"
        )

    opciones = {"(Sin cliente)": None}

    if search and len(search.strip()) >= 2:
        txt = search.strip()
        rows = (
            supabase.table("cliente")
            .select("clienteid, razonsocial, nombre, cifdni")
            .or_(
                f"razonsocial.ilike.%{txt}%,"
                f"nombre.ilike.%{txt}%,"
                f"cifdni.ilike.%{txt}%"
            )
            .limit(20)
            .execute()
            .data or []
        )

        for c in rows:
            nombre = c.get("razonsocial") or c.get("nombre") or f"Cliente {c['clienteid']}"
            cif = c.get("cifdni") or ""
            etiqueta = f"{nombre} ({cif})" if cif else nombre
            opciones[etiqueta] = c["clienteid"]

    # Valor por defecto
    default = "(Sin cliente)"
    if clienteid_inicial:
        for k, v in opciones.items():
            if v == clienteid_inicial:
                default = k

    with col2:
        sel = st.selectbox(label, list(opciones.keys()), index=list(opciones.keys()).index(default))
        return opciones.get(sel)


# ==========================================================
# 🔢 Contador genérico de registros (solución del error)
# ==========================================================
def contar_registros(supabase, tabla, filtros=None):
    """
    Contador seguro para KPIs.
    """
    try:
        q = supabase.table(tabla).select("*", count="exact")
        if filtros:
            for k, v in filtros.items():
                q = q.eq(k, v)
        res = q.execute()
        return getattr(res, "count", 0) or 0
    except Exception:
        return 0


# ==========================================================
# 👥 Cargar mapa de clientes (id -> nombre)
# ==========================================================
def cargar_clientes_map(supabase, acts):
    ids = list({a["clienteid"] for a in acts if a.get("clienteid")})
    if not ids:
        return {}

    try:
        res = (
            supabase.table("cliente")
            .select("clienteid, razonsocial")
            .in_("clienteid", ids)
            .execute()
        )
        return {r["clienteid"]: r["razonsocial"] for r in res.data}
    except:
        return {}


# ==========================================================
# 👥 Filtro universal por trabajador
# ==========================================================
def filtrar_por_trabajador(acts, trabajadorid):
    """
    Aplica el filtro del dashboard:
    - Ver mis actuaciones
    - Si trabajador_asignadoid es None → creador es visible
    """
    if not trabajadorid:
        return acts

    result = []
    for a in acts:
        asignado = a.get("trabajador_asignadoid")
        creador = a.get("trabajador_creadorid") or a.get("trabajadorid")

        if asignado == trabajadorid:
            result.append(a)
        elif asignado is None and creador == trabajadorid:
            result.append(a)

    return result
