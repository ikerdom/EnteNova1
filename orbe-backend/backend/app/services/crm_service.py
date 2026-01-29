from typing import List, Optional
from datetime import datetime

from backend.app.repositories.crm_repo import CrmRepository
from backend.app.schemas.crm import CrmAccionCreate, CrmAccionUpdate, CrmAccionOut, CrmAccionList


class CrmService:
    def __init__(self, repo: CrmRepository):
        self.repo = repo

    def listar(self, filtros: dict) -> CrmAccionList:
        rows = self.repo.listar(filtros)
        return CrmAccionList(data=[CrmAccionOut(**r) for r in rows])

    def crear(self, data: CrmAccionCreate) -> CrmAccionOut:
        payload = data.dict(exclude_none=True)
        created = self.repo.crear(payload)
        return CrmAccionOut(**created)

    def actualizar(self, accionid: int, data: CrmAccionUpdate) -> CrmAccionOut:
        payload = {}
        for k, v in data.dict(exclude_none=True).items():
            if isinstance(v, datetime):
                payload[k] = v.isoformat()
            else:
                payload[k] = v
        updated = self.repo.actualizar(accionid, payload)
        if not updated:
            raise ValueError("Acción no encontrada")
        return CrmAccionOut(**updated)

    def obtener(self, accionid: int) -> CrmAccionOut:
        acc = self.repo.obtener(accionid)
        if not acc:
            raise ValueError("Acción no encontrada")
        return CrmAccionOut(**acc)
