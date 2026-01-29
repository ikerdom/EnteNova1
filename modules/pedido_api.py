"""
Cliente HTTP para pedidos (FastAPI).
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
    r = requests.get(f"{_base_url()}/api/pedidos", params=params, timeout=20)
    return _handle(r)

def catalogos() -> dict:
    r = requests.get(f"{_base_url()}/api/pedidos/catalogos", timeout=20)
    return _handle(r)

def crear_pedido(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/pedidos", json=payload, timeout=20)
    return _handle(r)

def actualizar_pedido(pedidoid: int, payload: dict) -> dict:
    r = requests.put(f"{_base_url()}/api/pedidos/{pedidoid}", json=payload, timeout=20)
    return _handle(r)

def borrar_pedido(pedidoid: int) -> dict:
    r = requests.delete(f"{_base_url()}/api/pedidos/{pedidoid}", timeout=20)
    return _handle(r)


def detalle(pedidoid: int) -> dict:
    r = requests.get(f"{_base_url()}/api/pedidos/{pedidoid}", timeout=15)
    return _handle(r)


def lineas(pedidoid: int) -> list:
    r = requests.get(f"{_base_url()}/api/pedidos/{pedidoid}/lineas", timeout=15)
    return _handle(r)


def totales(pedidoid: int) -> dict:
    r = requests.get(f"{_base_url()}/api/pedidos/{pedidoid}/totales", timeout=15)
    return _handle(r)


def recalcular_totales(pedidoid: int, use_iva: bool, gastos_envio: float, envio_sin_cargo: bool) -> dict:
    params = {
        "use_iva": use_iva,
        "gastos_envio": gastos_envio,
        "envio_sin_cargo": envio_sin_cargo,
    }
    r = requests.post(f"{_base_url()}/api/pedidos/{pedidoid}/recalcular-totales", params=params, timeout=30)
    return _handle(r)

def agregar_linea(pedidoid: int, payload: dict) -> int:
    r = requests.post(f"{_base_url()}/api/pedidos/{pedidoid}/lineas", json=payload, timeout=20)
    return _handle(r)

def borrar_linea(pedidoid: int, detalleid: int) -> dict:
    r = requests.delete(f"{_base_url()}/api/pedidos/{pedidoid}/lineas/{detalleid}", timeout=20)
    return _handle(r)


def observaciones(pedidoid: int) -> list:
    r = requests.get(f"{_base_url()}/api/pedidos/{pedidoid}/observaciones", timeout=15)
    return _handle(r)


def crear_observacion(pedidoid: int, payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/pedidos/{pedidoid}/observaciones", json=payload, timeout=15)
    return _handle(r)
