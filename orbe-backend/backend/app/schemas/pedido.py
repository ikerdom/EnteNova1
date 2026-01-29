from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class PedidoOut(BaseModel):
    pedidoid: int
    numero: Optional[str] = None
    clienteid: Optional[int] = None
    trabajadorid: Optional[int] = None
    tipo_pedidoid: Optional[int] = None
    procedencia_pedidoid: Optional[int] = None
    estado_pedidoid: Optional[int] = None
    formapagoid: Optional[int] = None
    fecha_pedido: Optional[date] = None
    referencia_cliente: Optional[str] = None
    presupuesto_origenid: Optional[int] = None
    estado_incidencia: Optional[str] = None


class PedidoListResponse(BaseModel):
    data: List[PedidoOut]
    total: int
    total_pages: int
    page: int
    page_size: int


class PedidoDetalleOut(PedidoOut):
    fecha_confirmada: Optional[date] = None
    fecha_limite: Optional[date] = None
    fecha_envio: Optional[date] = None
    fecha_entrega_prevista: Optional[date] = None
    facturar_individual: Optional[bool] = None


class PedidoCreateIn(BaseModel):
    numero: str
    clienteid: Optional[int] = None
    trabajadorid: Optional[int] = None
    tipo_pedidoid: Optional[int] = None
    procedencia_pedidoid: Optional[int] = None
    estado_pedidoid: Optional[int] = None
    formapagoid: Optional[int] = None
    transportistaid: Optional[int] = None
    fecha_pedido: date
    referencia_cliente: Optional[str] = None
    justificante_pago_url: Optional[str] = None
    facturar_individual: Optional[bool] = False
    pedido_origenid: Optional[int] = None


class PedidoUpdateIn(BaseModel):
    numero: Optional[str] = None
    clienteid: Optional[int] = None
    trabajadorid: Optional[int] = None
    tipo_pedidoid: Optional[int] = None
    procedencia_pedidoid: Optional[int] = None
    estado_pedidoid: Optional[int] = None
    formapagoid: Optional[int] = None
    transportistaid: Optional[int] = None
    fecha_pedido: Optional[date] = None
    referencia_cliente: Optional[str] = None
    justificante_pago_url: Optional[str] = None
    facturar_individual: Optional[bool] = None
    pedido_origenid: Optional[int] = None


class PedidoLineaOut(BaseModel):
    pedido_detalleid: int
    productoid: Optional[int] = None
    nombre_producto: Optional[str] = None
    cantidad: Optional[float] = None
    precio_unitario: Optional[float] = None
    descuento_pct: Optional[float] = None
    importe_total_linea: Optional[float] = None


class PedidoLineaCreate(BaseModel):
    productoid: Optional[int] = None
    nombre_producto: Optional[str] = None
    cantidad: float = 1.0
    precio_unitario: float
    descuento_pct: Optional[float] = 0.0


class PedidoTotalesOut(BaseModel):
    pedidoid: int
    base_imponible: Optional[float] = None
    iva_importe: Optional[float] = None
    total_importe: Optional[float] = None
    gastos_envio: Optional[float] = None
    envio_sin_cargo: Optional[bool] = None
    fecha_recalculo: Optional[datetime] = None


class PedidoObservacionIn(BaseModel):
    tipo: str
    comentario: str
    usuario: str


class CatalogoItem(BaseModel):
    id: int
    label: str


class PedidoCatalogos(BaseModel):
    clientes: list[CatalogoItem]
    trabajadores: list[CatalogoItem]
    estados: list[CatalogoItem]
    tipos: list[CatalogoItem]
    procedencias: list[CatalogoItem]
    formas_pago: list[CatalogoItem]
    transportistas: list[CatalogoItem]
