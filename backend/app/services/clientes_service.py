# backend/app/services/clientes_service.py
import math
from typing import Optional

from backend.app.schemas.cliente import (
    ClienteListResponse,
    ClienteOut,
    ClienteDetalle,
    ClienteDireccion,
    ClienteContacto,
)
from backend.app.repositories.clientes_repo import ClientesRepository
from backend.app.schemas.cliente_create import ClienteCreateIn


class ClientesService:
    def __init__(self, repo: ClientesRepository):
        self.repo = repo

    def listar_clientes(
        self,
        q: Optional[str],
        tipo: Optional[str],
        idgrupo: Optional[int],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> ClienteListResponse:
        clientes_raw, total = self.repo.get_clientes(
            q=q,
            tipo=tipo,
            idgrupo=idgrupo,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )

        clientes: list[ClienteOut] = []

        for c in clientes_raw:
            data = dict(c) if isinstance(c, dict) else c.__dict__

            cliente = ClienteOut(
                clienteid=data.get("clienteid"),
                codigocuenta=data.get("codigocuenta"),
                codigoclienteoproveedor=data.get("codigoclienteoproveedor"),
                clienteoproveedor=data.get("clienteoproveedor"),
                razonsocial=data.get("razonsocial"),
                nombre=data.get("nombre"),
                cifdni=data.get("cifdni"),
                cif_normalizado=data.get("cif_normalizado"),
                viapublica=data.get("viapublica"),
                domicilio=data.get("domicilio"),
                codigopostal=data.get("codigopostal"),
                provincia=data.get("provincia"),
                municipio=data.get("municipio"),
                telefono=data.get("telefono"),
                telefono2=data.get("telefono2"),
                telefono3=data.get("telefono3"),
                fax=data.get("fax"),
                iban=data.get("iban"),
                codigobanco=data.get("codigobanco"),
                codigoagencia=data.get("codigoagencia"),
                dc=data.get("dc"),
                ccc=data.get("ccc"),
                codigotipoefecto=data.get("codigotipoefecto"),
                codigocuentaefecto=data.get("codigocuentaefecto"),
                codigocuentaimpagado=data.get("codigocuentaimpagado"),
                remesahabitual=data.get("remesahabitual"),
                idgrupo=data.get("idgrupo"),
            )

            clientes.append(cliente)

        total_pages = max(1, math.ceil(total / page_size))

        return ClienteListResponse(
            data=clientes,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    def obtener_detalle(self, clienteid: int) -> ClienteDetalle:
        raw = self.repo.get_cliente_detalle(clienteid)
        if not raw:
            raise ValueError("Cliente no encontrado")

        cli = raw.get("cliente", {})
        cliente = ClienteOut(
            clienteid=cli.get("clienteid"),
            codigocuenta=cli.get("codigocuenta"),
            codigoclienteoproveedor=cli.get("codigoclienteoproveedor"),
            clienteoproveedor=cli.get("clienteoproveedor"),
            razonsocial=cli.get("razonsocial"),
            nombre=cli.get("nombre"),
            cifdni=cli.get("cifdni"),
            cif_normalizado=cli.get("cif_normalizado"),
            viapublica=cli.get("viapublica"),
            domicilio=cli.get("domicilio"),
            codigopostal=cli.get("codigopostal"),
            provincia=cli.get("provincia"),
            municipio=cli.get("municipio"),
            telefono=cli.get("telefono"),
            telefono2=cli.get("telefono2"),
            telefono3=cli.get("telefono3"),
            fax=cli.get("fax"),
            iban=cli.get("iban"),
            codigobanco=cli.get("codigobanco"),
            codigoagencia=cli.get("codigoagencia"),
            dc=cli.get("dc"),
            ccc=cli.get("ccc"),
            codigotipoefecto=cli.get("codigotipoefecto"),
            codigocuentaefecto=cli.get("codigocuentaefecto"),
            codigocuentaimpagado=cli.get("codigocuentaimpagado"),
            remesahabitual=cli.get("remesahabitual"),
            idgrupo=cli.get("idgrupo"),
        )

        return ClienteDetalle(
            cliente=cliente,
            direcciones=[ClienteDireccion(**d) for d in raw.get("direcciones", [])],
            contactos=[ClienteContacto(**c) for c in raw.get("contactos", [])],
            contacto_principal=ClienteContacto(**raw["contacto_principal"]) if raw.get("contacto_principal") else None,
        )

    def actualizar_cliente(self, clienteid: int, body: ClienteCreateIn) -> dict:
        data = body.dict(exclude_none=True)
        data.pop("contactos", None)
        data.pop("direcciones", None)
        if not data:
            return {"clienteid": clienteid, "mensaje": "Sin cambios"}
        ok = self.repo.update_cliente(clienteid, data)
        if not ok:
            raise ValueError("No se pudo actualizar el cliente")
        return {"clienteid": clienteid, "mensaje": "Cliente actualizado"}
