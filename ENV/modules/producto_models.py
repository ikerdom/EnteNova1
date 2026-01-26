import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# ==================================================
# 📦 Modelo de producto + catálogos
# ==================================================

@dataclass
class Producto:
    productoid: int
    nombre: Optional[str] = None
    titulo: Optional[str] = None
    referencia: Optional[str] = None
    ean: Optional[str] = None
    isbn: Optional[str] = None
    precio_generico: Optional[float] = None
    tipo: Optional[str] = None
    producto_tipoid: Optional[int] = None
    familia_productoid: Optional[int] = None
    impuestoid: Optional[int] = None
    estado_productoid: Optional[int] = None
    fecha_publicacion: Optional[str] = None
    portada_url: Optional[str] = None
    publico: Optional[bool] = None
    versatilidad: Optional[str] = None
    sinopsis: Optional[str] = None


# ==================================================
# Helpers
# ==================================================
def _as_options(rows: List[Dict[str, Any]], label="nombre", value="id") -> Dict[str, Any]:
    if not rows:
        return {}
    return {r.get(label, "-"): r.get(value) for r in rows if r.get(value) is not None}


# ==================================================
# Catálogos cacheados
# ==================================================
@st.cache_data(ttl=300)
def load_familias(_supabase) -> Dict[str, Any]:
    """Carga familias de producto (tabla: producto_familia)."""
    try:
        res = (
            _supabase.table("producto_familia")
            .select("familia_productoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="familia_productoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar familias: {e}")
        return {}


@st.cache_data(ttl=300)
def load_tipos_producto(_supabase) -> Dict[str, Any]:
    """Carga tipos de producto (tabla: producto_tipo)."""
    try:
        res = (
            _supabase.table("producto_tipo")
            .select("producto_tipoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="producto_tipoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar tipos de producto: {e}")
        return {}

@st.cache_data(ttl=300)
def load_impuestos(_supabase) -> Dict[str, Any]:
    """
    Carga impuestos (tabla: impuesto).
    Devuelve { "IVA Libros (4.0%)": 1, "IVA General (21.0%)": 3, ... }
    """
    try:
        res = (
            _supabase.table("impuesto")
            .select("impuestoid, nombre, porcentaje")
            .order("porcentaje", desc=True)
            .execute()
        )
        data = res.data or []
        out = {}
        for r in data:
            nombre = r.get("nombre") or "Impuesto"
            pct = r.get("porcentaje")
            # normaliza a float y formatea con 1 decimal cuando aplique
            try:
                pctf = float(pct) if pct is not None else None
            except Exception:
                pctf = None
            label = f"{nombre} ({pctf:.1f}%)" if pctf is not None else nombre
            out[label] = r.get("impuestoid")
        return out
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar impuestos: {e}")
        return {}


@st.cache_data(ttl=300)
def load_estados_producto(_supabase) -> Dict[str, Any]:
    """Carga estados del producto (tabla: estado_producto)."""
    try:
        res = (
            _supabase.table("estado_producto")
            .select("estado_productoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return {r["nombre"]: r["estado_productoid"] for r in res.data or []}
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar estados de producto: {e}")
        return {}


# ==================================================
# Lookups por ID
# ==================================================
@st.cache_data(ttl=300)
def get_familia_label(fid: Optional[int], _supabase) -> str:
    if not fid:
        return "-"
    mapping = load_familias(_supabase)
    return next((name for name, vid in mapping.items() if vid == fid), "-")


@st.cache_data(ttl=300)
def get_tipo_label(tid: Optional[int], _supabase) -> str:
    if not tid:
        return "-"
    mapping = load_tipos_producto(_supabase)
    return next((name for name, vid in mapping.items() if vid == tid), "-")


@st.cache_data(ttl=300)
def get_impuesto_label(iid: Optional[int], _supabase) -> str:
    if not iid:
        return "-"
    mapping = load_impuestos(_supabase)
    return next((name for name, vid in mapping.items() if vid == iid), "-")


@st.cache_data(ttl=300)
def get_estado_label(eid: Optional[int], _supabase) -> str:
    if not eid:
        return "-"
    mapping = load_estados_producto(_supabase)
    return next((name for name, vid in mapping.items() if vid == eid), "-")
