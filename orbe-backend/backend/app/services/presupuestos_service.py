# backend/app/services/presupuestos_service.py
import math
from datetime import date, datetime
from typing import Dict, List, Optional

from backend.app.services.precio_engine import calcular_precio_linea

from backend.app.schemas.presupuesto import (
    PresupuestoCreateIn,
    PresupuestoListItem,
    PresupuestoListResponse,
    PresupuestoOut,
    PresupuestoLineaIn,
    PresupuestoLineaOut,
    PresupuestoRecalcResponse,
)
from backend.app.repositories.presupuestos_repo import PresupuestosRepository


class PresupuestosService:
    def __init__(self, repo: PresupuestosRepository):
        self.repo = repo

    # -----------------------------
    # Listado / detalle
    # -----------------------------
    def listar(
        self,
        q: Optional[str],
        estadoid: Optional[int],
        clienteid: Optional[int],
        ambito_impuesto: Optional[str],
        page: int,
        page_size: int,
        ordenar_por: str,
    ) -> PresupuestoListResponse:
        rows, total = self.repo.listar(q, estadoid, clienteid, ambito_impuesto, page, page_size, ordenar_por)

        ids = [
            r.get("presupuestoid") or r.get("presupuesto_id")
            for r in rows
            if (r.get("presupuestoid") or r.get("presupuesto_id")) is not None
        ]
        totales_map = self.repo.obtener_totales([int(i) for i in ids]) if ids else {}
        num_lineas_map = {int(pid): self.repo.contar_lineas(int(pid)) for pid in ids}

        items: List[PresupuestoListItem] = [
            PresupuestoListItem(
                presupuestoid=r.get("presupuestoid") or r.get("presupuesto_id"),
                numero=r.get("numero"),
                clienteid=r.get("clienteid"),
                cliente=(r.get("cliente") or {}).get("razonsocial")
                or (r.get("cliente") or {}).get("nombre"),
                estado_presupuestoid=r.get("estado_presupuestoid") or r.get("presupuesto_estadoid"),
                estado=(r.get("estado") or {}).get("estado") or (r.get("estado") or {}).get("nombre"),
                bloquea_edicion=(r.get("estado") or {}).get("bloquea_edicion"),
                fecha_presupuesto=r.get("fecha_presupuesto"),
                fecha_validez=r.get("fecha_validez"),
                ambito_impuesto=r.get("ambito_impuesto"),
                num_lineas=r.get("num_lineas")
                or num_lineas_map.get(int(r.get("presupuestoid") or r.get("presupuesto_id") or 0)),
                base_imponible=r.get("base_imponible")
                or (totales_map.get(int(r.get("presupuestoid") or r.get("presupuesto_id") or 0)) or {}).get("base_imponible"),
                iva_total=r.get("iva_total")
                or (totales_map.get(int(r.get("presupuestoid") or r.get("presupuesto_id") or 0)) or {}).get("iva_total"),
                total_documento=r.get("total_documento")
                or (totales_map.get(int(r.get("presupuestoid") or r.get("presupuesto_id") or 0)) or {}).get("total_documento"),
                total_estimada=r.get("total_estimada"),
                trabajadorid=r.get("trabajadorid"),
            )
            for r in rows
        ]

        total_pages = max(1, math.ceil((total or 0) / page_size))
        return PresupuestoListResponse(
            data=items,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    def obtener(self, presupuestoid: int) -> PresupuestoOut:
        pres = self.repo.obtener(presupuestoid)
        if not pres:
            raise ValueError("Presupuesto no encontrado")
        totales = self.repo.obtener_totales([presupuestoid]).get(presupuestoid, {})
        if pres.get("presupuestoid") is None and pres.get("presupuesto_id") is not None:
            pres["presupuestoid"] = pres.get("presupuesto_id")
        pres["base_imponible"] = pres.get("base_imponible") or totales.get("base_imponible")
        pres["iva_total"] = pres.get("iva_total") or totales.get("iva_total")
        pres["total_documento"] = pres.get("total_documento") or totales.get("total_documento")
        pres["estado"] = (pres.get("estado") or {}).get("estado") or (pres.get("estado") or {}).get("nombre")
        pres["bloquea_edicion"] = (pres.get("estado") or {}).get("bloquea_edicion")
        return PresupuestoOut(**pres)

    # -----------------------------
    # Crear / actualizar / borrar
    # -----------------------------
    def crear(self, data: PresupuestoCreateIn) -> PresupuestoOut:
        payload = data.dict(exclude_none=True)

        # Número automático si no viene (PRES-YYYY-####)
        if not payload.get("numero"):
            prefijo = f"PRES-{data.fecha_presupuesto.year}-"
            existentes = self.repo.ultimo_numero_prefijo(prefijo)
            usados = [
                int(x.split("-")[-1])
                for x in existentes
                if x.split("-")[-1].isdigit()
            ]
            siguiente = max(usados) + 1 if usados else 1
            payload["numero"] = f"{prefijo}{siguiente:04d}"

        # Region (prioridad: direccion_envio -> cliente envio/fiscal)
        regionid = self.repo.region_desde_direccion(payload.get("direccion_envioid"))
        if not regionid:
            regionid = self.repo.region_preferente_cliente(payload["clienteid"])
        if regionid:
            payload["regionid"] = regionid

        # Estado por defecto: Borrador si existe
        if not payload.get("estado_presupuestoid"):
            eid = self.repo.estado_por_nombre("Borrador")
            if eid:
                payload["estado_presupuestoid"] = eid

        payload.setdefault("editable", True)
        payload.setdefault("total_estimada", 0.0)
        created = self.repo.crear(payload)
        if not created:
            raise RuntimeError("No se pudo crear el presupuesto")
        return PresupuestoOut(**created)

    def actualizar(self, presupuestoid: int, data: Dict) -> PresupuestoOut:
        pres = self.repo.obtener(presupuestoid)
        if not pres:
            raise ValueError("Presupuesto no encontrado")

        if pres.get("editable") is False:
            raise ValueError("Este presupuesto está bloqueado y no se puede editar")

        # Si llega direccion_envioid, recalculamos region
        payload = {k: v for k, v in data.items() if v is not None}
        if "direccion_envioid" in payload:
            regionid = self.repo.region_desde_direccion(payload["direccion_envioid"])
            if regionid:
                payload["regionid"] = regionid

        self.repo.actualizar(presupuestoid, payload)
        nuevo = self.repo.obtener(presupuestoid)
        return PresupuestoOut(**nuevo)

    def borrar(self, presupuestoid: int):
        self.repo.borrar_lineas(presupuestoid)
        self.repo.borrar(presupuestoid)

    # -----------------------------
    # Líneas
    # -----------------------------
    def listar_lineas(self, presupuestoid: int) -> List[PresupuestoLineaOut]:
        raw = self.repo.listar_lineas(presupuestoid)
        out = []
        for r in raw:
            base_linea = r.get("base_linea")
            if base_linea is None:
                base_linea = r.get("importe_base")
            iva_pct = r.get("iva_pct") or 0.0
            iva_importe = r.get("iva_importe")
            if iva_importe is None and base_linea is not None:
                iva_importe = float(base_linea) * float(iva_pct) / 100.0
            total_linea = r.get("total_linea") or r.get("importe_total_linea")

            out.append(
                PresupuestoLineaOut(
                    presupuesto_detalleid=r.get("presupuesto_detalleid") or r.get("presupuesto_linea_id"),
                    productoid=r.get("productoid") or r.get("producto_id"),
                    descripcion=r.get("descripcion"),
                    cantidad=r.get("cantidad"),
                    precio_unitario=r.get("precio_unitario"),
                    descuento_pct=r.get("descuento_pct"),
                    iva_pct=r.get("iva_pct"),
                    importe_base=r.get("importe_base"),
                    importe_total_linea=r.get("importe_total_linea"),
                    base_linea=base_linea,
                    iva_importe=iva_importe,
                    total_linea=total_linea,
                    tarifa_aplicada=r.get("tarifa_aplicada"),
                    nivel_tarifa=r.get("nivel_tarifa"),
                    iva_origen=r.get("iva_origen"),
                )
            )
        return out

    def agregar_linea(self, presupuestoid: int, linea: PresupuestoLineaIn) -> int:
        pres = self.repo.obtener(presupuestoid)
        if not pres:
            raise ValueError("Presupuesto no encontrado")
        if pres.get("editable") is False:
            raise ValueError("Presupuesto bloqueado")

        clienteid = pres.get("clienteid")
        fecha_validez = pres.get("fecha_validez")
        fecha_calc = (
            date.fromisoformat(fecha_validez) if isinstance(fecha_validez, str) else fecha_validez
        ) or datetime.now().date()

        pricing = calcular_precio_linea(
            supabase=self.repo.supabase,
            clienteid=clienteid,
            productoid=linea.productoid,
            cantidad=linea.cantidad,
            fecha=fecha_calc,
        )

        unit_bruto = float(pricing.get("unit_bruto") or 0.0)
        dto_motor = float(pricing.get("descuento_pct") or 0.0)
        iva_pct = float(pricing.get("iva_pct") or 0.0)
        dto_final = float(linea.descuento_pct) if linea.descuento_pct is not None else dto_motor

        base = float(pricing.get("subtotal_sin_iva") or 0.0)
        total = float(pricing.get("total_con_iva") or 0.0)

        # Si hay dto manual, recalculamos base/total respetando IVA
        if linea.descuento_pct is not None:
            base = round(float(linea.cantidad) * unit_bruto * (1 - dto_final / 100.0), 2)
            total = round(base * (1 + iva_pct / 100.0), 2)

        row = {
            "presupuesto_id": presupuestoid,
            "producto_id": linea.productoid,
            "descripcion": linea.descripcion,
            "cantidad": float(linea.cantidad),
            "precio_unitario": unit_bruto,
            "descuento_pct": dto_final,
            "iva_pct": iva_pct,
            "base_linea": base,
            "iva_importe": round(base * iva_pct / 100.0, 2),
            "total_linea": total,
            "tarifa_aplicada": pricing.get("tarifa_aplicada"),
            "nivel_tarifa": pricing.get("nivel_tarifa"),
        }
        detalleid = self.repo.insertar_linea(row)
        self._recalcular_total_estimada(presupuestoid)
        return detalleid

    def recalcular_lineas(self, presupuestoid: int, fecha_calculo: Optional[date] = None) -> PresupuestoRecalcResponse:
        pres = self.repo.obtener(presupuestoid)
        if not pres:
            raise ValueError("Presupuesto no encontrado")

        lineas = self.repo.listar_lineas(presupuestoid)
        if not lineas:
            raise ValueError("No hay líneas en el presupuesto")

        clienteid = pres.get("clienteid")
        fecha_base = fecha_calculo or pres.get("fecha_validez") or pres.get("fecha_presupuesto")
        if isinstance(fecha_base, str):
            try:
                fecha_base = date.fromisoformat(fecha_base)
            except Exception:
                fecha_base = datetime.now().date()

        total_base = total_iva = total_total = 0.0

        for ln in lineas:
            pricing = calcular_precio_linea(
                supabase=self.repo.supabase,
                clienteid=clienteid,
                productoid=ln.productoid,
                cantidad=ln.cantidad or 1,
                fecha=fecha_base,
            )

            base = float(pricing["subtotal_sin_iva"])
            iva = float(pricing["iva_importe"])
            total = float(pricing["total_con_iva"])

            self.repo.actualizar_linea(
                ln.presupuesto_detalleid,
                {
                    "precio_unitario": pricing["unit_bruto"],
                    "descuento_pct": pricing["descuento_pct"],
                    "iva_pct": pricing["iva_pct"],
                    "importe_base": base,
                    "importe_total_linea": total,
                    "tarifa_aplicada": pricing.get("tarifa_aplicada"),
                    "nivel_tarifa": pricing.get("nivel_tarifa"),
                    "iva_origen": pricing.get("iva_origen"),
                },
            )

            total_base += base
            total_iva += iva
            total_total += total

        recalc_row = {
            "presupuestoid": presupuestoid,
            "base_imponible": round(total_base, 2),
            "iva_total": round(total_iva, 2),
            "total_presupuesto": round(total_total, 2),
            "fecha_recalculo": datetime.now().isoformat(),
        }
        self.repo.upsert_totales(recalc_row)
        self.repo.actualizar(presupuestoid, {"total_estimada": round(total_total, 2)})

        return PresupuestoRecalcResponse(**recalc_row)

    # -----------------------------
    # Conversión a pedido
    # -----------------------------
    def convertir_a_pedido(self, presupuestoid: int) -> Dict[str, object]:
        pres = self.repo.obtener(presupuestoid)
        if not pres:
            raise ValueError("Presupuesto no encontrado")

        existing = self.repo.pedido_por_presupuesto(presupuestoid)
        if existing:
            return {"pedidoid": existing["pedidoid"], "numero": existing["numero"], "ya_existia": True}

        hoy = datetime.now().date()
        numero_pedido = f"PED-{hoy.year}-{9000 + presupuestoid:04d}"

        pedido_row = {
            "numero": numero_pedido,
            "clienteid": pres.get("clienteid"),
            "trabajadorid": pres.get("trabajadorid"),
            "fecha_pedido": hoy.isoformat(),
            "estado_pedidoid": 1,  # Borrador
            "presupuesto_origenid": presupuestoid,
            "tipo_pedidoid": 1,
            "procedencia_pedidoid": 2,
        }
        pedido = self.repo.crear_pedido(pedido_row)
        if not pedido:
            raise RuntimeError("No se pudo crear el pedido")

        lineas = self.repo.listar_lineas(presupuestoid)
        for ln in lineas:
            self.repo.insertar_linea_pedido(
                {
                    "pedidoid": pedido["pedidoid"],
                    "productoid": ln.productoid,
                    "nombre_producto": ln.descripcion,
                    "cantidad": ln.cantidad,
                    "precio_unitario": ln.precio_unitario,
                    "descuento_pct": ln.descuento_pct or 0,
                    "iva_pct": ln.iva_pct or 21,
                    "importe_base": ln.importe_base or 0,
                    "importe_total_linea": ln.importe_total_linea or 0,
                }
            )

        estado_convertido = self.repo.estado_por_nombre("Convertido") or self.repo.estado_por_nombre("Aceptado") or pres.get("estado_presupuestoid")
        if estado_convertido:
            self.repo.marcar_presupuesto_estado(presupuestoid, estado_convertido, editable=False)

        return {
            "pedidoid": pedido["pedidoid"],
            "numero": pedido["numero"],
            "ya_existia": False,
        }

    # -----------------------------
    # Internos
    # -----------------------------
    def _recalcular_total_estimada(self, presupuestoid: int):
        lineas = self.repo.listar_lineas(presupuestoid)
        total = sum(float(l.importe_total_linea or 0) for l in lineas)
        self.repo.actualizar(presupuestoid, {"total_estimada": round(total, 2)})

    # Expuesto para UI (datos básicos de cliente)
    def cliente_basico(self, clienteid: int) -> Optional[dict]:
        try:
            return self.repo.cliente_basico(clienteid)
        except Exception:
            return None
