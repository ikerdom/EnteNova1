"""
Cliente ligero para la API de presupuestos (FastAPI).
Centraliza las llamadas HTTP para que los mÃ³dulos Streamlit no dependan de Supabase.
"""
from datetime import date
from typing import Any, Dict, Optional

import requests
import streamlit as st


def _base_url() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def _handle_response(resp: requests.Response) -> Any:
    # Algunos endpoints devuelven 404 cuando no hay datos (ej: cliente sin perfil básico)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    if resp.content:
        return resp.json()
    return {}


def list_presupuestos(params: Optional[dict] = None) -> dict:
    r = requests.get(f"{_base_url()}/api/presupuestos", params=params, timeout=20)
    return _handle_response(r)


def get_catalogos() -> dict:
    r = requests.get(f"{_base_url()}/api/presupuestos/catalogos", timeout=20)
    return _handle_response(r)


def get_presupuesto(presupuestoid: int) -> dict:
    r = requests.get(f"{_base_url()}/api/presupuestos/{presupuestoid}", timeout=20)
    return _handle_response(r)


def crear_presupuesto(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/presupuestos", json=payload, timeout=20)
    return _handle_response(r)


def actualizar_presupuesto(presupuestoid: int, payload: dict) -> dict:
    r = requests.put(f"{_base_url()}/api/presupuestos/{presupuestoid}", json=payload, timeout=20)
    return _handle_response(r)


def borrar_presupuesto(presupuestoid: int) -> dict:
    r = requests.delete(f"{_base_url()}/api/presupuestos/{presupuestoid}", timeout=20)
    return _handle_response(r)


def listar_lineas(presupuestoid: int) -> list:
    r = requests.get(f"{_base_url()}/api/presupuestos/{presupuestoid}/lineas", timeout=20)
    return _handle_response(r)


def agregar_linea(presupuestoid: int, payload: dict) -> int:
    r = requests.post(f"{_base_url()}/api/presupuestos/{presupuestoid}/lineas", json=payload, timeout=20)
    return _handle_response(r)


def recalcular_lineas(presupuestoid: int, fecha_calculo: Optional[date] = None) -> dict:
    params = {"fecha_calculo": fecha_calculo.isoformat()} if fecha_calculo else None
    r = requests.post(
        f"{_base_url()}/api/presupuestos/{presupuestoid}/recalcular",
        params=params,
        timeout=30,
    )
    return _handle_response(r)


def convertir_a_pedido(presupuestoid: int) -> dict:
    r = requests.post(f"{_base_url()}/api/presupuestos/{presupuestoid}/convertir-a-pedido", timeout=30)
    return _handle_response(r)


def cliente_basico(clienteid: int) -> dict:
    r = requests.get(f"{_base_url()}/api/presupuestos/cliente/{clienteid}/basico", timeout=15)
    return _handle_response(r)
