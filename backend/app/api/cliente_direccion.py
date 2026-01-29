# backend/app/api/cliente_direccion.py
from fastapi import APIRouter, Depends
from backend.app.schemas.cliente_direccion import (
    ClienteDireccionIn,
    ClienteDireccionOut,
)
from backend.app.services.cliente_direccion_service import ClienteDireccionService
from backend.app.core.database import get_supabase

router = APIRouter(
    prefix="/api/clientes/{clienteid}/direcciones",
    tags=["Direcciones"],
)


@router.get("")
def listar_direcciones(clienteid: int, supabase=Depends(get_supabase)):
    return ClienteDireccionService(supabase).listar(clienteid)


@router.post("")
def crear_direccion(
    clienteid: int,
    data: ClienteDireccionIn,
    supabase=Depends(get_supabase),
):
    ClienteDireccionService(supabase).crear(
        clienteid, data.dict(exclude_none=True)
    )
    return {"ok": True}


@router.put("/{direccionid}")
def actualizar_direccion(
    clienteid: int,
    direccionid: int,
    data: ClienteDireccionIn,
    supabase=Depends(get_supabase),
):
    ClienteDireccionService(supabase).actualizar(
        clienteid, direccionid, data.dict(exclude_none=True)
    )
    return {"ok": True}


@router.delete("/{direccionid}")
def borrar_direccion(
    clienteid: int,
    direccionid: int,
    supabase=Depends(get_supabase),
):
    ClienteDireccionService(supabase).borrar(direccionid)
    return {"ok": True}


