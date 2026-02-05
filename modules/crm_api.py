"""
Cliente HTTP para CRM acciones (FastAPI).
"""
from typing import Any, Dict, Optional
import requests
from modules.api_base import get_api_base


def _handle(resp: requests.Response) -> Any:
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


def listar(params: Optional[dict] = None) -> dict:
    r = requests.get(f"{get_api_base()}/api/crm/acciones", params=params, timeout=20)
    return _handle(r)


def crear(payload: dict) -> dict:
    r = requests.post(f"{get_api_base()}/api/crm/acciones", json=payload, timeout=20)
    return _handle(r)


def actualizar(accionid: int, payload: dict) -> dict:
    r = requests.put(f"{get_api_base()}/api/crm/acciones/{accionid}", json=payload, timeout=20)
    return _handle(r)


def detalle(accionid: int) -> dict:
    r = requests.get(f"{get_api_base()}/api/crm/acciones/{accionid}", timeout=15)
    return _handle(r)


def catalogos() -> dict:
    r = requests.get(f"{get_api_base()}/api/crm/catalogos", timeout=15)
    return _handle(r)
