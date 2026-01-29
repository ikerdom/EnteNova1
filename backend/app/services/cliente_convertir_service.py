# backend/app/services/cliente_convertir_service.py
class ClienteConvertirService:
    def __init__(self, supabase):
        self.supabase = supabase

    def _perfil_esta_completo(self, clienteid: int) -> bool:
        """
        Regla CENTRAL:
        define si un potencial puede convertirse.
        """
        # Cliente base
        cli = (
            self.supabase.table("cliente")
            .select("clienteid, razonsocial, nombre, cifdni, domicilio, municipio, codigopostal")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )

        if not cli:
            return False

        nombre = cli.get("razonsocial") or cli.get("nombre")
        if not nombre or not cli.get("cifdni"):
            return False

        # Dirección fiscal
        direccion = (
            self.supabase.table("clientes_direccion")
            .select("direccion, municipio, codigopostal")
            .eq("idtercero", clienteid)
            .limit(1)
            .execute()
            .data
        )

        if direccion:
            row = direccion[0]
            if row.get("direccion") and row.get("municipio") and row.get("codigopostal"):
                return True

        if not (cli.get("domicilio") and cli.get("municipio") and cli.get("codigopostal")):
            return False

        return True

    def convertir(self, clienteid: int):
        cli = (
            self.supabase.table("cliente")
            .select("clienteid, tipo_cliente")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )

        if not cli:
            raise ValueError("Cliente potencial no encontrado")

        if cli.get("tipo_cliente") != "potencial":
            raise ValueError("El cliente no es potencial")

        if not self._perfil_esta_completo(clienteid):
            raise ValueError("El perfil no está completo. No se puede convertir.")

        self.supabase.table("cliente").update(
            {
                "tipo_cliente": "cliente",
                "perfil_completo": True,
            }
        ).eq("clienteid", clienteid).execute()

        return {
            "clienteid": clienteid,
            "tipo_cliente": "cliente",
            "perfil_completo": True,
            "mensaje": "Cliente potencial convertido correctamente",
        }
