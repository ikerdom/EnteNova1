from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.database import get_supabase
from backend.app.repositories.pedidos_repo import PedidosRepository
from backend.app.schemas.pedido import (
    PedidoListResponse,
    PedidoDetalleOut,
    PedidoLineaOut,
    PedidoTotalesOut,
    PedidoObservacionIn,
    PedidoCreateIn,
    PedidoUpdateIn,
    PedidoLineaCreate,
    PedidoCatalogos,
)
from backend.app.services.pedidos_service import PedidosService

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


def get_service(supabase=Depends(get_supabase)) -> PedidosService:
    repo = PedidosRepository(supabase)
    return PedidosService(repo)


@router.get("", response_model=PedidoListResponse)
def listar_pedidos(
    q: Optional[str] = Query(None),
    estadoid: Optional[int] = Query(None),
    tipo_pedidoid: Optional[int] = Query(None),
    procedencia_pedidoid: Optional[int] = Query(None),
    trabajadorid: Optional[int] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    devoluciones: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    service: PedidosService = Depends(get_service),
):
    filtros = {
        "q": q,
        "estadoid": estadoid,
        "tipo_pedidoid": tipo_pedidoid,
        "procedencia_pedidoid": procedencia_pedidoid,
        "trabajadorid": trabajadorid,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "tipo_devolucion": devoluciones,
    }
    return service.listar(filtros, page, page_size)


@router.get("/catalogos", response_model=PedidoCatalogos)
def catalogos_pedidos(service: PedidosService = Depends(get_service)):
    return service.catalogos()


@router.post("", response_model=PedidoDetalleOut)
def crear_pedido(body: PedidoCreateIn, service: PedidosService = Depends(get_service)):
    return service.crear(body)


@router.put("/{pedidoid}", response_model=PedidoDetalleOut)
def actualizar_pedido(pedidoid: int, body: PedidoUpdateIn, service: PedidosService = Depends(get_service)):
    try:
        return service.actualizar(pedidoid, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{pedidoid}")
def borrar_pedido(pedidoid: int, service: PedidosService = Depends(get_service)):
    service.borrar(pedidoid)
    return {"ok": True}


@router.get("/{pedidoid}", response_model=PedidoDetalleOut)
def obtener_pedido(pedidoid: int, service: PedidosService = Depends(get_service)):
    try:
        return service.detalle(pedidoid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{pedidoid}/lineas", response_model=list[PedidoLineaOut])
def lineas_pedido(pedidoid: int, service: PedidosService = Depends(get_service)):
    return service.lineas(pedidoid)


@router.post("/{pedidoid}/lineas", response_model=int)
def agregar_linea_pedido(pedidoid: int, body: PedidoLineaCreate, service: PedidosService = Depends(get_service)):
    return service.agregar_linea(pedidoid, body)


@router.delete("/{pedidoid}/lineas/{detalleid}")
def borrar_linea_pedido(pedidoid: int, detalleid: int, service: PedidosService = Depends(get_service)):
    service.borrar_linea(pedidoid, detalleid)
    return {"ok": True}


@router.get("/{pedidoid}/totales", response_model=Optional[PedidoTotalesOut])
def totales_pedido(pedidoid: int, service: PedidosService = Depends(get_service)):
    return service.totales(pedidoid)


@router.post("/{pedidoid}/recalcular-totales", response_model=PedidoTotalesOut)
def recalcular_totales(
    pedidoid: int,
    use_iva: bool = Query(True),
    gastos_envio: float = Query(0.0),
    envio_sin_cargo: bool = Query(False),
    service: PedidosService = Depends(get_service),
):
    try:
        return service.recalcular_totales(pedidoid, use_iva=use_iva, gastos_envio=gastos_envio, envio_sin_cargo=envio_sin_cargo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pedidoid}/observaciones")
def listar_observaciones(pedidoid: int, service: PedidosService = Depends(get_service)):
    return service.observaciones(pedidoid)


@router.post("/{pedidoid}/observaciones")
def crear_observacion(
    pedidoid: int,
    body: PedidoObservacionIn,
    service: PedidosService = Depends(get_service),
):
    service.crear_observacion(pedidoid, body, usuario=body.usuario or "sistema")
    return {"ok": True}
