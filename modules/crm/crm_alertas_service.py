import requests
from modules.api_base import get_api_base


def _handle(resp: requests.Response) -> dict:
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


# ======================================================
# ðŸ“Œ ALERTAS PARA UN TRABAJADOR (COMERCIAL)
# ======================================================
def get_alertas_trabajador(_supa_unused, trabajadorid: int) -> dict:
    if not trabajadorid:
        return {
            "total": 0,
            "criticas": [],
            "hoy": [],
            "proximas": [],
            "seguimiento": [],
        }
    try:
        r = requests.get(
            f"{get_api_base()}/api/crm/alertas",
            params={"trabajadorid": trabajadorid},
            timeout=20,
        )
        return _handle(r)
    except Exception:
        return {
            "total": 0,
            "criticas": [],
            "hoy": [],
            "proximas": [],
            "seguimiento": [],
        }


# ======================================================
# ðŸ“Œ ALERTAS GLOBALES (ADMIN / EDITOR)
# ======================================================
def get_alertas_globales(_supa_unused) -> dict:
    try:
        r = requests.get(f"{get_api_base()}/api/crm/alertas/globales", timeout=20)
        return _handle(r)
    except Exception:
        return {"total": 0, "criticas": []}


# ======================================================
# 📌 WRAPPER COMPATIBLE (Topbar + Supervisión)
# ======================================================
def get_alertas_usuario(supa, trabajadorid: int):
    """
    Función buscada por:
    - topbar (alertas rápidas)
    - campania_supervision
    - widgets globales

    Produce una LISTA PLANA de alertas:
        [{ titulo, mensaje, prioridad, color }, ...]
    """

    if not trabajadorid:
        return []

    data = get_alertas_trabajador(supa, trabajadorid)

    alertas = []

    # -------- CRÍTICAS --------
    for a in data.get("criticas", []):
        cli = a.get("cliente", {}).get("razonsocial") or a.get("cliente", {}).get("nombre", "Cliente")
        fecha = a.get("fecha_vencimiento") or "—"

        alertas.append({
            "titulo": a.get("titulo") or "Actuación crítica",
            "mensaje": f"{cli} — vencida el {fecha}",
            "prioridad": "Alta",
            "color": "#ef4444",
        })

    # -------- HOY --------
    for a in data.get("hoy", []):
        cli = a.get("cliente", {}).get("razonsocial") or a.get("cliente", {}).get("nombre", "Cliente")
        alertas.append({
            "titulo": a.get("titulo") or "Actuación para hoy",
            "mensaje": f"{cli} — vence hoy",
            "prioridad": "Media",
            "color": "#f59e0b",
        })

    # -------- PRÓXIMAS --------
    for a in data.get("proximas", []):
        cli = a.get("cliente", {}).get("razonsocial") or a.get("cliente", {}).get("nombre", "Cliente")
        fecha = a.get("fecha_vencimiento") or "—"
        alertas.append({
            "titulo": a.get("titulo") or "Próxima actuación",
            "mensaje": f"{cli} — vence el {fecha}",
            "prioridad": "Baja",
            "color": "#3b82f6",
        })

    return alertas


# ======================================================
# 📌 RESUMEN GLOBAL (Cabecera supervisión)
# ======================================================
def get_resumen_global(supa):
    """Resumen rápido para tarjetas del dashboard de supervisión."""
    hoy = date.today()

    # Contadores seguros (Supabase count)
    try:
        estado_id = _estado_id(supa, "Pendiente")
        tot = (
            supa.table("crm_actuacion")
            .select("crm_actuacionid", count="exact")
            .eq("crm_actuacion_estadoid", estado_id)
            .execute()
            .count
            or 0
        )
    except Exception:
        tot = 0

    try:
        hoy_ct = (
            supa.table("crm_actuacion")
            .select("crm_actuacionid", count="exact")
            .eq("crm_actuacion_estadoid", estado_id)
            .eq("fecha_vencimiento", hoy.isoformat())
            .execute()
            .count
            or 0
        )
    except Exception:
        hoy_ct = 0

    try:
        venc = (
            supa.table("crm_actuacion")
            .select("crm_actuacionid", count="exact")
            .eq("crm_actuacion_estadoid", estado_id)
            .lt("fecha_vencimiento", hoy.isoformat())
            .execute()
            .count
            or 0
        )
    except Exception:
        venc = 0

    alta = hoy_ct + venc

    return {
        "alertas_totales": tot,
        "hoy": hoy_ct,
        "vencidas": venc,
        "alta": alta,
    }


def _estado_id(supa, nombre: str):
    return None
