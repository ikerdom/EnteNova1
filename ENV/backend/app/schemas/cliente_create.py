from typing import Optional, List
from pydantic import BaseModel


class ClienteContactoIn(BaseModel):
    tipo: str  # TELEFONO | FAX | EMAIL
    valor: str
    principal: bool = False


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


class ClienteCreateIn(BaseModel):
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

    contactos: Optional[List[ClienteContactoIn]] = None
    direcciones: Optional[List[ClienteDireccionIn]] = None


class ClienteCreateOut(BaseModel):
    clienteid: int
    mensaje: str
