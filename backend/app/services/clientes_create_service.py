import time
from fastapi import HTTPException
from backend.app.schemas.cliente_create import ClienteCreateIn, ClienteCreateOut


class ClientesCreateService:
    def __init__(self, supabase):
        self.supabase = supabase

    def crear(self, data: ClienteCreateIn) -> ClienteCreateOut:
        if not (data.razonsocial or data.nombre):
            raise HTTPException(status_code=400, detail="Razonsocial o nombre es obligatorio.")

        cliente_payload = {
            "codigocuenta": data.codigocuenta,
            "codigoclienteoproveedor": data.codigoclienteoproveedor,
            "clienteoproveedor": data.clienteoproveedor,
            "razonsocial": data.razonsocial,
            "nombre": data.nombre,
            "cifdni": data.cifdni,
            "cif_normalizado": data.cif_normalizado,
            "viapublica": data.viapublica,
            "domicilio": data.domicilio,
            "codigopostal": data.codigopostal,
            "provincia": data.provincia,
            "municipio": data.municipio,
            "telefono": data.telefono,
            "telefono2": data.telefono2,
            "telefono3": data.telefono3,
            "fax": data.fax,
            "iban": data.iban,
            "codigobanco": data.codigobanco,
            "codigoagencia": data.codigoagencia,
            "dc": data.dc,
            "ccc": data.ccc,
            "codigotipoefecto": data.codigotipoefecto,
            "codigocuentaefecto": data.codigocuentaefecto,
            "codigocuentaimpagado": data.codigocuentaimpagado,
            "remesahabitual": data.remesahabitual,
            "idgrupo": data.idgrupo,
        }

        res = self.supabase.table("cliente").insert(cliente_payload).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el cliente.")
        clienteid = res.data[0]["clienteid"]

        if data.direcciones:
            for d in data.direcciones:
                payload = d.dict(exclude_none=True)
                payload["idtercero"] = payload.get("idtercero") or clienteid
                if not payload.get("direccion_origen_id"):
                    payload["direccion_origen_id"] = int(time.time() * 1000)
                self.supabase.table("clientes_direccion").insert(payload).execute()

        if data.contactos:
            for c in data.contactos:
                row = c.dict(exclude_none=True)
                row["clienteid"] = clienteid
                self.supabase.table("cliente_contacto").insert(row).execute()

        msg = "Cliente creado correctamente."
        return ClienteCreateOut(clienteid=clienteid, mensaje=msg)
