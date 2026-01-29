from typing import List
from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: int
    label: str


class CatalogosResponse(BaseModel):
    estados: List[CatalogItem] = []
    categorias: List[CatalogItem] = []
    formas_pago: List[CatalogItem] = []
    grupos: List[CatalogItem] = []
    trabajadores: List[CatalogItem] = []
    tarifas: List[CatalogItem] = []
