# backend/app/schemas/crm_actuacion.py
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel


class CrmActuacionIn(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None

    crm_actuacion_tipoid: Optional[int] = None
    crm_actuacion_estadoid: Optional[int] = None

    fecha_vencimiento: Optional[date] = None
    fecha_accion: Optional[datetime] = None

    requiere_seguimiento: bool = False
    fecha_recordatorio: Optional[datetime] = None

    trabajador_creadorid: Optional[int] = None
    trabajador_asignadoid: Optional[int] = None


class CrmActuacionOut(BaseModel):
    crm_actuacionid: int
    clienteid: Optional[int] = None

    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None

    crm_actuacion_tipoid: Optional[int] = None
    crm_actuacion_estadoid: Optional[int] = None

    fecha_vencimiento: Optional[date] = None
    fecha_accion: Optional[datetime] = None

    requiere_seguimiento: Optional[bool] = None
    fecha_recordatorio: Optional[datetime] = None

    trabajador_creadorid: Optional[int] = None
    trabajador_asignadoid: Optional[int] = None
