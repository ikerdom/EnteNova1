from typing import List
from fastapi import APIRouter, Depends, Query
from backend.app.core.database import get_supabase
from backend.app.schemas.postal import PostalLocalidadOut

router = APIRouter(prefix="/api/postal", tags=["Postal"])


@router.get("/buscar", response_model=List[PostalLocalidadOut])
def buscar_postal(
    cp: str = Query(..., min_length=1),
    supabase=Depends(get_supabase),
):
    cp = (cp or "").strip()
    resultados = []

    # exacto
    exact = (
        supabase.table("postal_localidad")
        .select("postallocid,codigo_postal,municipio,provincia_nombre_raw,region_nombre_raw")
        .eq("codigo_postal", cp)
        .order("municipio")
        .execute()
        .data or []
    )
    resultados.extend(exact)

    # variante sin ceros
    if cp.startswith("0"):
        alt_cp = cp.lstrip("0")
        if alt_cp:
            alt = (
                supabase.table("postal_localidad")
                .select("postallocid,codigo_postal,municipio,provincia_nombre_raw,region_nombre_raw")
                .eq("codigo_postal", alt_cp)
                .order("municipio")
                .execute()
                .data or []
            )
            resultados.extend(alt)

    # dedupe por postallocid
    finales = {r["postallocid"]: r for r in resultados if r.get("postallocid")}
    return list(finales.values())
