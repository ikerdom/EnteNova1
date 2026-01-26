"""
Cliente HTTP para la gestión de tarifas vía FastAPI.
Centraliza las llamadas para mantener la UI libre de Supabase.
"""
from typing import Any, Dict, Optional

import requests
import streamlit as st


def _base_url() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def _handle(resp: requests.Response) -> Any:
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


def catalogos() -> dict:
    r = requests.get(f"{_base_url()}/api/tarifas/catalogos", timeout=20)
    return _handle(r)


def listar_reglas(params: Optional[dict] = None) -> dict:
    r = requests.get(f"{_base_url()}/api/tarifas/reglas", params=params, timeout=20)
    return _handle(r)


def crear_regla(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/tarifas/reglas", json=payload, timeout=20)
    return _handle(r)


def actualizar_regla(reglaid: int, payload: dict) -> dict:
    r = requests.patch(f"{_base_url()}/api/tarifas/reglas/{reglaid}", json=payload, timeout=20)
    return _handle(r)


def borrar_regla(reglaid: int) -> dict:
    r = requests.delete(f"{_base_url()}/api/tarifas/reglas/{reglaid}", timeout=20)
    return _handle(r)


def asignar_cliente_tarifa(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/tarifas/cliente-tarifa", json=payload, timeout=20)
    return _handle(r)


def calcular_precio(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/tarifas/calcular-precio", json=payload, timeout=20)
    return _handle(r)
