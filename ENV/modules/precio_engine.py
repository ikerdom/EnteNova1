# ======================================================
# 💸 MÓDULO DE CÁLCULO DE PRECIOS — EnteNova Gnosis
# ======================================================
# Reglas:
# - Tabla tarifa: MAESTRA, contiene descuento_pct (sin fechas).
# - Tabla tarifa_regla: asigna una tarifa a combinaciones y Rango de fechas.
#   Campos target: (clienteid | grupoid) x (productoid | familia_productoid)
#   + ventanas fecha_inicio / fecha_fin + habilitada + prioridad (asc)
#
# Jerarquía de aplicación (1 > 2 > 3 > 4 > 5 > 6):
# 1) producto + cliente
# 2) familia  + cliente
# 3) producto + grupo
# 4) familia  + grupo
# 5) cliente_tarifa activa (si existe)
# 6) fallback: "Tarifa General" (descuento 0) — si existe habilitada
#
# IVA:
# - Primero usa producto.impuestoid si está y está habilitado y vigente
# - Si no, usa producto_tipo.impuestoid
# - Si no, busca en IMPUESTO por país (según región de envío→facturación) y tipo_producto,
#   dando preferencia a coincidencia exacta de tipo_producto; fallback a "general" (tipo null)
#
# Redondeo a 2 decimales en todos los importes.

from datetime import date
from math import prod
from turtle import st
from typing import Optional, Dict, Any


def _today_iso(d: Optional[date] = None) -> str:
    return (d or date.today()).isoformat()


def _is_active_window(row: Dict[str, Any], fecha_iso: str) -> bool:
    fi = row.get("fecha_inicio")
    ff = row.get("fecha_fin")
    if fi and fi > fecha_iso:
        return False
    if ff and ff < fecha_iso:
        return False
    return True


def _first_or_none(rows):
    return rows[0] if rows else None


def _round2(x: float) -> float:
    return round(float(x or 0.0) + 1e-12, 2)  # evitar artefactos binarios

def _fetch_cliente_ctx(supabase, clienteid: Optional[int]) -> Dict[str, Any]:
    ctx = {
        "grupoid": 0,
        "regionid": None,
        "region_nombre": "España",
        "region_origen": None
    }

    if not clienteid:
        return ctx

    # grupo
    try:
        cli = (
            supabase.table("cliente")
            .select("clienteid, grupoid")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )
        if cli and cli.get("grupoid"):
            ctx["grupoid"] = cli["grupoid"]
    except:
        pass

    # dirección de envío
    try:
        env = (
            supabase.table("cliente_direccion")
            .select("regionid")
            .eq("clienteid", clienteid)
            .eq("tipo", "envio")
            .limit(1)
            .execute()
            .data
        )
        if env:
            ctx["regionid"] = env[0]["regionid"]
            ctx["region_origen"] = "envio"
    except:
        pass

    # dirección fiscal si no hay envío
    if ctx["regionid"] is None:
        try:
            fac = (
                supabase.table("cliente_direccion")
                .select("regionid")
                .eq("clienteid", clienteid)
                .eq("tipo", "fiscal")
                .limit(1)
                .execute()
                .data
            )
            if fac:
                ctx["regionid"] = fac[0]["regionid"]
                ctx["region_origen"] = "fiscal"
        except:
            pass

    # nombre región
    if ctx["regionid"]:
        reg = (
            supabase.table("region")
            .select("nombre")
            .eq("regionid", ctx["regionid"])
            .single()
            .execute()
            .data
        )
        if reg:
            ctx["region_nombre"] = reg["nombre"]

    return ctx

def _fetch_producto_ctx(supabase, productoid: Optional[int]) -> Dict[str, Any]:
    """
    Devuelve datos base del producto:
    - familia_productoid
    - precio_generico
    - impuestoid (si existe)
    - producto_tipoid
    - nombre_tipo_producto (para IVA por tipo)
    """
    ctx = {
        "familia_productoid": None,
        "precio_generico": 0.0,
        "impuestoid": None,
        "producto_tipoid": None,
        "tipo_producto_nombre": None,
    }
    if not productoid:
        return ctx
    try:
        prod = (
            supabase.table("producto")
            .select("familia_productoid, precio_generico, impuestoid, producto_tipoid")
            .eq("productoid", productoid)
            .single()
            .execute()
            .data
        )
        if prod:
            ctx["familia_productoid"] = prod.get("familia_productoid")
            ctx["precio_generico"] = float(prod.get("precio_generico") or 0.0)
            ctx["impuestoid"] = prod.get("impuestoid")
            ctx["producto_tipoid"] = prod.get("producto_tipoid")

            # nombre del tipo (para búsqueda de IVA por tipo)
            if ctx["producto_tipoid"]:
                trow = (
                    supabase.table("producto_tipo")
                    .select("nombre, impuestoid")
                    .eq("producto_tipoid", ctx["producto_tipoid"])
                    .single()
                    .execute()
                    .data
                )
                if trow:
                    ctx["tipo_producto_nombre"] = trow.get("nombre")
                    # si producto no trae impuestoid, heredar del tipo
                    if not ctx["impuestoid"] and trow.get("impuestoid"):
                        ctx["impuestoid"] = trow.get("impuestoid")
    except Exception:
        pass
    return ctx

# ======================================================
# 🧾 Resolver IVA / impuesto
# ======================================================
def _resolve_impuesto_pct(
    supabase,
    *,
    product_impuestoid: Optional[int],
    producto_tipoid: Optional[int],
    producto_tipo_nombre: Optional[str],
    region_nombre: Optional[str],
    fecha_iso: str,
) -> Dict[str, Any]:
    """
    Determina el IVA aplicable según producto, tipo y región.
    """
    # 1️⃣ Impuesto del producto
    if product_impuestoid:
        try:
            imp = (
                supabase.table("impuesto")
                .select("impuestoid, nombre, porcentaje, pais, habilitado, fecha_inicio, fecha_fin")
                .eq("impuestoid", product_impuestoid)
                .single()
                .execute()
                .data
            )
            if imp and imp.get("habilitado") and _is_active_window(imp, fecha_iso):
                return {"iva_pct": float(imp["porcentaje"]), "iva_nombre": imp["nombre"], "iva_origen": "producto"}
        except Exception:
            pass

    # 2️⃣ Impuesto del tipo de producto (si no tiene propio)
    if producto_tipoid:
        try:
            tipo = (
                supabase.table("producto_tipo")
                .select("impuestoid, nombre")
                .eq("producto_tipoid", producto_tipoid)
                .single()
                .execute()
                .data
            )
            if tipo and tipo.get("impuestoid"):
                imp = (
                    supabase.table("impuesto")
                    .select("nombre, porcentaje, pais, habilitado, fecha_inicio, fecha_fin")
                    .eq("impuestoid", tipo["impuestoid"])
                    .single()
                    .execute()
                    .data
                )
                if imp and imp.get("habilitado") and _is_active_window(imp, fecha_iso):
                    return {"iva_pct": float(imp["porcentaje"]), "iva_nombre": imp["nombre"], "iva_origen": "producto_tipo"}
        except Exception:
            pass

    # 3️⃣ Búsqueda contextual por tipo_producto + país/región
    try:
        q = supabase.table("impuesto").select("nombre, porcentaje, tipo_producto, pais, habilitado, fecha_inicio, fecha_fin")
        q = q.eq("habilitado", True)
        if region_nombre:
            q = q.eq("pais", region_nombre)
        imps = q.execute().data or []
        imps = [i for i in imps if _is_active_window(i, fecha_iso)]

        exact = [i for i in imps if (i.get("tipo_producto") or "").lower() == (producto_tipo_nombre or "").lower()]
        if exact:
            i0 = exact[0]
            return {"iva_pct": float(i0["porcentaje"]), "iva_nombre": i0["nombre"], "iva_origen": "busqueda"}

        general = [i for i in imps if not i.get("tipo_producto")]
        if general:
            i0 = general[0]
            return {"iva_pct": float(i0["porcentaje"]), "iva_nombre": i0["nombre"], "iva_origen": "busqueda"}
    except Exception:
        pass

    # 4️⃣ Fallback genérico España 21%
    try:
        imp_es = (
            supabase.table("impuesto")
            .select("nombre, porcentaje")
            .eq("pais", "España")
            .eq("habilitado", True)
            .execute()
            .data
        )
        if imp_es:
            gen = next((i for i in imp_es if "general" in i.get("nombre", "").lower()), imp_es[0])
            return {"iva_pct": float(gen["porcentaje"]), "iva_nombre": gen["nombre"], "iva_origen": "fallback"}
    except Exception:
        pass

    return {"iva_pct": 0.0, "iva_nombre": None, "iva_origen": "desconocido"}

# ======================================================
# 🧮 Resolver tarifa aplicable según jerarquía
# ======================================================
def _resolve_tarifa(
    supabase,
    fecha_iso: str,
    *,
    clienteid: Optional[int],
    grupoid: Optional[int],
    productoid: Optional[int],
    familiaid: Optional[int],
) -> Dict[str, Any]:
    """
    Devuelve la mejor tarifa aplicable respetando jerarquía, fechas y prioridad.
    Si no encuentra ninguna válida, devuelve la Tarifa General (5%).
    """

    out = {
        "nivel_tarifa": "fallback_general",
        "tarifaid": 5,
        "tarifa_aplicada": "Tarifa General",
        "descuento_pct": 5.0,
        "regla_id": None,
    }

    try:
        # Cargar todas las reglas activas
        reglas = (
            supabase.table("tarifa_regla")
            .select(
                "tarifa_reglaid, tarifaid, clienteid, grupoid, productoid, familia_productoid, "
                "fecha_inicio, fecha_fin, prioridad, habilitada"
            )
            .eq("habilitada", True)
            .execute()
            .data
            or []
        )
    except Exception:
        reglas = []

    # Filtrar por fecha vigente
    reglas = [r for r in reglas if _is_active_window(r, fecha_iso)]
    if not reglas:
        return out

    # 🔹 Definir jerarquía (más específica a menos)
    jerarquia = [
        ("producto+cliente", lambda r: r["clienteid"] == clienteid and r["productoid"] == productoid),
        ("familia+cliente",  lambda r: r["clienteid"] == clienteid and r["familia_productoid"] == familiaid),
        ("producto+grupo",   lambda r: r["grupoid"] == grupoid and r["productoid"] == productoid),
        ("familia+grupo",    lambda r: r["grupoid"] == grupoid and r["familia_productoid"] == familiaid),
    ]

    # 🔹 Buscar mejor regla según jerarquía
    for nivel, cond in jerarquia:
        candidatas = [r for r in reglas if cond(r)]
        if not candidatas:
            continue

        # Enriquecer con datos de la tarifa
        enriched = []
        for r in candidatas:
            try:
                t = (
                    supabase.table("tarifa")
                    .select("tarifaid, nombre, descuento_pct, habilitada")
                    .eq("tarifaid", r["tarifaid"])
                    .single()
                    .execute()
                    .data
                )
                if not t or not t.get("habilitada"):
                    continue

                enriched.append({
                    "nivel_tarifa": nivel,
                    "tarifaid": t["tarifaid"],
                    "tarifa_aplicada": t["nombre"],
                    "descuento_pct": float(t["descuento_pct"] or 0.0),
                    "regla_id": r["tarifa_reglaid"],
                    "fecha_inicio": r.get("fecha_inicio"),
                    "prioridad": r.get("prioridad") or 999,
                })
            except Exception:
                continue

        if enriched:
            # Ordenar: descuento DESC, fecha_inicio más reciente DESC, prioridad ASC
            enriched.sort(
                key=lambda x: (-x["descuento_pct"], x["fecha_inicio"] or "", x["prioridad"])
            )
            mejor = enriched[0]
            return mejor

    # 🔹 Cliente_tarifa (directa) si tiene alguna vigente
    try:
        cts = (
            supabase.table("cliente_tarifa")
            .select("tarifaid, fecha_desde, fecha_hasta")
            .eq("clienteid", clienteid)
            .execute()
            .data
            or []
        )
        cts = [c for c in cts if _is_active_window({"fecha_inicio": c.get("fecha_desde"), "fecha_fin": c.get("fecha_hasta")}, fecha_iso)]
        if cts:
            t = (
                supabase.table("tarifa")
                .select("tarifaid, nombre, descuento_pct, habilitada")
                .eq("tarifaid", cts[0]["tarifaid"])
                .single()
                .execute()
                .data
            )
            if t and t.get("habilitada"):
                return {
                    "nivel_tarifa": "cliente_tarifa",
                    "tarifaid": t["tarifaid"],
                    "tarifa_aplicada": t["nombre"],
                    "descuento_pct": float(t["descuento_pct"] or 0.0),
                    "regla_id": None,
                }
    except Exception:
        pass

    # 🔹 Fallback: Tarifa General
    return out


# ======================================================
# 💸 FUNCIÓN PRINCIPAL — Cálculo completo de línea
# ======================================================
def calcular_precio_linea(
    supabase,
    clienteid: Optional[int] = None,
    productoid: Optional[int] = None,
    precio_base_unit: Optional[float] = None,
    cantidad: float = 1.0,
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    fecha_iso = _today_iso(fecha)
    cli_ctx = _fetch_cliente_ctx(supabase, clienteid)
    pr_ctx = _fetch_producto_ctx(supabase, productoid)

    grupoid = cli_ctx.get("grupoid")
    familiaid = pr_ctx.get("familia_productoid")

    unit_bruto = float(precio_base_unit or pr_ctx.get("precio_generico") or 0.0)

    # 🔹 Resolver tarifa según jerarquía
    tarifa = _resolve_tarifa(
        supabase,
        fecha_iso,
        clienteid=clienteid,
        grupoid=grupoid,
        productoid=productoid,
        familiaid=familiaid,
    )

    descuento_pct = float(tarifa.get("descuento_pct") or 0.0)
    unit_neto = _round2(unit_bruto * (1 - descuento_pct / 100.0))
    subtotal = _round2(unit_neto * cantidad)

    # 🔹 Resolver IVA
    ivx = _resolve_impuesto_pct(
        supabase,
        product_impuestoid=pr_ctx.get("impuestoid"),
        producto_tipoid=pr_ctx.get("producto_tipoid"),
        producto_tipo_nombre=pr_ctx.get("tipo_producto_nombre"),
        region_nombre=cli_ctx.get("region_nombre") or "España",
        fecha_iso=fecha_iso,
    )
    iva_pct = float(ivx.get("iva_pct") or 0.0)
    iva_importe = _round2(subtotal * iva_pct / 100.0)
    total_con_iva = _round2(subtotal + iva_importe)

    return {
        "unit_bruto": _round2(unit_bruto),
        "descuento_pct": _round2(descuento_pct),
        "unit_neto_sin_iva": unit_neto,
        "subtotal_sin_iva": subtotal,
        "iva_pct": iva_pct,
        "iva_importe": iva_importe,
        "total_con_iva": total_con_iva,
        "tarifaid": tarifa.get("tarifaid"),
        "tarifa_aplicada": tarifa.get("tarifa_aplicada"),
        "nivel_tarifa": tarifa.get("nivel_tarifa"),
        "regla_id": tarifa.get("regla_id"),
        "iva_nombre": ivx.get("iva_nombre"),
        "iva_origen": ivx.get("iva_origen"),
        "region": cli_ctx.get("region_nombre") or "España",
        "region_origen": cli_ctx.get("region_origen"),
    }
