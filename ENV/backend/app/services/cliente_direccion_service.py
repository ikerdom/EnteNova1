# backend/app/services/cliente_direccion_service.py
import time


class ClienteDireccionService:
    def __init__(self, supabase):
        self.supabase = supabase

    def listar(self, clienteid: int):
        return (
            self.supabase.table("clientes_direccion")
            .select("*")
            .eq("idtercero", clienteid)
            .order("clientes_direccionid", desc=True)
            .execute()
            .data
            or []
        )

    def crear(self, clienteid: int, data: dict):
        data["idtercero"] = clienteid
        if not data.get("direccion_origen_id"):
            data["direccion_origen_id"] = int(time.time() * 1000)
        self.supabase.table("clientes_direccion").insert(data).execute()

    def actualizar(self, clienteid: int, direccionid: int, data: dict):
        self.supabase.table("clientes_direccion").update(data).eq(
            "clientes_direccionid", direccionid
        ).execute()

    def borrar(self, direccionid: int):
        self.supabase.table("clientes_direccion").delete().eq(
            "clientes_direccionid", direccionid
        ).execute()
