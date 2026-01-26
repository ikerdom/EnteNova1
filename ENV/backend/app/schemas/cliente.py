# backend/app/schemas/cliente.py
from typing import Optional, List
from pydantic import BaseModel


# ============================
# Cliente (salida API)
# ============================
class ClienteOut(BaseModel):
    clienteid: int

    codigocuenta: Optional[str] = None
    codigoclienteoproveedor: Optional[str] = None
    clienteoproveedor: Optional[str] = None
    razonsocial: Optional[str] = None
    nombre: Optional[str] = None
    cifdni: Optional[str] = None
    cif_normalizado: Optional[str] = None

    viapublica: Optional[str] = None
    domicilio: Optional[str] = None
    codigopostal: Optional[str] = None
    provincia: Optional[str] = None
    municipio: Optional[str] = None

    telefono: Optional[str] = None
    telefono2: Optional[str] = None
    telefono3: Optional[str] = None
    fax: Optional[str] = None

    iban: Optional[str] = None
    codigobanco: Optional[str] = None
    codigoagencia: Optional[str] = None
    dc: Optional[str] = None
    ccc: Optional[str] = None

    codigotipoefecto: Optional[str] = None
    codigocuentaefecto: Optional[str] = None
    codigocuentaimpagado: Optional[str] = None
    remesahabitual: Optional[str] = None

    idgrupo: Optional[int] = None

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    data: List[ClienteOut]
    total: int
    total_pages: int
    page: int
    page_size: int


# ============================
# Cliente detalle
# ============================
class ClienteDireccion(BaseModel):
    clientes_direccionid: Optional[int] = None
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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ClienteContacto(BaseModel):
    cliente_contactoid: Optional[int] = None
    clienteid: Optional[int] = None
    tipo: Optional[str] = None
    valor: Optional[str] = None
    valor_norm: Optional[str] = None
    principal: Optional[bool] = None


class ClienteDetalle(BaseModel):
    cliente: ClienteOut
    direcciones: List[ClienteDireccion] = []
    contactos: List[ClienteContacto] = []
    contacto_principal: Optional[ClienteContacto] = None
