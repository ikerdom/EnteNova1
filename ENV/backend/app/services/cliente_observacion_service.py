# backend/app/services/cliente_observacion_service.py
from datetime import datetime
from backend.app.schemas.cliente_observacion import (
    ClienteObservacionIn,
    TIPOS_OBSERVACION,
)


class ClienteObservacionService:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listar observaciones
    # -----------------------------
    def listar(self, clienteid: int):
        try:
            return (
                self.supabase.table("cliente_observacion")
                .select(
                    "cliente_observacionid, clienteid, tipo, comentario, usuario, fecha"
                )
                .eq("clienteid", clienteid)
                .order("fecha", desc=True)
                .execute()
                .data
                or []
            )
        except Exception:
            # fallback si la tabla aún no existe
            return []

    # -----------------------------
    # Crear observación
    # -----------------------------
    def crear(self, clienteid: int, data: ClienteObservacionIn):
        self._validar(data)

        row = {
            "clienteid": clienteid,
            "tipo": data.tipo,
            "comentario": data.comentario.strip(),
            "usuario": data.usuario,
            "fecha": datetime.utcnow().isoformat(),
        }

        self.supabase.table("cliente_observacion").insert(row).execute()

    # -----------------------------
    # Validaciones centrales
    # -----------------------------
    def _validar(self, data: ClienteObservacionIn):
        if not data.comentario or not data.comentario.strip():
            raise ValueError("El comentario es obligatorio")

        if data.tipo not in TIPOS_OBSERVACION:
            raise ValueError("Tipo de observación no válido")
