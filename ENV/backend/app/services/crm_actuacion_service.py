# backend/app/services/crm_actuacion_service.py
from backend.app.schemas.crm_actuacion import CrmActuacionIn


class CrmActuacionService:
    def __init__(self, supabase):
        self.supabase = supabase

    def listar(self, clienteid: int):
        return (
            self.supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, titulo, descripcion, observaciones, "
                "crm_actuacion_tipoid, crm_actuacion_estadoid, "
                "fecha_vencimiento, fecha_accion, requiere_seguimiento, fecha_recordatorio, "
                "trabajador_creadorid, trabajador_asignadoid"
            )
            .eq("clienteid", clienteid)
            .order("fecha_vencimiento")
            .execute()
            .data
            or []
        )

    def crear(self, clienteid: int, data: CrmActuacionIn):
        self._validar(data)
        row = data.model_dump(exclude_none=True)
        row["clienteid"] = clienteid
        self.supabase.table("crm_actuacion").insert(row).execute()

    def actualizar(self, crm_id: int, data: CrmActuacionIn):
        self._validar(data)
        self.supabase.table("crm_actuacion").update(
            data.model_dump(exclude_none=True)
        ).eq("crm_actuacionid", crm_id).execute()

    def _validar(self, data: CrmActuacionIn):
        if not data.titulo or not data.titulo.strip():
            raise ValueError("El titulo es obligatorio")
