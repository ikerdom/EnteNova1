from typing import Optional, Tuple, List


class ProductosRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def get_productos(
        self,
        q: Optional[str],
        familiaid: Optional[int],
        tipoid: Optional[int],
        categoriaid: Optional[int],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> Tuple[List[dict], int]:
        """
        Devuelve (productos, total)
        """
        query = self.supabase.table("producto").select("*", count="exact")

        if q:
            query = query.or_(
                ",".join(
                    [
                        f"titulo_automatico.ilike.%{q}%",
                        f"idproducto.ilike.%{q}%",
                        f"idproductoreferencia.ilike.%{q}%",
                        f"isbn.ilike.%{q}%",
                        f"ean.ilike.%{q}%",
                    ]
                )
            )

        if familiaid:
            query = query.eq("producto_familiaid", familiaid)

        if tipoid:
            query = query.eq("producto_tipoid", tipoid)

        if categoriaid:
            query = query.eq("producto_categoriaid", categoriaid)

        ascending = sort_dir.upper() == "ASC"
        query = query.order(sort_field, desc=not ascending)

        start = (page - 1) * page_size
        end = start + page_size - 1
        res = query.range(start, end).execute()

        data = res.data or []
        total = res.count or 0
        return data, total

    def get_catalogos(self) -> dict:
        def items(table: str, id_field: str, label_field: str, where=None, order_field=None):
            q = self.supabase.table(table).select(f"{id_field},{label_field}")
            if where:
                for k, v in where.items():
                    q = q.eq(k, v)
            if order_field:
                q = q.order(order_field)
            res = q.execute().data or []
            return [r for r in res if r.get(id_field) is not None]

        return {
            "familias": items("producto_familia", "producto_familiaid", "nombre", where={"habilitado": True}, order_field="nombre"),
            "tipos": items("producto_tipo", "producto_tipoid", "nombre", where={"habilitado": True}, order_field="nombre"),
            "categorias": items("producto_categoria", "producto_categoriaid", "nombre", where={"habilitado": True}, order_field="nombre"),
        }

    def get_producto(self, productoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("producto")
            .select("*")
            .eq("catalogo_productoid", productoid)
            .single()
            .execute()
        )
        return res.data if res and res.data else None
