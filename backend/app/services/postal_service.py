# backend/app/services/postal_service.py
class PostalService:
    def __init__(self, supabase):
        self.supabase = supabase

    def buscar_cp(self, cp: str):
        cp = (cp or "").strip()
        if not cp:
            return []

        resultados = []

        exact = (
            self.supabase.table("postal_localidad")
            .select("*")
            .eq("codigo_postal", cp)
            .execute()
            .data or []
        )
        resultados.extend(exact)

        if cp.startswith("0"):
            alt = cp.lstrip("0")
            if alt:
                alt_rows = (
                    self.supabase.table("postal_localidad")
                    .select("*")
                    .eq("codigo_postal", alt)
                    .execute()
                    .data or []
                )
                resultados.extend(alt_rows)

        finales = {r["postallocid"]: r for r in resultados if r.get("postallocid")}
        return list(finales.values())
