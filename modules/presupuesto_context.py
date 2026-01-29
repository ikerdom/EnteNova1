# modules/presupuesto_context.py
"""
Contexto unificado de presupuesto para el motor de PDF.

Este módulo NO pinta nada, solo:
- Lee presupuesto, cliente, direcciones, comercial y líneas.
- Calcula totales y desglose de IVA.
- Devuelve un dict 'ctx' coherente para presupuesto_pdf.build_pdf_bytes().
"""

from datetime import datetime, date


# ---------------------------
# Helpers internos
# ---------------------------
def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _fmt_fecha_iso_to_ddmmyyyy(fecha):
    """
    Recibe:
      - '2025-11-19'
      - '2025-11-19 10:01:44'
      - datetime / date
    y devuelve '19/11/2025'.
    Si no puede parsear, devuelve tal cual en str.
    """
    if not fecha:
        return "-"

    # Si ya es date/datetime
    if isinstance(fecha, (datetime, date)):
        return fecha.strftime("%d/%m/%Y")

    # Si es string
    s = str(fecha)
    # Intentar parsear como ISO con datetime.fromisoformat
    try:
        d = datetime.fromisoformat(s)
        return d.strftime("%d/%m/%Y")
    except Exception:
        # Último intento: sólo la parte de fecha (YYYY-MM-DD)
        try:
            base = s.split(" ")[0]
            d = datetime.fromisoformat(base)
            return d.strftime("%d/%m/%Y")
        except Exception:
            return s


# ---------------------------
# Cargas básicas (siempre devuelven dict)
# ---------------------------
def _load_presupuesto(supabase, presupuestoid: int) -> dict:
    res = (
        supabase.table("presupuesto")
        .select("*")
        .eq("presupuesto_id", presupuestoid)
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_cliente(supabase, clienteid: int) -> dict:
    if not clienteid:
        return {}
    res = (
        supabase.table("cliente")
        .select("*")
        .eq("idtercero", clienteid)
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_trabajador(supabase, trabajadorid: int) -> dict:
    if not trabajadorid:
        return {}
    res = (
        supabase.table("trabajador")
        .select("trabajadorid, nombre, apellidos, telefono, email")
        .eq("trabajadorid", trabajadorid)
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_forma_pago(supabase, forma_pagoid: int) -> dict:
    if not forma_pagoid:
        return {}
    res = (
        supabase.table("forma_pago")
        .select("*")
        .eq("formapagoid", forma_pagoid)
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_direccion_by_id(supabase, cliente_direccionid: int) -> dict:
    if not cliente_direccionid:
        return {}
    res = (
        supabase.table("clientes_direccion")
        .select(
            "clientes_direccionid, direccionfiscal, direccion, codigopostal, municipio, idprovincia, idpais"
        )
        .eq("clientes_direccionid", cliente_direccionid)
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_direccion_fiscal(supabase, clienteid: int) -> dict:
    if not clienteid:
        return {}
    res = (
        supabase.table("clientes_direccion")
        .select(
            "clientes_direccionid, direccionfiscal, direccion, codigopostal, municipio, idprovincia, idpais"
        )
        .eq("idtercero", clienteid)
        
        .maybe_single()
        .execute()
    )
    return res.data or {}


def _load_primera_direccion_envio(supabase, clienteid: int) -> dict:
    if not clienteid:
        return {}
    res = (
        supabase.table("clientes_direccion")
        .select(
            "clientes_direccionid, direccionfiscal, direccion, codigopostal, municipio, idprovincia, idpais"
        )
        .eq("idtercero", clienteid)
        
        .order("cliente_direccionid")
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else {}


# ---------------------------
# Líneas y totales
# ---------------------------
def _load_lineas_presupuesto(supabase, presupuestoid: int):
    """
    Devuelve:
      - lista de lineas en formato PDF
      - dict totales
    """
    res = (
        supabase.table("presupuesto_linea")
        .select(
            "presupuesto_linea_id, descripcion, cantidad, precio_unitario, "
            "descuento_pct, iva_pct, base_linea, iva_importe, total_linea"
        )
        .eq("presupuesto_id", presupuestoid)
        .order("presupuesto_linea_id")
        .execute()
    )
    lineas_raw = res.data or []


    lineas_pdf = []
    desglose = {}  # {iva_pct: {"base": x, "iva": y}}
    base_total = 0.0
    iva_total = 0.0
    total_total = 0.0

    for ln in lineas_raw:
        try:
            cant = float(ln.get("cantidad") or 0)
        except Exception:
            cant = 0.0
        try:
            precio_unit = float(ln.get("precio_unitario") or 0)
        except Exception:
            precio_unit = 0.0
        try:
            dto_pct = float(ln.get("descuento_pct") or 0)
        except Exception:
            dto_pct = 0.0
        try:
            iva_pct = float(ln.get("iva_pct") or 0)
        except Exception:
            iva_pct = 0.0
        try:
            base = float(ln.get("base_linea") or 0)
        except Exception:
            base = cant * precio_unit * (1 - dto_pct / 100.0) if cant and precio_unit else 0.0
        try:
            total_linea = float(ln.get("total_linea") or 0)
        except Exception:
            total_linea = base * (1 + iva_pct / 100.0)

        iva_importe = base * iva_pct / 100.0

        base_total += base
        iva_total += iva_importe
        total_total += total_linea

        key = int(iva_pct)
        if key not in desglose:
            desglose[key] = {"base": 0.0, "iva": 0.0}
        desglose[key]["base"] += base
        desglose[key]["iva"] += iva_importe

        lineas_pdf.append(
            {
                "concepto": ln.get("descripcion") or "-",
                "unidades": cant,
                "precio": precio_unit,
                "dto": dto_pct,
                "iva": iva_pct,
                "base": base,
                "total": total_linea,
            }
        )

    if total_total <= 0:
        total_total = base_total + iva_total

    totales = {
        "base": base_total,
        "iva": iva_total,
        "total": total_total,
        "desglose": desglose,
    }

    return lineas_pdf, totales


# ---------------------------
# Empresa (simple por ahora)
# ---------------------------
def _load_empresa() -> dict:
    """
    De momento, dejamos datos fijos.
    Si en el futuro tienes tabla 'empresa', aquí se puede leer.
    """
    return {
        "nombre": "ORBE · Editorial / Formación",
        "cif": "B-00000000",
        "direccion": "C/ Ejemplo 123, Madrid",
        "telefono": "+34 900 000 000",
        "email": "info@orbe.com",
        "web": "www.orbe.com",
        "logo_path": "./logo_orbe.png",
        "texto_legal": (
            "Este presupuesto es válido durante 30 días desde la fecha de emisión. "
            "Los precios no incluyen otros impuestos o tasas que pudieran ser de aplicación. "
            "El tratamiento de datos personales se realiza conforme al RGPD y la LOPDGDD."
        ),
    }


# ---------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------
def build_presupuesto_context(supabase, presupuestoid: int) -> dict:
    """
    Devuelve un dict con:
      - empresa
      - cliente
      - presupuesto
      - lineas
      - totales
      - direccion_fiscal
      - direccion_envio
    que es justo lo que espera presupuesto_pdf.build_pdf_bytes().
    """
    pres = _load_presupuesto(supabase, presupuestoid)
    if not pres:
        raise ValueError(f"Presupuesto {presupuestoid} no encontrado")

    clienteid = pres.get("clienteid")
    trabajadorid = pres.get("trabajadorid")

    cliente_raw = _load_cliente(supabase, clienteid)
    trabajador = _load_trabajador(supabase, trabajadorid)

    # Forma de pago: de momento desde el cliente
    forma_pagoid = cliente_raw.get("formapagoid") or cliente_raw.get("forma_pagoid")
    forma_pago = _load_forma_pago(supabase, forma_pagoid) if forma_pagoid else {}

    # Empresa
    empresa = _load_empresa()

    # Cliente (normalizado para el PDF)
    cliente_ctx = {
        "razon_social": _safe(
            cliente_raw.get("razon_social")
            or cliente_raw.get("nombre_comercial")
            or "",
            "-"
        ),
        "cif": _safe(
            cliente_raw.get("cif_nif") or cliente_raw.get("cif"),
            "-"
        ),
        # Contacto / ATT — primero lo que haya en el presupuesto, luego fallback al cliente
        "contacto_att": pres.get("contacto_att")
        or cliente_raw.get("contacto_att")
        or None,
        "telefono_contacto": pres.get("telefono_contacto")
        or cliente_raw.get("telefono_contacto")
        or cliente_raw.get("telefono")
        or None,
        "email_contacto": pres.get("email_contacto")
        or cliente_raw.get("email_contacto")
        or cliente_raw.get("email")
        or None,
    }

    # Comercial / trabajador
    if trabajador:
        comercial_nombre = (
            (trabajador.get("nombre") or "") + " " + (trabajador.get("apellidos") or "")
        ).strip()
    else:
        comercial_nombre = ""

    # Forma de pago (nombre)
    forma_pago_nombre = forma_pago.get("nombre") if forma_pago else None

    # Fechas (las dejamos ya formateadas dd/mm/yyyy)
    fecha_pres_fmt = _fmt_fecha_iso_to_ddmmyyyy(pres.get("fecha_presupuesto"))
    fecha_validez_fmt = _fmt_fecha_iso_to_ddmmyyyy(pres.get("fecha_validez"))

    # Presupuesto (cabecera documento)
    presupuesto_ctx = {
        "numero": pres.get("numero"),
        "fecha": fecha_pres_fmt,
        "validez": fecha_validez_fmt,
        "forma_pago": _safe(forma_pago_nombre, "-"),
        "comercial": _safe(comercial_nombre, "-"),
        "observaciones": pres.get("observaciones") or "",
    }

    # Direcciones
    direccion_fiscal = _load_direccion_fiscal(supabase, clienteid)

    direccion_envio = {}
    if pres.get("direccion_envioid"):
        direccion_envio = _load_direccion_by_id(supabase, pres["direccion_envioid"])
    if not direccion_envio:
        # fallback: primera de envío
        direccion_envio = _load_primera_direccion_envio(supabase, clienteid)
    if not direccion_envio:
        # último fallback: fiscal
        direccion_envio = direccion_fiscal or {}

    # Normalizar formato de direcciones para el PDF
    def _norm_dir(d: dict) -> dict:
        if not d:
            return {}
        return {
            "direccion": d.get("direccion"),
            "cp": d.get("cp"),
            "ciudad": d.get("ciudad"),
            "provincia": d.get("provincia"),
            "pais": d.get("pais") or "ESPAÑA",
        }

    dir_fiscal_ctx = _norm_dir(direccion_fiscal)
    dir_envio_ctx = _norm_dir(direccion_envio)

    # Líneas + totales
    lineas_ctx, totales_ctx = _load_lineas_presupuesto(supabase, presupuestoid)

    ctx = {
        "empresa": empresa,
        "cliente": cliente_ctx,
        "presupuesto": presupuesto_ctx,
        "lineas": lineas_ctx,
        "totales": totales_ctx,
        "direccion_fiscal": dir_fiscal_ctx,
        "direccion_envio": dir_envio_ctx,
    }

    return ctx
