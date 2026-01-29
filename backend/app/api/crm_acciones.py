from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.database import get_supabase
from backend.app.repositories.crm_repo import CrmRepository
from backend.app.schemas.crm import CrmAccionCreate, CrmAccionUpdate, CrmAccionList, CrmAccionOut
from backend.app.services.crm_service import CrmService

router = APIRouter(prefix="/api/crm/acciones", tags=["CRM"])


def get_service(supabase=Depends(get_supabase)) -> CrmService:
    repo = CrmRepository(supabase)
    return CrmService(repo)


@router.get("", response_model=CrmAccionList)
def listar_acciones(
    trabajador_asignadoid: Optional[int] = Query(None),
    clienteid: Optional[int] = Query(None),
    crm_actuacion_estadoid: Optional[int] = Query(None),
    crm_actuacion_tipoid: Optional[int] = Query(None),
    buscar: Optional[str] = Query(None),
    service: CrmService = Depends(get_service),
):
    filtros = {
        "trabajador_asignadoid": trabajador_asignadoid,
        "clienteid": clienteid,
        "crm_actuacion_estadoid": crm_actuacion_estadoid,
        "crm_actuacion_tipoid": crm_actuacion_tipoid,
        "buscar": buscar,
    }
    return service.listar(filtros)


@router.post("", response_model=CrmAccionOut)
def crear_accion(body: CrmAccionCreate, service: CrmService = Depends(get_service)):
    return service.crear(body)


@router.put("/{accionid}", response_model=CrmAccionOut)
def actualizar_accion(accionid: int, body: CrmAccionUpdate, service: CrmService = Depends(get_service)):
    try:
        return service.actualizar(accionid, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{accionid}", response_model=CrmAccionOut)
def obtener_accion(accionid: int, service: CrmService = Depends(get_service)):
    try:
        return service.obtener(accionid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
