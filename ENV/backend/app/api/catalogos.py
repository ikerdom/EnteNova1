from fastapi import APIRouter, Depends

from backend.app.core.database import get_supabase

router = APIRouter(prefix="/api/catalogos", tags=["Catalogos"])


@router.get("/trabajadores")
def listar_trabajadores(supabase=Depends(get_supabase)):
    try:
        rows = (
            supabase.table("trabajador")
            .select("trabajadorid,nombre,apellidos")
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    return rows
