# backend/app/schemas/cliente_convertir.py
from typing import Optional
from pydantic import BaseModel


class ClienteConvertirResponse(BaseModel):
    clienteid: int
    tipo_cliente: str
    perfil_completo: bool
    mensaje: str
