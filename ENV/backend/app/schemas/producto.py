from typing import Optional, List
from pydantic import BaseModel


class ProductoOut(BaseModel):
    catalogo_productoid: int
    productoid: Optional[int] = None
    titulo_automatico: Optional[str] = None
    idproducto: Optional[str] = None
    idproductoreferencia: Optional[str] = None
    isbn: Optional[str] = None
    ean: Optional[str] = None
    producto_familiaid: Optional[int] = None
    producto_categoriaid: Optional[int] = None
    producto_tipoid: Optional[int] = None
    pvp: Optional[float] = None
    portada_url: Optional[str] = None

    # labels enriquecidos
    familia: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None

    class Config:
        from_attributes = True


class ProductoListResponse(BaseModel):
    data: List[ProductoOut]
    total: int
    total_pages: int
    page: int
    page_size: int


class CatalogItem(BaseModel):
    id: int
    label: str


class ProductoCatalogosResponse(BaseModel):
    familias: List[CatalogItem]
    tipos: List[CatalogItem]
    categorias: List[CatalogItem]


class ProductoDetail(BaseModel):
    catalogo_productoid: int
    productoid: Optional[int] = None
    titulo_automatico: Optional[str] = None
    idproducto: Optional[str] = None
    idproductoreferencia: Optional[str] = None
    isbn: Optional[str] = None
    ean: Optional[str] = None
    pvp: Optional[float] = None
    portada_url: Optional[str] = None
    publico: Optional[bool] = None
    fecha_publicacion: Optional[str] = None
    familia: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
