from datetime import date, timedelta


# ======================================================
# 📌 ALERTAS PARA UN TRABAJADOR (COMERCIAL)
# ======================================================
def get_alertas_trabajador(supa, trabajadorid: int) -> dict:
    """Alertas SOLO para el comercial logueado."""

    if not trabajadorid:
        # Garantizamos estructura estable
        return {
            "total": 0,
            "criticas": [],
            "hoy": [],
            "proximas": [],
            "seguimiento": [],
        }

    hoy = date.today()
    maniana = hoy + timedelta(days=1)
    sem = hoy + timedelta(days=7)
    estado_id = _estado_id(supa, "Pendiente")
    if not estado_id:
        return {
            "total": 0,
            "criticas": [],
            "hoy": [],
            "proximas": [],
            "seguimiento": [],
        }

    # --------------------------------------------------
    # 🔴 CRÍTICAS = vencidas + seguimiento vencido
    # --------------------------------------------------
    try:
        criticas = (
            supa.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, crm_actuacion_estado(estado), fecha_vencimiento, "
                "fecha_accion, titulo, resultado, requiere_seguimiento, fecha_recordatorio, "
                "cliente (clienteid, razonsocial, nombre)"
            )
            .eq("trabajador_asignadoid", trabajadorid)
            .eq("crm_actuacion_estadoid", estado_id)
            .or_(
                f"fecha_vencimiento.lt.{hoy.isoformat()},"
                f"and(requiere_seguimiento.eq.true,fecha_recordatorio.lt.{hoy.isoformat()})"
            )
            .order("fecha_vencimiento")
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        criticas = []

    # --------------------------------------------------
    # 🟠 HOY = vencen hoy o recordatorio hoy
    # --------------------------------------------------
    try:
        hoy_list = (
            supa.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, crm_actuacion_estado(estado), fecha_vencimiento, "
                "fecha_accion, titulo, resultado, requiere_seguimiento, fecha_recordatorio, "
                "cliente (clienteid, razonsocial, nombre)"
            )
            .eq("trabajador_asignadoid", trabajadorid)
            .eq("crm_actuacion_estadoid", estado_id)
            .or_(
                f"fecha_vencimiento.eq.{hoy.isoformat()},"
                f"fecha_recordatorio.eq.{hoy.isoformat()}"
            )
            .order("fecha_vencimiento")
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        hoy_list = []

    # --------------------------------------------------
    # 🟡 PRÓXIMAS = entre mañana y +7 días
    # --------------------------------------------------
    try:
        proximas = (
            supa.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, crm_actuacion_estado(estado), fecha_vencimiento, "
                "fecha_accion, titulo, resultado, requiere_seguimiento, fecha_recordatorio, "
                "cliente (clienteid, razonsocial, nombre)"
            )
            .eq("trabajador_asignadoid", trabajadorid)
            .eq("crm_actuacion_estadoid", estado_id)
            .gte("fecha_vencimiento", maniana.isoformat())
            .lte("fecha_vencimiento", sem.isoformat())
            .order("fecha_vencimiento")
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        proximas = []

    # --------------------------------------------------
    # 🔁 SEGUIMIENTO
    # --------------------------------------------------
    try:
        seguimiento = (
            supa.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, crm_actuacion_estado(estado), fecha_vencimiento, "
                "fecha_accion, titulo, resultado, requiere_seguimiento, fecha_recordatorio, "
                "cliente (clienteid, razonsocial, nombre)"
            )
            .eq("trabajador_asignadoid", trabajadorid)
            .eq("crm_actuacion_estadoid", estado_id)
            .eq("requiere_seguimiento", True)
            .order("fecha_recordatorio")
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        seguimiento = []

    # --------------------------------------------------
    # Conteo sin duplicados
    # --------------------------------------------------
    ids_totales = set()
    for lista in (criticas, hoy_list, proximas, seguimiento):
        for a in lista:
            ids_totales.add(a.get("crm_actuacionid"))

    return {
        "total": len(ids_totales),
        "criticas": criticas,
        "hoy": hoy_list,
        "proximas": proximas,
        "seguimiento": seguimiento,
    }


# ======================================================
# 📌 ALERTAS GLOBALES (ADMIN / EDITOR)
# ======================================================
def get_alertas_globales(supa) -> dict:
    """Alertas críticas globales (supervisión)."""

    hoy = date.today()

    try:
        estado_id = _estado_id(supa, "Pendiente")
        criticas = (
            supa.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, trabajador_asignadoid, crm_actuacion_estado(estado), fecha_vencimiento, "
                "fecha_accion, titulo, resultado, requiere_seguimiento, fecha_recordatorio, "
                "cliente (clienteid, razonsocial, nombre), "
                "trabajador!crm_actuacion_trabajador_asignadoid_fkey (trabajadorid, nombre, apellidos)"
            )
            .eq("crm_actuacion_estadoid", estado_id)
            .or_(
                f"fecha_vencimiento.lt.{hoy.isoformat()},"
                f"and(requiere_seguimiento.eq.true,fecha_recordatorio.lt.{hoy.isoformat()})"
            )
            .order("fecha_vencimiento")
            .limit(200)
            .execute()
            .data
            or []
        )
    except Exception:
        criticas = []

    return {
        "total": len(criticas),
        "criticas": criticas,
    }


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
    try:
        row = (
            supa.table("crm_actuacion_estado")
            .select("crm_actuacion_estadoid")
            .eq("estado", nombre)
            .single()
            .execute()
            .data
        )
    except Exception:
        row = None
    return row.get("crm_actuacion_estadoid") if row else None
