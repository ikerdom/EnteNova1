import math
from typing import Optional

from backend.app.schemas.producto import (
    ProductoOut,
    ProductoListResponse,
    ProductoCatalogosResponse,
    CatalogItem,
    ProductoDetail,
)
from backend.app.repositories.productos_repo import ProductosRepository


class ProductosService:
    def __init__(self, repo: ProductosRepository):
        self.repo = repo

    def listar(
        self,
        q: Optional[str],
        familiaid: Optional[int],
        tipoid: Optional[int],
        categoriaid: Optional[int],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> ProductoListResponse:
        raw, total = self.repo.get_productos(
            q=q,
            familiaid=familiaid,
            tipoid=tipoid,
            categoriaid=categoriaid,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )

        # catálogos para enriquecer labels
        cats = self.repo.get_catalogos()
        fam_map = {r["producto_familiaid"]: r["nombre"] for r in cats.get("familias", []) if r.get("producto_familiaid")}
        tipo_map = {r["producto_tipoid"]: r["nombre"] for r in cats.get("tipos", []) if r.get("producto_tipoid")}
        cat_map = {r["producto_categoriaid"]: r["nombre"] for r in cats.get("categorias", []) if r.get("producto_categoriaid")}

        productos = []
        for p in raw:
            productos.append(
                ProductoOut(
                    catalogo_productoid=p.get("catalogo_productoid"),
                    productoid=p.get("catalogo_productoid"),
                    titulo_automatico=p.get("titulo_automatico"),
                    idproducto=p.get("idproducto"),
                    idproductoreferencia=p.get("idproductoreferencia"),
                    isbn=p.get("isbn"),
                    ean=p.get("ean"),
                    producto_familiaid=p.get("producto_familiaid"),
                    producto_categoriaid=p.get("producto_categoriaid"),
                    producto_tipoid=p.get("producto_tipoid"),
                    pvp=p.get("pvp"),
                    portada_url=p.get("portada_url"),
                    familia=fam_map.get(p.get("producto_familiaid")),
                    tipo=tipo_map.get(p.get("producto_tipoid")),
                    categoria=cat_map.get(p.get("producto_categoriaid")),
                )
            )

        total_pages = max(1, math.ceil(total / page_size))
        return ProductoListResponse(
            data=productos,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    def catalogos(self) -> ProductoCatalogosResponse:
        cats = self.repo.get_catalogos()

        def to_items(rows: list, id_field: str, label_field: str):
            return [
                CatalogItem(id=int(r[id_field]), label=str(r[label_field]))
                for r in rows
                if r.get(id_field) is not None
            ]

        return ProductoCatalogosResponse(
            familias=to_items(cats.get("familias", []), "producto_familiaid", "nombre"),
            tipos=to_items(cats.get("tipos", []), "producto_tipoid", "nombre"),
            categorias=to_items(cats.get("categorias", []), "producto_categoriaid", "nombre"),
        )

    def detalle(self, productoid: int) -> Optional[ProductoDetail]:
        p = self.repo.get_producto(productoid)
        if not p:
            return None
        cats = self.repo.get_catalogos()
        fam_map = {r["producto_familiaid"]: r["nombre"] for r in cats.get("familias", []) if r.get("producto_familiaid")}
        tipo_map = {r["producto_tipoid"]: r["nombre"] for r in cats.get("tipos", []) if r.get("producto_tipoid")}
        cat_map = {r["producto_categoriaid"]: r["nombre"] for r in cats.get("categorias", []) if r.get("producto_categoriaid")}

        return ProductoDetail(
            catalogo_productoid=p.get("catalogo_productoid"),
            productoid=p.get("catalogo_productoid"),
            titulo_automatico=p.get("titulo_automatico"),
            idproducto=p.get("idproducto"),
            idproductoreferencia=p.get("idproductoreferencia"),
            isbn=p.get("isbn"),
            ean=p.get("ean"),
            pvp=p.get("pvp"),
            portada_url=p.get("portada_url"),
            publico=p.get("publico"),
            fecha_publicacion=p.get("fecha_publicacion"),
            familia=fam_map.get(p.get("producto_familiaid")),
            tipo=tipo_map.get(p.get("producto_tipoid")),
            categoria=cat_map.get(p.get("producto_categoriaid")),
        )
