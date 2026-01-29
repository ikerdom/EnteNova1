aimport streamlit as st
from typing import Dict, Any, Optional, List


# =========================
# Helpers comunes
# =========================
def _as_options(
    rows: List[Dict[str, Any]],
    label: str = "nombre",
    value: str = "id",
) -> Dict[str, Any]:
    """Convierte lista de dicts a {label: value} cuidando None."""
    if not rows:
        return {}

    out: Dict[str, Any] = {}
    for r in rows:
        lbl = str(r.get(label) or "").strip()
        val = r.get(value)
        if lbl and val is not None:
            out[lbl] = val
    return out


# =========================
# LOADERS (cacheados)
# Nota: usar parámetro _supabase para evitar errores de cache hash.
# =========================
@st.cache_data(ttl=300)
def load_estados_cliente(_supabase) -> Dict[str, Any]:
    try:
        res = (
            _supabase.table("cliente_estado")
            .select("estadoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="estadoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar estados de cliente: {e}")
        return {}


@st.cache_data(ttl=300)
def load_categorias(_supabase) -> Dict[str, Any]:
    try:
        res = (
            _supabase.table("cliente_categoria")
            .select("categoriaid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="categoriaid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar categorías: {e}")
        return {}


@st.cache_data(ttl=300)
def load_grupos(_supabase) -> Dict[str, Any]:
    try:
        res = (
            _supabase.table("grupo")
            .select("grupoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="grupoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar grupos: {e}")
        return {}


@st.cache_data(ttl=300)
def load_trabajadores(_supabase) -> Dict[str, Any]:
    try:
        res = (
            _supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos")
            .order("nombre")
            .execute()
        )

        if not res.data:
            return {}

        out: Dict[str, Any] = {}
        for r in res.data:
            nombre = str(r.get("nombre") or "").strip()
            apellidos = str(r.get("apellidos") or "").strip()
            lbl = f"{nombre} {apellidos}".strip() or "Trabajador"
            out[lbl] = r.get("trabajadorid")
        return out

    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar trabajadores: {e}")
        return {}


@st.cache_data(ttl=300)
def load_formas_pago(_supabase) -> Dict[str, Any]:
    try:
        res = (
            _supabase.table("forma_pago")
            .select("formapagoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="formapagoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar formas de pago: {e}")
        return {}


# =========================
# LOOKUPS (id -> etiqueta)
# =========================
@st.cache_data(ttl=300)
def get_estado_label(eid: Optional[int], _supabase) -> str:
    if not eid:
        return "-"
    mapping = load_estados_cliente(_supabase)
    for name, vid in mapping.items():
        if vid == eid:
            return name
    return "-"


@st.cache_data(ttl=300)
def get_categoria_label(cid: Optional[int], _supabase) -> str:
    if not cid:
        return "-"
    mapping = load_categorias(_supabase)
    for name, vid in mapping.items():
        if vid == cid:
            return name
    return "-"


@st.cache_data(ttl=300)
def get_grupo_label(gid: Optional[int], _supabase) -> str:
    if not gid:
        return "-"
    mapping = load_grupos(_supabase)
    for name, vid in mapping.items():
        if vid == gid:
            return name
    return "-"


@st.cache_data(ttl=300)
def get_formapago_label(fid: Optional[int], _supabase) -> str:
    if not fid:
        return "-"
    mapping = load_formas_pago(_supabase)
    for name, vid in mapping.items():
        if vid == fid:
            return name
    return "-"


@st.cache_data(ttl=300)
def get_trabajador_label(tid: Optional[int], _supabase) -> str:
    if not tid:
        return "-"
    mapping = load_trabajadores(_supabase)
    for name, vid in mapping.items():
        if vid == tid:
            return name
    return "-"
