from postgrest.exceptions import APIError
# backend/app/repositories/pedidos_repo.py
from typing import List, Optional, Tuple


class PedidosRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listado
    # -----------------------------
    def listar(self, filtros: dict, page: int, page_size: int) -> Tuple[List[dict], int]:
        q = self.supabase.table("pedido").select("*", count="exact")

        if filtros.get("tipo_devolucion"):
            tipo_dev = (
                self.supabase.table("pedido_tipo")
                .select("tipo_pedidoid")
                .eq("nombre", "DevoluciÃ³n")
                .maybe_single()
                .execute()
                .data
            )
            if tipo_dev:
                q = q.eq("tipo_pedidoid", tipo_dev.get("tipo_pedidoid"))

        if filtros.get("q"):
            q = q.or_(f"numero.ilike.%{filtros['q']}%,referencia_cliente.ilike.%{filtros['q']}%")
        if filtros.get("estadoid"):
            q = q.eq("estado_pedidoid", filtros["estadoid"])
        if filtros.get("tipo_pedidoid"):
            q = q.eq("tipo_pedidoid", filtros["tipo_pedidoid"])
        if filtros.get("procedencia_pedidoid"):
            q = q.eq("procedencia_pedidoid", filtros["procedencia_pedidoid"])
        if filtros.get("trabajadorid"):
            q = q.eq("trabajadorid", filtros["trabajadorid"])
        if filtros.get("fecha_desde"):
            q = q.gte("fecha_pedido", filtros["fecha_desde"])
        if filtros.get("fecha_hasta"):
            q = q.lte("fecha_pedido", filtros["fecha_hasta"])

        start = (page - 1) * page_size
        end = start + page_size - 1
        try:
            res = q.order("fecha_pedido", desc=True).range(start, end).execute()
        except APIError as e:
            if getattr(e, "args", None) and isinstance(e.args[0], dict) and e.args[0].get("code") == "PGRST205":
                return [], 0
            raise

    # -----------------------------
    # Cabecera / detalle
    # -----------------------------
    def obtener(self, pedidoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("pedido")
            .select("*")
            .eq("pedidoid", pedidoid)
            .maybe_single()
            .execute()
        )
        return res.data or None

    def crear(self, data: dict) -> dict:
        res = self.supabase.table("pedido").insert(data).execute()
        return (res.data or [None])[0]

    def actualizar(self, pedidoid: int, data: dict):
        self.supabase.table("pedido").update(data).eq("pedidoid", pedidoid).execute()

    def borrar(self, pedidoid: int):
        self.supabase.table("pedido").delete().eq("pedidoid", pedidoid).execute()

    # -----------------------------
    # LÃ­neas
    # -----------------------------
    def lineas(self, pedidoid: int) -> List[dict]:
        res = (
            self.supabase.table("pedido_detalle")
            .select("pedido_detalleid, productoid, nombre_producto, cantidad, precio_unitario, descuento_pct, importe_total_linea")
            .eq("pedidoid", pedidoid)
            .order("pedido_detalleid")
            .execute()
        )
        return res.data or []

    def insertar_linea(self, data: dict) -> int:
        res = self.supabase.table("pedido_detalle").insert(data).execute()
        return res.data[0]["pedido_detalleid"]

    def borrar_linea(self, detalleid: int):
        self.supabase.table("pedido_detalle").delete().eq("pedido_detalleid", detalleid).execute()

    # -----------------------------
    # Totales
    # -----------------------------
    def totales(self, pedidoid: int) -> Optional[dict]:
        try:
            res = (
                self.supabase.table("pedido_totales")
                .select("*")
                .eq("pedidoid", pedidoid)
                .maybe_single()
                .execute()
            )
            return getattr(res, "data", None) or None
        except Exception:
            return None

    def actualizar_totales(self, pedidoid: int, payload: dict):
        exists = self.totales(pedidoid)
        if exists:
            self.supabase.table("pedido_totales").update(payload).eq("pedidoid", pedidoid).execute()
        else:
            payload["pedidoid"] = pedidoid
            self.supabase.table("pedido_totales").insert(payload).execute()

    # -----------------------------
    # Observaciones
    # -----------------------------
    def observaciones(self, pedidoid: int) -> List[dict]:
        res = (
            self.supabase.table("pedido_observacion")
            .select("comentario, tipo, fecha, usuario")
            .eq("pedidoid", pedidoid)
            .order("fecha", desc=True)
            .execute()
        )
        return res.data or []

    def crear_observacion(self, pedidoid: int, data: dict):
        data["pedidoid"] = pedidoid
        self.supabase.table("pedido_observacion").insert(data).execute()

    # -----------------------------
    # Catálogos
    # -----------------------------
    def catalogo(self, table: str, id_field: str, label_field: str, where_enabled: bool = False, order_field: Optional[str] = None) -> List[dict]:
        q = self.supabase.table(table).select(f"{id_field},{label_field}")
        if where_enabled:
            try:
                q = q.eq("habilitado", True)
            except Exception:
                pass
        if order_field:
            try:
                q = q.order(order_field)
            except Exception:
                pass
        try:
            res = q.execute()
            return res.data or []
        except Exception:
            return []
