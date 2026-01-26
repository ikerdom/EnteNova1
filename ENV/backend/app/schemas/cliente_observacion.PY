# backend/app/schemas/cliente_observacion.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


TIPOS_OBSERVACION = {
    "General",
    "Comercial",
    "Administración",
    "Otro",
}


class ClienteObservacionIn(BaseModel):
    tipo: str
    comentario: str
    usuario: str


class ClienteObservacionOut(BaseModel):
    cliente_observacionid: int
    clienteid: int

    tipo: str
    comentario: str
    usuario: str
    fecha: datetime
