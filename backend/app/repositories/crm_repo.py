# backend/app/repositories/crm_repo.py
from typing import List, Optional


class CrmRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def listar(self, filtros: dict) -> List[dict]:
        q = self.supabase.table("crm_actuacion").select(
            "crm_actuacionid,titulo,descripcion,observaciones,fecha_accion,fecha_vencimiento,"
            "requiere_seguimiento,fecha_recordatorio,clienteid,trabajador_creadorid,"
            "trabajador_asignadoid,crm_actuacion_estadoid,crm_actuacion_tipoid,"
            "crm_actuacion_estado(estado),crm_actuacion_tipo(tipo)"
        )
        if filtros.get("trabajador_asignadoid"):
            q = q.eq("trabajador_asignadoid", filtros["trabajador_asignadoid"])
        if filtros.get("clienteid"):
            q = q.eq("clienteid", filtros["clienteid"])
        if filtros.get("crm_actuacion_estadoid"):
            q = q.eq("crm_actuacion_estadoid", filtros["crm_actuacion_estadoid"])
        if filtros.get("crm_actuacion_tipoid"):
            q = q.eq("crm_actuacion_tipoid", filtros["crm_actuacion_tipoid"])
        q = q.order("fecha_vencimiento", desc=False)
        res = q.execute()
        rows = res.data or []
        if filtros.get("buscar"):
            s = filtros["buscar"].lower()
            rows = [r for r in rows if s in (r.get("titulo") or "").lower()]
        for r in rows:
            r["estado"] = (r.get("crm_actuacion_estado") or {}).get("estado")
            r["tipo"] = (r.get("crm_actuacion_tipo") or {}).get("tipo")
        return rows

    def crear(self, data: dict) -> dict:
        res = self.supabase.table("crm_actuacion").insert(data).execute()
        return (res.data or [None])[0]

    def actualizar(self, accionid: int, data: dict) -> dict:
        self.supabase.table("crm_actuacion").update(data).eq("crm_actuacionid", accionid).execute()
        res = (
            self.supabase.table("crm_actuacion")
            .select("*")
            .eq("crm_actuacionid", accionid)
            .maybe_single()
            .execute()
        )
        return res.data or {}

    def obtener(self, accionid: int) -> Optional[dict]:
        res = (
            self.supabase.table("crm_actuacion")
            .select("*")
            .eq("crm_actuacionid", accionid)
            .maybe_single()
            .execute()
        )
        return res.data or None
