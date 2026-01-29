"""
Cliente HTTP para CRM acciones (FastAPI).
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


def listar(params: Optional[dict] = None) -> dict:
    r = requests.get(f"{_base_url()}/api/crm/acciones", params=params, timeout=20)
    return _handle(r)


def crear(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/crm/acciones", json=payload, timeout=20)
    return _handle(r)


def actualizar(accionid: int, payload: dict) -> dict:
    r = requests.put(f"{_base_url()}/api/crm/acciones/{accionid}", json=payload, timeout=20)
    return _handle(r)


def detalle(accionid: int) -> dict:
    r = requests.get(f"{_base_url()}/api/crm/acciones/{accionid}", timeout=15)
    return _handle(r)
