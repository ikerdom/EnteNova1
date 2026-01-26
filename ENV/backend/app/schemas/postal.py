from typing import Optional
from pydantic import BaseModel


class PostalLocalidadOut(BaseModel):
    postallocid: int
    codigo_postal: Optional[str] = None
    municipio: Optional[str] = None
    provincia_nombre_raw: Optional[str] = None
    region_nombre_raw: Optional[str] = None
