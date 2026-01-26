from datetime import date
from typing import List, Optional

from pydantic import BaseModel, model_validator


class CatalogoItem(BaseModel):
    id: int
    label: str


class TarifaCatalogos(BaseModel):
    tarifas: List[CatalogoItem]
    clientes: List[CatalogoItem]
    grupos: List[CatalogoItem]
    productos: List[CatalogoItem]
    familias: List[CatalogoItem]


class TarifaReglaBase(BaseModel):
    tarifaid: int
    clienteid: Optional[int] = None
    grupoid: Optional[int] = None
    idgrupo: Optional[int] = None
    productoid: Optional[int] = None
    catalogo_productoid: Optional[int] = None
    familia_productoid: Optional[int] = None
    producto_tipoid: Optional[int] = None
    tarifa_regla_tipoid: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    prioridad: Optional[int] = None
    habilitada: bool = True

    @model_validator(mode="after")
    def validar_objetivo(self):
        if not any(
            getattr(self, k)
            for k in ("clienteid", "idgrupo", "grupoid", "catalogo_productoid", "productoid", "familia_productoid")
        ):
            raise ValueError("Debes seleccionar al menos cliente/grupo/producto/familia")
        return self


class TarifaReglaCreate(TarifaReglaBase):
    pass


class TarifaReglaUpdate(BaseModel):
    habilitada: Optional[bool] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    prioridad: Optional[int] = None


class TarifaReglaOut(TarifaReglaBase):
    tarifa_reglaid: int


class TarifaReglaListResponse(BaseModel):
    data: List[TarifaReglaOut]
    total: int


class ClienteTarifaCreate(BaseModel):
    clienteid: int
    tarifaid: int
    fecha_desde: date
    fecha_hasta: Optional[date] = None


class PrecioRequest(BaseModel):
    clienteid: Optional[int] = None
    productoid: Optional[int] = None
    precio_base_unit: Optional[float] = None
    cantidad: float = 1.0
    fecha: Optional[date] = None


class PrecioResponse(BaseModel):
    unit_bruto: float
    descuento_pct: float
    unit_neto_sin_iva: float
    subtotal_sin_iva: float
    iva_pct: float
    iva_importe: float
    total_con_iva: float
    tarifaid: Optional[int] = None
    tarifa_aplicada: Optional[str] = None
    nivel_tarifa: Optional[str] = None
    regla_id: Optional[int] = None
    iva_nombre: Optional[str] = None
    iva_origen: Optional[str] = None
    region: Optional[str] = None
    region_origen: Optional[str] = None
