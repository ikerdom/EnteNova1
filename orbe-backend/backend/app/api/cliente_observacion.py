# backend/app/api/cliente_observacion.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.database import get_supabase
from backend.app.schemas.cliente_observacion import (
    ClienteObservacionIn,
    ClienteObservacionOut,
)
from backend.app.services.cliente_observacion_service import (
    ClienteObservacionService,
)

router = APIRouter(
    prefix="/api/clientes/{clienteid}/observaciones",
    tags=["Observaciones"],
)


@router.get("", response_model=List[ClienteObservacionOut])
def listar_observaciones(clienteid: int, supabase=Depends(get_supabase)):
    return ClienteObservacionService(supabase).listar(clienteid)


@router.post("")
def crear_observacion(
    clienteid: int,
    data: ClienteObservacionIn,
    supabase=Depends(get_supabase),
):
    svc = ClienteObservacionService(supabase)
    try:
        svc.crear(clienteid, data)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
