import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


# ==================================================
# 📦 MODELO DE PEDIDO
# ==================================================
@dataclass
class Pedido:
    pedidoid: int
    numero: str
    clienteid: Optional[int] = None
    trabajadorid: Optional[int] = None
    tipo_pedidoid: Optional[int] = None
    procedencia_pedidoid: Optional[int] = None
    estado_pedidoid: Optional[int] = None
    formapagoid: Optional[int] = None
    transportistaid: Optional[int] = None
    fecha_pedido: Optional[str] = None
    fecha_confirmada: Optional[str] = None
    fecha_limite: Optional[str] = None
    fecha_envio: Optional[str] = None
    fecha_entrega_prevista: Optional[str] = None
    referencia_cliente: Optional[str] = None
    justificante_pago_url: Optional[str] = None
    facturar_individual: Optional[bool] = None


# ==================================================
# Helper para convertir a opciones
# ==================================================
def _as_options(rows: List[Dict[str, Any]], label="nombre", value="id") -> Dict[str, Any]:
    if not rows:
        return {}
    return {r.get(label, "-"): r.get(value) for r in rows if r.get(value) is not None}


# ==================================================
# Catálogos cacheados
# ==================================================
@st.cache_data(ttl=300)
def load_estados_pedido(_supabase) -> Dict[str, Any]:
    """Carga estados de pedido."""
    try:
        res = (
            _supabase.table("pedido_estado")
            .select("estado_pedidoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="estado_pedidoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar estados de pedido: {e}")
        return {}


@st.cache_data(ttl=300)
def load_tipos_pedido(_supabase) -> Dict[str, Any]:
    """Carga tipos de pedido."""
    try:
        res = (
            _supabase.table("pedido_tipo")
            .select("tipo_pedidoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="tipo_pedidoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar tipos de pedido: {e}")
        return {}


@st.cache_data(ttl=300)
def load_procedencias_pedido(_supabase) -> Dict[str, Any]:
    """Carga procedencias de pedido."""
    try:
        res = (
            _supabase.table("pedido_procedencia")
            .select("procedencia_pedidoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="procedencia_pedidoid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar procedencias: {e}")
        return {}


@st.cache_data(ttl=300)
def load_transportistas(_supabase) -> Dict[str, Any]:
    """Carga transportistas."""
    try:
        res = (
            _supabase.table("transportista")
            .select("transportistaid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
        )
        return _as_options(res.data, label="nombre", value="transportistaid")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar transportistas: {e}")
        return {}


@st.cache_data(ttl=300)
def load_formas_pago(_supabase) -> Dict[str, Any]:
    """Carga formas de pago."""
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


@st.cache_data(ttl=300)
def load_trabajadores(_supabase) -> Dict[str, Any]:
    """Carga trabajadores."""
    try:
        res = (
            _supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos, trabajador_rol(nombre)")
            .order("nombre")
            .execute()
        )
        options = {}
        for r in res.data or []:
            rol = ""
            if isinstance(r.get("trabajador_rol"), dict):
                rol = r["trabajador_rol"].get("nombre") or ""
            label = f"{r.get('nombre','')} {r.get('apellidos','')}".strip()
            if rol:
                label = f"{label} ({rol})"
            options[label] = r["trabajadorid"]
        return options
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar trabajadores: {e}")
        return {}


@st.cache_data(ttl=300)
def load_clientes(_supabase) -> Dict[str, Any]:
    """Carga clientes activos."""
    try:
        res = (
            _supabase.table("cliente")
            .select("clienteid, razonsocial, nombre")
            .order("razonsocial")
            .execute()
        )
        return {
            (r.get("razonsocial") or r.get("nombre") or f"Cliente {r.get('clienteid')}"): r.get("clienteid")
            for r in res.data or []
            if r.get("clienteid") is not None
        }
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar clientes: {e}")
        return {}
