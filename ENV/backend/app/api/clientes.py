from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.app.core.database import get_supabase

from backend.app.schemas.cliente import ClienteListResponse, ClienteDetalle
from backend.app.services.clientes_service import ClientesService
from backend.app.repositories.clientes_repo import ClientesRepository

from backend.app.schemas.catalogos import CatalogosResponse, CatalogItem
from backend.app.schemas.cliente_create import ClienteCreateIn, ClienteCreateOut
from backend.app.services.clientes_create_service import ClientesCreateService

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


def get_clientes_service(supabase=Depends(get_supabase)) -> ClientesService:
    repo = ClientesRepository(supabase)
    return ClientesService(repo)


@router.get("", response_model=ClienteListResponse)
def listar_clientes(
    q: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    idgrupo: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    sort_field: str = Query("razonsocial"),
    sort_dir: str = Query("ASC", pattern="^(ASC|DESC)$"),
    service: ClientesService = Depends(get_clientes_service),
):
    return service.listar_clientes(
        q=q,
        tipo=tipo,
        idgrupo=idgrupo,
        page=page,
        page_size=page_size,
        sort_field=sort_field,
        sort_dir=sort_dir,
    )


@router.get("/catalogos", response_model=CatalogosResponse)
def catalogos(supabase=Depends(get_supabase)):
    def items(table: str, id_field: str, label_field: str, where=None, order_field=None):
        try:
            q = supabase.table(table).select(f"{id_field},{label_field}")
            if where:
                for k, v in where.items():
                    q = q.eq(k, v)
            if order_field:
                q = q.order(order_field)
            data = q.execute().data or []
            return [CatalogItem(id=int(r[id_field]), label=str(r[label_field])) for r in data if r.get(id_field) is not None]
        except Exception:
            return []

    return CatalogosResponse(
        grupos=items("grupo", "idgrupo", "grupo_nombre", order_field="grupo_nombre"),
    )


@router.get("/{clienteid}", response_model=ClienteDetalle)
def obtener_cliente(
    clienteid: int,
    service: ClientesService = Depends(get_clientes_service),
):
    try:
        return service.obtener_detalle(clienteid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")


@router.post("", response_model=ClienteCreateOut)
def crear_cliente(
    body: ClienteCreateIn,
    supabase=Depends(get_supabase),
):
    service = ClientesCreateService(supabase)
    return service.crear(body)


@router.put("/{clienteid}", response_model=ClienteCreateOut)
def actualizar_cliente(
    clienteid: int,
    body: ClienteCreateIn,
    service: ClientesService = Depends(get_clientes_service),
):
    try:
        return service.actualizar_cliente(clienteid, body)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
