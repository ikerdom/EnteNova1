# backend/app/api/crm_actuacion.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.database import get_supabase
from backend.app.schemas.crm_actuacion import CrmActuacionIn, CrmActuacionOut
from backend.app.services.crm_actuacion_service import CrmActuacionService

router = APIRouter(
    prefix="/api/clientes/{clienteid}/crm",
    tags=["CRM"],
)


@router.get("", response_model=List[CrmActuacionOut])
def listar_crm(clienteid: int, supabase=Depends(get_supabase)):
    return CrmActuacionService(supabase).listar(clienteid)


@router.post("")
def crear_crm(
    clienteid: int,
    data: CrmActuacionIn,
    supabase=Depends(get_supabase),
):
    svc = CrmActuacionService(supabase)
    try:
        svc.crear(clienteid, data)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{crm_id}")
def actualizar_crm(
    clienteid: int,
    crm_id: int,
    data: CrmActuacionIn,
    supabase=Depends(get_supabase),
):
    svc = CrmActuacionService(supabase)
    try:
        svc.actualizar(crm_id, data)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
