from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.database import get_supabase
from backend.app.repositories.tarifas_repo import TarifasRepository
from backend.app.schemas.tarifa import (
    TarifaCatalogos,
    TarifaReglaListResponse,
    TarifaReglaCreate,
    TarifaReglaOut,
    TarifaReglaUpdate,
    ClienteTarifaCreate,
    PrecioRequest,
    PrecioResponse,
)
from backend.app.services.tarifas_service import TarifasService

router = APIRouter(prefix="/api/tarifas", tags=["Tarifas"])


def get_service(supabase=Depends(get_supabase)) -> TarifasService:
    repo = TarifasRepository(supabase)
    return TarifasService(repo)


@router.get("/catalogos", response_model=TarifaCatalogos)
def catalogos(service: TarifasService = Depends(get_service)):
    return service.catalogos()


@router.get("/reglas", response_model=TarifaReglaListResponse)
def listar_reglas(
    clienteid: Optional[int] = Query(None),
    grupoid: Optional[int] = Query(None),
    productoid: Optional[int] = Query(None),
    familiaid: Optional[int] = Query(None),
    tarifaid: Optional[int] = Query(None),
    incluir_deshabilitadas: bool = Query(False),
    service: TarifasService = Depends(get_service),
):
    return service.listar_reglas(
        clienteid=clienteid,
        grupoid=grupoid,
        productoid=productoid,
        familiaid=familiaid,
        tarifaid=tarifaid,
        incluir_deshabilitadas=incluir_deshabilitadas,
    )


@router.post("/reglas", response_model=TarifaReglaOut)
def crear_regla(body: TarifaReglaCreate, service: TarifasService = Depends(get_service)):
    try:
        return service.crear_regla(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/reglas/{reglaid}", response_model=TarifaReglaOut)
def actualizar_regla(
    reglaid: int,
    body: TarifaReglaUpdate,
    service: TarifasService = Depends(get_service),
):
    try:
        return service.actualizar_regla(reglaid, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/reglas/{reglaid}")
def borrar_regla(reglaid: int, service: TarifasService = Depends(get_service)):
    service.borrar_regla(reglaid)
    return {"ok": True}


@router.post("/cliente-tarifa")
def asignar_cliente_tarifa(body: ClienteTarifaCreate, service: TarifasService = Depends(get_service)):
    try:
        return service.asignar_cliente_tarifa(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calcular-precio", response_model=PrecioResponse)
def calcular_precio(body: PrecioRequest, service: TarifasService = Depends(get_service)):
    return service.calcular_precio(body)
