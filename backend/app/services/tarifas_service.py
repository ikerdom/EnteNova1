# backend/app/services/tarifas_service.py
from datetime import date
from typing import Optional

from backend.app.repositories.tarifas_repo import TarifasRepository
from backend.app.schemas.tarifa import (
    CatalogoItem,
    ClienteTarifaCreate,
    PrecioRequest,
    PrecioResponse,
    TarifaCatalogos,
    TarifaReglaCreate,
    TarifaReglaListResponse,
    TarifaReglaOut,
    TarifaReglaUpdate,
)
from backend.app.services.precio_engine import calcular_precio_linea


class TarifasService:
    def __init__(self, repo: TarifasRepository):
        self.repo = repo

    # -----------------------------
    # Catalogos
    # -----------------------------
    def catalogos(self) -> TarifaCatalogos:
        def to_items(rows: list, id_field: str, label_field: str):
            return [
                CatalogoItem(id=int(r[id_field]), label=str(r[label_field]))
                for r in rows
                if r.get(id_field) is not None
            ]

        tarifas = self.repo.catalogo("tarifa", "tarifaid", "nombre", where_enabled=False, order_field="tarifaid")
        clientes = self.repo.catalogo("cliente", "clienteid", "razonsocial", order_field="razonsocial")
        grupos = self.repo.catalogo("grupo", "idgrupo", "grupo_nombre", order_field="grupo_nombre")
        try:
            productos = (
                self.repo.supabase.table("producto")
                .select("catalogo_productoid, titulo_automatico, idproducto")
                .order("titulo_automatico")
                .execute()
                .data
                or []
            )
        except Exception:
            productos = []
        familias = self.repo.catalogo("producto_familia", "producto_familiaid", "nombre", order_field="nombre")

        return TarifaCatalogos(
            tarifas=to_items(tarifas, "tarifaid", "nombre"),
            clientes=to_items(clientes, "clienteid", "razonsocial"),
            grupos=to_items(grupos, "idgrupo", "grupo_nombre"),
            productos=[
                CatalogoItem(
                    id=int(p["catalogo_productoid"]),
                    label=str(
                        p.get("titulo_automatico")
                        or p.get("idproducto")
                        or f"Producto {p.get('catalogo_productoid')}"
                    ),
                )
                for p in productos
                if p.get("catalogo_productoid") is not None
            ],
            familias=to_items(familias, "producto_familiaid", "nombre"),
        )

    # -----------------------------
    # Reglas
    # -----------------------------
    def listar_reglas(
        self,
        *,
        clienteid: Optional[int],
        grupoid: Optional[int],
        productoid: Optional[int],
        familiaid: Optional[int],
        tarifaid: Optional[int],
        incluir_deshabilitadas: bool,
    ) -> TarifaReglaListResponse:
        rows = self.repo.list_reglas()

        def _regla_producto_id(r: dict) -> Optional[int]:
            return r.get("productoid") or r.get("catalogo_productoid") or r.get("catalogo_productoid_viejo")

        # Filtro cliente/grupo manteniendo reglas genericas (None) para ese ambito
        if clienteid:
            rows = [r for r in rows if r.get("clienteid") in (None, clienteid)]
        if grupoid:
            rows = [r for r in rows if r.get("idgrupo") in (None, grupoid)]

        # Filtro producto/familia respetando el comportamiento previo
        fam_ctx = familiaid
        if productoid and not familiaid:
            fam_ctx = self.repo.producto_familia(productoid)

        if productoid:
            rows = [
                r
                for r in rows
                if (
                    _regla_producto_id(r) == productoid
                    or r.get("familia_productoid") == fam_ctx
                )
            ]
        elif fam_ctx:
            rows = [r for r in rows if r.get("familia_productoid") == fam_ctx]

        if tarifaid:
            rows = [r for r in rows if r.get("tarifaid") == tarifaid]

        if not incluir_deshabilitadas:
            rows = [r for r in rows if r.get("habilitada") is True]

        out = [
            TarifaReglaOut(
                tarifa_reglaid=r.get("tarifa_reglaid"),
                tarifaid=r.get("tarifaid"),
                clienteid=r.get("clienteid"),
                grupoid=r.get("idgrupo") or r.get("grupoid"),
                idgrupo=r.get("idgrupo"),
                productoid=_regla_producto_id(r),
                catalogo_productoid=_regla_producto_id(r),
                familia_productoid=r.get("familia_productoid"),
                producto_tipoid=r.get("producto_tipoid"),
                tarifa_regla_tipoid=r.get("tarifa_regla_tipoid"),
                fecha_inicio=r.get("fecha_inicio"),
                fecha_fin=r.get("fecha_fin"),
                prioridad=r.get("prioridad"),
                habilitada=bool(r.get("habilitada", True)),
            )
            for r in rows
        ]

        return TarifaReglaListResponse(data=out, total=len(out))

    def crear_regla(self, data: TarifaReglaCreate) -> TarifaReglaOut:
        payload = data.dict(exclude_none=True)
        if payload.get("grupoid") and not payload.get("idgrupo"):
            payload["idgrupo"] = payload.get("grupoid")
        if payload.get("productoid") and not payload.get("catalogo_productoid"):
            payload["catalogo_productoid"] = payload.get("productoid")

        if not payload.get("tarifa_regla_tipoid"):
            codigo = None
            if payload.get("clienteid") and payload.get("catalogo_productoid"):
                codigo = "CP"
            elif payload.get("clienteid") and payload.get("familia_productoid"):
                codigo = "CF"
            elif payload.get("idgrupo") and payload.get("catalogo_productoid"):
                codigo = "GP"
            elif payload.get("idgrupo") and payload.get("familia_productoid"):
                codigo = "GF"
            elif not any(
                payload.get(k) for k in ("clienteid", "idgrupo", "catalogo_productoid", "familia_productoid")
            ):
                codigo = "GEN"
            if codigo:
                tipo_id = self.repo.get_tarifa_regla_tipo_id(codigo)
                if tipo_id:
                    payload["tarifa_regla_tipoid"] = tipo_id

        created = self.repo.insert_regla(payload)
        return TarifaReglaOut(**created)

    def actualizar_regla(self, reglaid: int, data: TarifaReglaUpdate) -> TarifaReglaOut:
        payload = {k: v for k, v in data.dict(exclude_none=True).items()}
        updated = self.repo.update_regla(reglaid, payload)
        if not updated:
            raise ValueError("Regla no encontrada")
        return TarifaReglaOut(**updated)

    def borrar_regla(self, reglaid: int):
        self.repo.delete_regla(reglaid)

    # -----------------------------
    # cliente_tarifa (general)
    # -----------------------------
    def asignar_cliente_tarifa(self, data: ClienteTarifaCreate) -> dict:
        payload = data.dict(exclude_none=True)
        return self.repo.insert_cliente_tarifa(payload)

    # -----------------------------
    # Calculo de precio (motor centralizado)
    # -----------------------------
    def calcular_precio(self, req: PrecioRequest) -> PrecioResponse:
        res = calcular_precio_linea(
            supabase=self.repo.supabase,
            clienteid=req.clienteid,
            productoid=req.productoid,
            precio_base_unit=req.precio_base_unit,
            cantidad=req.cantidad,
            fecha=req.fecha,
        )
        return PrecioResponse(**res)
