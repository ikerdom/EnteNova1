# backend/app/repositories/tarifas_repo.py
from typing import List, Optional, Tuple, Dict


class TarifasRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Catálogos
    # -----------------------------
    def catalogo(self, table: str, id_field: str, label_field: str, where_enabled: bool = False, order_field: Optional[str] = None) -> List[dict]:
        q = self.supabase.table(table).select(f"{id_field}, {label_field}")
        if where_enabled:
            try:
                q = q.eq("habilitado", True)
            except Exception:
                pass
        if order_field:
            q = q.order(order_field)
        res = q.execute()
        return res.data or []

    # -----------------------------
    # Reglas
    # -----------------------------
    def list_reglas(self) -> List[dict]:
        res = (
            self.supabase.table("tarifa_regla")
            .select("*")
            .order("tarifa_reglaid")
            .execute()
        )
        return res.data or []

    def get_tarifa_regla_tipo_id(self, codigo: str) -> Optional[int]:
        if not codigo:
            return None
        res = (
            self.supabase.table("tarifa_regla_tipo")
            .select("tarifa_regla_tipoid")
            .eq("codigo", codigo)
            .maybe_single()
            .execute()
        )
        d = res.data or None
        return d.get("tarifa_regla_tipoid") if d else None

    def insert_regla(self, data: dict) -> dict:
        res = self.supabase.table("tarifa_regla").insert(data).execute()
        return (res.data or [None])[0]

    def update_regla(self, reglaid: int, data: dict) -> dict:
        self.supabase.table("tarifa_regla").update(data).eq("tarifa_reglaid", reglaid).execute()
        res = (
            self.supabase.table("tarifa_regla")
            .select("*")
            .eq("tarifa_reglaid", reglaid)
            .maybe_single()
            .execute()
        )
        return res.data or {}

    def delete_regla(self, reglaid: int):
        self.supabase.table("tarifa_regla").delete().eq("tarifa_reglaid", reglaid).execute()

    # -----------------------------
    # Cliente_tarifa
    # -----------------------------
    def insert_cliente_tarifa(self, data: dict) -> dict:
        res = self.supabase.table("cliente_tarifa").insert(data).execute()
        return (res.data or [None])[0]

    # -----------------------------
    # Helpers
    # -----------------------------
    def producto_familia(self, productoid: int) -> Optional[int]:
        res = (
            self.supabase.table("producto")
            .select("producto_familiaid")
            .eq("catalogo_productoid", productoid)
            .maybe_single()
            .execute()
        )
        d = res.data or None
        return d.get("producto_familiaid") if d else None
