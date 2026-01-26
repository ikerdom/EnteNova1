from postgrest.exceptions import APIError
# backend/app/repositories/presupuestos_repo.py
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


class PresupuestosRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def _select_presupuesto_fields(self) -> str:
        return (
            "presupuesto_id,numero,clienteid,presupuesto_estadoid,fecha_presupuesto,"
            "fecha_validez,total_estimada,trabajadorid,editable,ambito_impuesto,"
            "cliente:cliente(razonsocial,nombre),"
            "estado:presupuesto_estado(estado,bloquea_edicion)"
        )

    # -----------------------------
    # Listado paginado
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
    ) -> Tuple[List[dict], int]:
        query = self.supabase.table("presupuesto").select(self._select_presupuesto_fields(), count="exact")

        if q:
            query = query.or_(f"numero.ilike.%{q}%,referencia_cliente.ilike.%{q}%")

        if estadoid:
            query = query.eq("presupuesto_estadoid", estadoid)

        if clienteid:
            query = query.eq("clienteid", clienteid)

        if ambito_impuesto:
            query = query.eq("ambito_impuesto", ambito_impuesto)

        if ordenar_por == "fecha_presupuesto":
            query = query.order("fecha_presupuesto", desc=True)
        else:
            query = query.order("created_at", desc=True)

        start = (page - 1) * page_size
        end = start + page_size - 1
        try:
            res = query.range(start, end).execute()
            return res.data or [], res.count or 0
        except APIError as e:
            if getattr(e, "args", None) and isinstance(e.args[0], dict) and e.args[0].get("code") == "PGRST205":
                return [], 0
            raise

    # -----------------------------
    # Cabecera
    # -----------------------------
    def obtener(self, presupuestoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("presupuesto")
            .select(self._select_presupuesto_fields())
            .eq("presupuesto_id", presupuestoid)
            .maybe_single()
            .execute()
        )
        return res.data or None

    def crear(self, data: dict) -> dict:
        res = self.supabase.table("presupuesto").insert(data).execute()
        return (res.data or [None])[0]

    def actualizar(self, presupuestoid: int, data: dict):
        self.supabase.table("presupuesto").update(data).eq("presupuesto_id", presupuestoid).execute()

    def borrar(self, presupuestoid: int):
        self.supabase.table("presupuesto").delete().eq("presupuesto_id", presupuestoid).execute()

    # -----------------------------
    # LÍneas
    # -----------------------------
    def listar_lineas(self, presupuestoid: int) -> List[dict]:
        res = (
            self.supabase.table("presupuesto_linea")
            .select(
                "presupuesto_linea_id, producto_id, descripcion, cantidad, precio_unitario, "
                "descuento_pct, iva_pct, base_linea, iva_importe, total_linea, "
                "tarifa_aplicada, nivel_tarifa"
            )
            .eq("presupuesto_id", presupuestoid)
            .order("presupuesto_linea_id", desc=False)
            .execute()
        )
        return res.data or []
    def insertar_linea(self, data: dict) -> int:
        res = self.supabase.table("presupuesto_linea").insert(data).execute()
        return res.data[0]["presupuesto_linea_id"]

    def actualizar_linea(self, detalleid: int, data: dict):
        self.supabase.table("presupuesto_linea").update(data).eq("presupuesto_linea_id", detalleid).execute()

    def borrar_lineas(self, presupuestoid: int):
        self.supabase.table("presupuesto_linea").delete().eq("presupuesto_id", presupuestoid).execute()

    def upsert_totales(self, data: dict):
        self.supabase.table("presupuesto_totales").upsert(data).execute()

    def obtener_totales(self, presupuesto_ids: List[int]) -> Dict[int, dict]:
        if not presupuesto_ids:
            return {}

        def _fetch(id_col: str) -> Dict[int, dict]:
            res = (
                self.supabase.table("presupuesto_totales")
                .select(f"{id_col},base_imponible,iva_total,total_documento")
                .in_(id_col, presupuesto_ids)
                .execute()
            )
            rows = res.data or []
            out = {}
            for r in rows:
                pid = r.get(id_col)
                if pid is not None:
                    out[int(pid)] = r
            return out

        try:
            return _fetch("presupuesto_id")
        except APIError as e:
            if getattr(e, "args", None) and isinstance(e.args[0], dict) and e.args[0].get("code") == "PGRST204":
                return _fetch("presupuestoid")
            raise

    def contar_lineas(self, presupuestoid: int) -> int:
        for table, id_col in [("presupuesto_linea", "presupuesto_id"), ("presupuesto_detalle", "presupuestoid")]:
            try:
                res = (
                    self.supabase.table(table)
                    .select(id_col, count="exact")
                    .eq(id_col, presupuestoid)
                    .execute()
                )
                return res.count or 0
            except APIError as e:
                if getattr(e, "args", None) and isinstance(e.args[0], dict) and e.args[0].get("code") in ("PGRST204", "PGRST205"):
                    continue
                raise
        return 0

    # -----------------------------
    # Apoyos
    # -----------------------------
    def estado_por_nombre(self, nombre: str) -> Optional[int]:
        try:
            res = (
                self.supabase.table("presupuesto_estado")
                .select("presupuesto_estadoid, estado")
                .ilike("estado", nombre)
                .maybe_single()
                .execute()
            )
        except APIError as e:
            if getattr(e, "args", None) and isinstance(e.args[0], dict) and e.args[0].get("code") == "PGRST205":
                return None
            raise
        d = res.data or None
        return d.get("presupuesto_estadoid") if d else None

    def region_desde_direccion(self, direccionid: Optional[int]) -> Optional[int]:
        if not direccionid:
            return None
        res = (
            self.supabase.table("clientes_direccion")
            .select("regionid, rci_idterritorio, idprovincia")
            .eq("clientes_direccionid", direccionid)
            .maybe_single()
            .execute()
        )
        d = res.data or None
        if not d:
            return None
        regionid = d.get("regionid") or d.get("rci_idterritorio") or d.get("idprovincia")
        return regionid if isinstance(regionid, int) else None

    def region_preferente_cliente(self, clienteid: int) -> Optional[int]:
        # 1) envio, 2) fiscal
        try:
            envio = (
                self.supabase.table("clientes_direccion")
                .select("regionid, rci_idterritorio, idprovincia")
                .eq("idtercero", clienteid)
                .limit(1)
                .execute()
                .data
            )
            if envio and envio[0].get("regionid"):
                regionid = envio[0].get("regionid") or envio[0].get("rci_idterritorio") or envio[0].get("idprovincia")
                return regionid if isinstance(regionid, int) else None
        except Exception:
            pass

        try:
            fiscal = (
                self.supabase.table("cliente")
                .select("idprovincia")
                .eq("clienteid", clienteid)
                .maybe_single()
                .execute()
                .data
            )
            if fiscal and fiscal.get("idprovincia"):
                return fiscal.get("idprovincia")
        except Exception:
            pass
        return None

    def ultimo_numero_prefijo(self, prefijo: str) -> List[str]:
        res = (
            self.supabase.table("presupuesto")
            .select("numero")
            .ilike("numero", f"{prefijo}%")
            .execute()
        )
        return [r.get("numero") for r in (res.data or []) if r.get("numero")]

    def pedido_por_presupuesto(self, presupuestoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("pedido")
            .select("pedidoid, numero, estado_pedidoid")
            .eq("presupuesto_origenid", presupuestoid)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def crear_pedido(self, data: dict) -> dict:
        res = self.supabase.table("pedido").insert(data).execute()
        return (res.data or [None])[0]

    def insertar_linea_pedido(self, data: dict):
        self.supabase.table("pedido_detalle").insert(data).execute()

    def marcar_presupuesto_estado(self, presupuestoid: int, estadoid: int, editable: Optional[bool] = None):
        update_data: Dict[str, object] = {"estado_presupuestoid": estadoid}
        if editable is not None:
            update_data["editable"] = editable
        self.supabase.table("presupuesto").update(update_data).eq("presupuestoid", presupuestoid).execute()

    def cliente_basico(self, clienteid: int) -> Optional[dict]:
        res = (
            self.supabase.table("cliente")
            .select("clienteid, razonsocial, nombre, cifdni, telefono, telefono2, telefono3")
            .eq("clienteid", clienteid)
            .maybe_single()
            .execute()
        )
        return res.data or None
