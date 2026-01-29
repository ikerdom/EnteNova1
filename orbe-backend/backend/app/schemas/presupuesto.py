from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class PresupuestoListItem(BaseModel):
    presupuestoid: int
    numero: Optional[str] = None
    clienteid: Optional[int] = None
    cliente: Optional[str] = None
    estado_presupuestoid: Optional[int] = None
    estado: Optional[str] = None
    bloquea_edicion: Optional[bool] = None
    fecha_presupuesto: Optional[date] = None
    fecha_validez: Optional[date] = None
    ambito_impuesto: Optional[str] = None
    num_lineas: Optional[int] = None
    base_imponible: Optional[float] = None
    iva_total: Optional[float] = None
    total_documento: Optional[float] = None
    total_estimada: Optional[float] = None
    trabajadorid: Optional[int] = None


class PresupuestoListResponse(BaseModel):
    data: List[PresupuestoListItem]
    total: int
    total_pages: int
    page: int
    page_size: int


class PresupuestoBase(BaseModel):
    numero: Optional[str] = None
    clienteid: int
    trabajadorid: Optional[int] = None
    referencia_cliente: Optional[str] = None
    fecha_presupuesto: date
    fecha_validez: date
    ambito_impuesto: Optional[str] = None
    observaciones: Optional[str] = None
    facturar_individual: bool = False
    contacto_att: Optional[str] = None
    telefono_contacto: Optional[str] = None
    direccion_envioid: Optional[int] = None
    formapagoid: Optional[int] = None
    estado_presupuestoid: Optional[int] = None
    regionid: Optional[int] = None


class PresupuestoCreateIn(PresupuestoBase):
    pass


class PresupuestoUpdateIn(BaseModel):
    numero: Optional[str] = None
    trabajadorid: Optional[int] = None
    referencia_cliente: Optional[str] = None
    fecha_presupuesto: Optional[date] = None
    fecha_validez: Optional[date] = None
    ambito_impuesto: Optional[str] = None
    observaciones: Optional[str] = None
    facturar_individual: Optional[bool] = None
    contacto_att: Optional[str] = None
    telefono_contacto: Optional[str] = None
    direccion_envioid: Optional[int] = None
    formapagoid: Optional[int] = None
    estado_presupuestoid: Optional[int] = None
    regionid: Optional[int] = None


class PresupuestoOut(PresupuestoBase):
    presupuestoid: int
    editable: Optional[bool] = True
    total_estimada: Optional[float] = None
    estado: Optional[str] = None
    bloquea_edicion: Optional[bool] = None
    base_imponible: Optional[float] = None
    iva_total: Optional[float] = None
    total_documento: Optional[float] = None


class PresupuestoLineaBase(BaseModel):
    productoid: int
    cantidad: float = 1.0
    descuento_pct: Optional[float] = None
    descripcion: Optional[str] = None


class PresupuestoLineaIn(PresupuestoLineaBase):
    pass


class PresupuestoLineaOut(BaseModel):
    presupuesto_detalleid: int
    productoid: Optional[int] = None
    descripcion: Optional[str] = None
    cantidad: Optional[float] = None
    precio_unitario: Optional[float] = None
    descuento_pct: Optional[float] = None
    iva_pct: Optional[float] = None
    importe_base: Optional[float] = None
    importe_total_linea: Optional[float] = None
    base_linea: Optional[float] = None
    iva_importe: Optional[float] = None
    total_linea: Optional[float] = None
    tarifa_aplicada: Optional[str] = None
    nivel_tarifa: Optional[str] = None
    iva_origen: Optional[str] = None


class PresupuestoRecalcResponse(BaseModel):
    base_imponible: float
    iva_total: float
    total_presupuesto: float
    fecha_recalculo: datetime


class PresupuestoCatalogos(BaseModel):
    estados: List[dict]
    clientes: List[dict]
    trabajadores: List[dict]
    formas_pago: List[dict]
