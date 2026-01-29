# backend/app/services/cliente_contacto_service.py
from typing import Any, Dict, List


class ClienteContactoService:
    def __init__(self, supabase):
        self.supabase = supabase

    def listar(self, clienteid: int) -> List[Dict[str, Any]]:
        return (
            self.supabase.table("cliente_contacto")
            .select("cliente_contactoid, clienteid, tipo, valor, valor_norm, principal")
            .eq("clienteid", clienteid)
            .order("principal", desc=True)
            .order("tipo")
            .execute()
            .data
            or []
        )

    def crear(self, clienteid: int, data: dict) -> int:
        if not data.get("tipo") or not data.get("valor"):
            raise ValueError("Tipo y valor son obligatorios")

        row = {**data}
        row["clienteid"] = clienteid

        if row.get("principal") is True:
            self._desmarcar_principal(clienteid, row.get("tipo"))

        res = self.supabase.table("cliente_contacto").insert(row).execute()
        return res.data[0]["cliente_contactoid"]

    def actualizar(self, clienteid: int, contactoid: int, data: dict):
        if "tipo" in data and not data.get("tipo"):
            raise ValueError("Tipo es obligatorio")
        if "valor" in data and not data.get("valor"):
            raise ValueError("Valor es obligatorio")

        if data.get("principal") is True and data.get("tipo"):
            self._desmarcar_principal(clienteid, data.get("tipo"))

        self.supabase.table("cliente_contacto").update(data).eq(
            "cliente_contactoid", contactoid
        ).execute()

    def borrar(self, clienteid: int, contactoid: int):
        self.supabase.table("cliente_contacto").delete().eq(
            "cliente_contactoid", contactoid
        ).execute()

    def hacer_principal(self, clienteid: int, contactoid: int, tipo: str | None = None):
        if not tipo:
            row = (
                self.supabase.table("cliente_contacto")
                .select("tipo")
                .eq("cliente_contactoid", contactoid)
                .limit(1)
                .execute()
                .data
                or []
            )
            tipo = row[0].get("tipo") if row else None

        if not tipo:
            raise ValueError("No se pudo determinar el tipo del contacto")

        self._desmarcar_principal(clienteid, tipo)
        self.supabase.table("cliente_contacto").update(
            {"principal": True}
        ).eq("cliente_contactoid", contactoid).execute()

    def _desmarcar_principal(self, clienteid: int, tipo: str):
        self.supabase.table("cliente_contacto").update(
            {"principal": False}
        ).eq("clienteid", clienteid).eq("tipo", tipo).execute()
