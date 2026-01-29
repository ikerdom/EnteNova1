from fastapi import FastAPI
from backend.app.api import (
    catalogos,
    clientes,
    postal,
    productos,
    cliente_contacto,
    cliente_observacion,
    cliente_direccion,
    crm_actuacion,
    presupuestos,
    tarifas,
    pedidos,
    crm_acciones,
)

app = FastAPI(title="ERP EnteNova")

app.include_router(clientes.router)
app.include_router(catalogos.router)
app.include_router(postal.router)
app.include_router(productos.router)
app.include_router(cliente_contacto.router)
app.include_router(cliente_observacion.router)
app.include_router(cliente_direccion.router)
app.include_router(crm_actuacion.router)
app.include_router(presupuestos.router)
app.include_router(tarifas.router)
app.include_router(pedidos.router)
app.include_router(crm_acciones.router)

@app.get("/health")
def health():
    return {"status": "ok"}
