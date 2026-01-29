# backend/app/schemas/cliente_direccion.py
from typing import Optional
from pydantic import BaseModel


class ClienteDireccionIn(BaseModel):
    direccion_origen_id: Optional[int] = None
    idtercero: Optional[int] = None
    razonsocial: Optional[str] = None
    nombrecomercial: Optional[str] = None
    direccionfiscal: Optional[str] = None
    direccion: Optional[str] = None
    idpais: Optional[str] = None
    idprovincia: Optional[str] = None
    idmunicipio: Optional[str] = None
    codigopostal: Optional[str] = None
    rci_estado: Optional[str] = None
    rci_poblacion: Optional[str] = None
    rci_idterritorio: Optional[str] = None
    municipio: Optional[str] = None
    cif: Optional[str] = None
    referenciacliente: Optional[str] = None


class ClienteDireccionOut(ClienteDireccionIn):
    clientes_direccionid: int
