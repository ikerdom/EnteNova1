# backend/app/schemas/cliente_contacto.py
from typing import Optional
from pydantic import BaseModel


class ClienteContactoIn(BaseModel):
    tipo: str  # TELEFONO | FAX | EMAIL
    valor: str
    principal: bool = False


class ClienteContactoOut(ClienteContactoIn):
    cliente_contactoid: int
    clienteid: int
    valor_norm: Optional[str] = None
