from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.app.core.database import get_supabase
from backend.app.repositories.productos_repo import ProductosRepository
from backend.app.services.productos_service import ProductosService
from backend.app.schemas.producto import (
    ProductoListResponse,
    ProductoCatalogosResponse,
    ProductoDetail,
)

router = APIRouter(prefix="/api/productos", tags=["Productos"])


def get_productos_service(supabase=Depends(get_supabase)) -> ProductosService:
    repo = ProductosRepository(supabase)
    return ProductosService(repo)


@router.get("", response_model=ProductoListResponse)
def listar_productos(
    q: Optional[str] = Query(None),
    familiaid: Optional[int] = Query(None),
    tipoid: Optional[int] = Query(None),
    categoriaid: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    sort_field: str = Query("titulo_automatico"),
    sort_dir: str = Query("ASC", pattern="^(ASC|DESC)$"),
    service: ProductosService = Depends(get_productos_service),
):
    return service.listar(
        q=q,
        familiaid=familiaid,
        tipoid=tipoid,
        categoriaid=categoriaid,
        page=page,
        page_size=page_size,
        sort_field=sort_field,
        sort_dir=sort_dir,
    )


@router.get("/catalogos", response_model=ProductoCatalogosResponse)
def catalogos(service: ProductosService = Depends(get_productos_service)):
    return service.catalogos()


@router.get("/{productoid}", response_model=Optional[ProductoDetail])
def detalle(productoid: int, service: ProductosService = Depends(get_productos_service)):
    return service.detalle(productoid)
