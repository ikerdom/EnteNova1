from typing import List
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.database import get_supabase
from backend.app.schemas.cliente_contacto import ClienteContactoIn, ClienteContactoOut
from backend.app.services.cliente_contacto_service import ClienteContactoService

router = APIRouter(
    prefix="/api/clientes/{clienteid}/contactos",
    tags=["Contactos"],
)


def get_service(supabase=Depends(get_supabase)) -> ClienteContactoService:
    return ClienteContactoService(supabase)


@router.get("", response_model=List[ClienteContactoOut])
def listar_contactos(
    clienteid: int,
    service: ClienteContactoService = Depends(get_service),
):
    return service.listar(clienteid)


@router.post("", response_model=int)
def crear_contacto(
    clienteid: int,
    body: ClienteContactoIn,
    service: ClienteContactoService = Depends(get_service),
):
    try:
        return service.crear(clienteid, body.dict(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{contactoid}")
def actualizar_contacto(
    clienteid: int,
    contactoid: int,
    body: ClienteContactoIn,
    service: ClienteContactoService = Depends(get_service),
):
    try:
        service.actualizar(clienteid, contactoid, body.dict(exclude_none=True))
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{contactoid}")
def borrar_contacto(
    clienteid: int,
    contactoid: int,
    service: ClienteContactoService = Depends(get_service),
):
    service.borrar(clienteid, contactoid)
    return {"ok": True}


@router.post("/{contactoid}/hacer-principal")
def hacer_principal(
    clienteid: int,
    contactoid: int,
    service: ClienteContactoService = Depends(get_service),
):
    try:
        service.hacer_principal(clienteid, contactoid)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
