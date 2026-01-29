# backend/app/api/clientes_convertir.py
from fastapi import APIRouter, Depends, HTTPException
from backend.app.schemas.cliente_convertir import ClienteConvertirResponse
from backend.app.services.cliente_convertir_service import ClienteConvertirService
from backend.app.core.database import get_supabase

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


@router.post("/{clienteid}/convertir", response_model=ClienteConvertirResponse)
def convertir_potencial(
    clienteid: int,
    supabase=Depends(get_supabase),
):
    service = ClienteConvertirService(supabase)
    try:
        return service.convertir(clienteid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
