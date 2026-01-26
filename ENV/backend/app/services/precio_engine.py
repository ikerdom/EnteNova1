from datetime import date
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


def _round2(x: float) -> float:
    return round(float(x or 0.0) + 1e-12, 2)


def _fetch_cliente_ctx(supabase, clienteid: Optional[int]) -> Dict[str, Any]:
    ctx = {
        "grupoid": 0,
        "ambito": "ES",
        "region_origen": None,
    }

    if not clienteid:
        return ctx

    try:
        cli = (
            supabase.table("cliente")
            .select("clienteid, idgrupo")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )
        if cli and cli.get("idgrupo"):
            ctx["grupoid"] = cli["idgrupo"]
    except Exception:
        pass

    try:
        env = (
            supabase.table("clientes_direccion")
            .select("idpais")
            .eq("idtercero", clienteid)
            .order("clientes_direccionid")
            .limit(1)
            .execute()
            .data
        )
        if env and env[0].get("idpais"):
            ctx["ambito"] = env[0]["idpais"]
            ctx["region_origen"] = "envio"
    except Exception:
        pass

    return ctx


def _fetch_producto_ctx(supabase, productoid: Optional[int]) -> Dict[str, Any]:
    ctx = {
        "familia_productoid": None,
        "precio_generico": 0.0,
        "producto_tipoid": None,
        "tipo_producto_nombre": None,
    }
    if not productoid:
        return ctx

    try:
        prod = (
            supabase.table("producto")
            .select("producto_familiaid, pvp, producto_tipoid")
            .eq("catalogo_productoid", productoid)
            .single()
            .execute()
            .data
        )
        if prod:
            ctx["familia_productoid"] = prod.get("producto_familiaid")
            ctx["precio_generico"] = float(prod.get("pvp") or 0.0)
            ctx["producto_tipoid"] = prod.get("producto_tipoid")

            if ctx["producto_tipoid"]:
                trow = (
                    supabase.table("producto_tipo")
                    .select("nombre")
                    .eq("producto_tipoid", ctx["producto_tipoid"])
                    .single()
                    .execute()
                    .data
                )
                if trow:
                    ctx["tipo_producto_nombre"] = trow.get("nombre")
    except Exception:
        pass

    return ctx


def _resolve_impuesto_pct(
    supabase,
    *,
    producto_tipoid: Optional[int],
    ambito: Optional[str],
    fecha_iso: str,
) -> Dict[str, Any]:
    try:
        rows = (
            supabase.table("impuesto")
            .select(
                "impuestoid, impuesto_nombre, tasa_pct, ambito, producto_tipoid, habilitado, fecha_inicio, fecha_fin"
            )
            .eq("habilitado", True)
            .execute()
            .data
            or []
        )
        rows = [r for r in rows if _is_active_window(r, fecha_iso)]
        if ambito:
            rows = [r for r in rows if (r.get("ambito") or "").upper() == ambito.upper()]

        tipo_rows = [r for r in rows if producto_tipoid and r.get("producto_tipoid") == producto_tipoid]
        if tipo_rows:
            best = sorted(tipo_rows, key=lambda r: r.get("fecha_inicio") or "", reverse=True)[0]
            return {
                "iva_pct": float(best.get("tasa_pct") or 0.0),
                "iva_nombre": best.get("impuesto_nombre"),
                "iva_origen": "producto_tipo",
            }

        general = [r for r in rows if not r.get("producto_tipoid")]
        if general:
            best = sorted(general, key=lambda r: r.get("fecha_inicio") or "", reverse=True)[0]
            return {
                "iva_pct": float(best.get("tasa_pct") or 0.0),
                "iva_nombre": best.get("impuesto_nombre"),
                "iva_origen": "ambito_general",
            }
    except Exception:
        pass

    return {"iva_pct": 0.0, "iva_nombre": None, "iva_origen": "desconocido"}


def _resolve_tarifa(
    supabase,
    fecha_iso: str,
    *,
    clienteid: Optional[int],
    grupoid: Optional[int],
    productoid: Optional[int],
    familiaid: Optional[int],
) -> Dict[str, Any]:
    out = {
        "nivel_tarifa": "fallback_general",
        "tarifaid": 5,
        "tarifa_aplicada": "Tarifa General",
        "descuento_pct": 5.0,
        "regla_id": None,
    }

    try:
        reglas = (
            supabase.table("tarifa_regla")
            .select("*")
            .eq("habilitada", True)
            .execute()
            .data
            or []
        )
    except Exception:
        reglas = []

    reglas = [r for r in reglas if _is_active_window(r, fecha_iso)]
    if not reglas:
        return out

    def _regla_producto(r):
        return (
            r.get("catalogo_productoid") == productoid
            or r.get("catalogo_productoid_viejo") == productoid
            or r.get("productoid") == productoid
        )

    jerarquia = [
        ("producto+cliente", lambda r: r.get("clienteid") == clienteid and _regla_producto(r)),
        ("familia+cliente",  lambda r: r.get("clienteid") == clienteid and r.get("familia_productoid") == familiaid),
        ("producto+grupo",   lambda r: r.get("idgrupo") == grupoid and _regla_producto(r)),
        ("familia+grupo",    lambda r: r.get("idgrupo") == grupoid and r.get("familia_productoid") == familiaid),
    ]

    for nivel, cond in jerarquia:
        candidatas = [r for r in reglas if cond(r)]
        if not candidatas:
            continue

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

                enriched.append(
                    {
                        "nivel_tarifa": nivel,
                        "tarifaid": t["tarifaid"],
                        "tarifa_aplicada": t["nombre"],
                        "descuento_pct": float(t["descuento_pct"] or 0.0),
                        "regla_id": r["tarifa_reglaid"],
                        "fecha_inicio": r.get("fecha_inicio"),
                        "prioridad": r.get("prioridad") or 999,
                    }
                )
            except Exception:
                continue

        if enriched:
            enriched.sort(key=lambda x: (-x["descuento_pct"], x["fecha_inicio"] or "", x["prioridad"]))
            return enriched[0]

    try:
        cts = (
            supabase.table("cliente_tarifa")
            .select("tarifaid, fecha_desde, fecha_hasta")
            .eq("clienteid", clienteid)
            .execute()
            .data
            or []
        )
        cts = [
            c for c in cts if _is_active_window(
                {"fecha_inicio": c.get("fecha_desde"), "fecha_fin": c.get("fecha_hasta")},
                fecha_iso,
            )
        ]
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

    return out


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

    ivx = _resolve_impuesto_pct(
        supabase,
        producto_tipoid=pr_ctx.get("producto_tipoid"),
        ambito=cli_ctx.get("ambito") or "ES",
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
        "region": cli_ctx.get("ambito") or "ES",
        "region_origen": cli_ctx.get("region_origen"),
    }
