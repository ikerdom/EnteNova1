import math
from datetime import datetime
from typing import Optional

from backend.app.repositories.pedidos_repo import PedidosRepository
from backend.app.schemas.pedido import (
    PedidoListResponse,
    PedidoOut,
    PedidoDetalleOut,
    PedidoLineaOut,
    PedidoTotalesOut,
    PedidoObservacionIn,
    PedidoCreateIn,
    PedidoUpdateIn,
    PedidoLineaCreate,
    PedidoCatalogos,
    CatalogoItem,
)
from backend.app.services.precio_engine import calcular_precio_linea


class PedidosService:
    def __init__(self, repo: PedidosRepository):
        self.repo = repo

    # -----------------------------
    # Listar
    # -----------------------------
    def listar(
        self,
        filtros: dict,
        page: int,
        page_size: int,
    ) -> PedidoListResponse:
        rows, total = self.repo.listar(filtros, page, page_size)
        data = [PedidoOut(**r) for r in rows]
        total_pages = max(1, math.ceil((total or 0) / page_size))
        return PedidoListResponse(
            data=data,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    # -----------------------------
    # Detalle
    # -----------------------------
    def detalle(self, pedidoid: int) -> PedidoDetalleOut:
        ped = self.repo.obtener(pedidoid)
        if not ped:
            raise ValueError("Pedido no encontrado")
        return PedidoDetalleOut(**ped)

    def crear(self, data: PedidoCreateIn) -> PedidoDetalleOut:
        created = self.repo.crear(data.dict(exclude_none=True))
        if not created:
            raise RuntimeError("No se pudo crear el pedido")
        return PedidoDetalleOut(**created)

    def actualizar(self, pedidoid: int, data: PedidoUpdateIn) -> PedidoDetalleOut:
        if not self.repo.obtener(pedidoid):
            raise ValueError("Pedido no encontrado")
        self.repo.actualizar(pedidoid, data.dict(exclude_none=True))
        nuevo = self.repo.obtener(pedidoid)
        return PedidoDetalleOut(**nuevo)

    def borrar(self, pedidoid: int):
        self.repo.borrar(pedidoid)

    # -----------------------------
    # Líneas
    # -----------------------------
    def lineas(self, pedidoid: int):
        return [PedidoLineaOut(**l) for l in self.repo.lineas(pedidoid)]

    def agregar_linea(self, pedidoid: int, data: PedidoLineaCreate) -> int:
        payload = data.dict(exclude_none=True)
        payload["pedidoid"] = pedidoid
        return self.repo.insertar_linea(payload)

    def borrar_linea(self, pedidoid: int, detalleid: int):
        self.repo.borrar_linea(detalleid)

    # -----------------------------
    # Totales
    # -----------------------------
    def totales(self, pedidoid: int) -> Optional[PedidoTotalesOut]:
        t = self.repo.totales(pedidoid)
        if t:
            return PedidoTotalesOut(**t)
        # Si no hay registro en pedido_totales, devolvemos ceros para no romper la UI
        return PedidoTotalesOut(
            pedidoid=pedidoid,
            base_imponible=0.0,
            iva_importe=0.0,
            total_importe=0.0,
            gastos_envio=0.0,
            envio_sin_cargo=False,
            fecha_recalculo=None,
        )

    def recalcular_totales(self, pedidoid: int, use_iva: bool = True, gastos_envio: float = 0.0, envio_sin_cargo: bool = False):
        ped = self.repo.obtener(pedidoid)
        if not ped:
            raise ValueError("Pedido no encontrado")

        lineas = self.repo.lineas(pedidoid)
        if not lineas:
            raise ValueError("No hay líneas en el pedido")

        base_total = iva_total = 0.0
        for l in lineas:
            engine = calcular_precio_linea(
                supabase=self.repo.supabase,
                clienteid=ped.get("clienteid"),
                productoid=l.productoid,
                precio_base_unit=l.precio_unitario,
                cantidad=l.cantidad or 1,
            )
            subtotal = engine["unit_neto_sin_iva"] * (l.cantidad or 1)
            base_total += subtotal
            iva_pct = engine["iva_pct"] if use_iva else 0.0
            iva_total += subtotal * (iva_pct / 100.0)

        total_importe = base_total + iva_total + (gastos_envio or 0.0)
        payload = {
            "base_imponible": round(base_total, 2),
            "iva_importe": round(iva_total, 2),
            "total_importe": round(total_importe, 2),
            "gastos_envio": round(gastos_envio or 0.0, 2),
            "envio_sin_cargo": bool(envio_sin_cargo),
            "fecha_recalculo": datetime.now().isoformat(),
        }
        self.repo.actualizar_totales(pedidoid, payload)
        return PedidoTotalesOut(pedidoid=pedidoid, **payload)

    # -----------------------------
    # Observaciones
    # -----------------------------
    def observaciones(self, pedidoid: int):
        return self.repo.observaciones(pedidoid)

    def crear_observacion(self, pedidoid: int, data: PedidoObservacionIn, usuario: str):
        payload = data.dict()
        payload["usuario"] = usuario
        payload["fecha"] = datetime.now().isoformat(timespec="seconds")
        self.repo.crear_observacion(pedidoid, payload)

    # -----------------------------
    # Catálogos
    # -----------------------------
    def catalogos(self) -> PedidoCatalogos:
        def to_items(rows: list, id_field: str, label_field: str):
            return [
                CatalogoItem(id=int(r[id_field]), label=str(r[label_field]))
                for r in rows
                if r.get(id_field) is not None
            ]

        return PedidoCatalogos(
            clientes=to_items(self.repo.catalogo("cliente", "clienteid", "razonsocial", order_field="razonsocial"), "clienteid", "razonsocial"),
            trabajadores=to_items(self.repo.catalogo("trabajador", "trabajadorid", "nombre", order_field="nombre"), "trabajadorid", "nombre"),
            estados=to_items(self.repo.catalogo("pedido_estado", "estado_pedidoid", "nombre", where_enabled=True, order_field=None), "estado_pedidoid", "nombre"),
            tipos=to_items(self.repo.catalogo("pedido_tipo", "tipo_pedidoid", "nombre", where_enabled=True, order_field="nombre"), "tipo_pedidoid", "nombre"),
            procedencias=to_items(self.repo.catalogo("pedido_procedencia", "procedencia_pedidoid", "nombre", where_enabled=True, order_field="nombre"), "procedencia_pedidoid", "nombre"),
            formas_pago=to_items(self.repo.catalogo("forma_pago", "formapagoid", "nombre", where_enabled=True, order_field=None), "formapagoid", "nombre"),
            transportistas=to_items(self.repo.catalogo("transportista", "transportistaid", "nombre", where_enabled=True, order_field="nombre"), "transportistaid", "nombre"),
        )
