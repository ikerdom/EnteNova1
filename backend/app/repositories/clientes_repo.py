# backend/app/repositories/clientes_repo.py
from typing import Optional, Tuple, List
from backend.app.schemas.cliente import ClienteOut


class ClientesRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def get_clientes(
        self,
        q: Optional[str],
        tipo: Optional[str],
        idgrupo: Optional[int],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> Tuple[List[dict], int]:
        """
        Devuelve (clientes, total)
        """

        query = self.supabase.table("cliente").select(
            "clienteid, codigocuenta, codigoclienteoproveedor, clienteoproveedor, "
            "razonsocial, nombre, cifdni, cif_normalizado, viapublica, domicilio, "
            "codigopostal, provincia, municipio, telefono, telefono2, telefono3, fax, "
            "iban, codigobanco, codigoagencia, dc, ccc, codigotipoefecto, "
            "codigocuentaefecto, codigocuentaimpagado, remesahabitual, idgrupo",
            count="exact",
        )

        if q:
            safe_q = q.replace(",", " ")
            query = query.or_(
                "razonsocial.ilike.%{0}%,nombre.ilike.%{0}%,cifdni.ilike.%{0}%,"
                "codigocuenta.ilike.%{0}%,codigoclienteoproveedor.ilike.%{0}%".format(safe_q)
            )

        if tipo:
            query = query.eq("clienteoproveedor", tipo)

        if idgrupo:
            query = query.eq("idgrupo", idgrupo)

        # Orden
        allowed_sort = {
            "clienteid",
            "razonsocial",
            "nombre",
            "cifdni",
            "codigocuenta",
            "codigoclienteoproveedor",
        }
        sort_field = sort_field if sort_field in allowed_sort else "razonsocial"
        ascending = sort_dir.upper() == "ASC"
        query = query.order(sort_field, desc=not ascending)

        # Paginación
        start = (page - 1) * page_size
        end = start + page_size - 1

        res = query.range(start, end).execute()

        data = res.data or []
        total = res.count or 0

        return data, total

    def get_cliente_detalle(self, clienteid: int) -> dict:
        base = (
            self.supabase.table("cliente")
            .select(
                "clienteid, codigocuenta, codigoclienteoproveedor, clienteoproveedor, "
                "razonsocial, nombre, cifdni, cif_normalizado, viapublica, domicilio, "
                "codigopostal, provincia, municipio, telefono, telefono2, telefono3, fax, "
                "iban, codigobanco, codigoagencia, dc, ccc, codigotipoefecto, "
                "codigocuentaefecto, codigocuentaimpagado, remesahabitual, idgrupo"
            )
            .eq("clienteid", clienteid)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not base:
            return {}

        cliente = base[0]

        direcciones = (
            self.supabase.table("clientes_direccion")
            .select(
                "clientes_direccionid, direccion_origen_id, idtercero, razonsocial, "
                "nombrecomercial, direccionfiscal, direccion, idpais, idprovincia, "
                "idmunicipio, codigopostal, rci_estado, rci_poblacion, rci_idterritorio, "
                "municipio, cif, referenciacliente, created_at, updated_at"
            )
            .eq("idtercero", clienteid)
            .order("clientes_direccionid", desc=True)
            .execute()
            .data
            or []
        )
        contactos = (
            self.supabase.table("cliente_contacto")
            .select("cliente_contactoid, clienteid, tipo, valor, valor_norm, principal")
            .eq("clienteid", clienteid)
            .order("principal", desc=True)
            .order("tipo")
            .execute()
            .data
            or []
        )

        return {
            "cliente": cliente,
            "direcciones": direcciones,
            "contactos": contactos,
            "contacto_principal": next((c for c in contactos if c.get("principal")), None),
        }

    def update_cliente(self, clienteid: int, data: dict) -> bool:
        if not data:
            return False
        self.supabase.table("cliente").update(data).eq("clienteid", clienteid).execute()
        return True
