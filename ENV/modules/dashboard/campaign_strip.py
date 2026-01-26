# modules/dashboard/campaign_strip.py

import streamlit as st
from datetime import date
from modules.dashboard.utils import safe_date


# ======================================================
# 📣 TIRA SUPERIOR DE CAMPAÑAS ACTIVAS (SEMANA)
# ======================================================
def render_campaign_strip(
    supabase,
    semana_ini: date,
    semana_fin: date,
    trabajadorid: int | None,
    ver_todo: bool,
):
    try:
        # ------------------------------------------------------
        # 1) Campañas activas
        # ------------------------------------------------------
        camp_res = (
            supabase.table("campania")
            .select(
                "campaniaid, nombre, tipo_accion, fecha_inicio, fecha_fin, "
                "objetivo_total, objetivo_diario, estado"
            )
            .eq("estado", "activa")
            .execute()
        )

        campanias = camp_res.data or []
        if not campanias:
            return

        camp_ids = [c["campaniaid"] for c in campanias]

        # ------------------------------------------------------
        # 2) Relación campaña ↔ actuación
        # ------------------------------------------------------
        rel_res = (
            supabase.table("campania_actuacion")
            .select("campaniaid, actuacionid")
            .in_("campaniaid", camp_ids)
            .execute()
        )

        relaciones = rel_res.data or []
        if not relaciones:
            return

        # Map: actuacion → campaña
        act_to_camp = {r["actuacionid"]: r["campaniaid"] for r in relaciones}
        act_ids = list(act_to_camp.keys())
        if not act_ids:
            return

        # ------------------------------------------------------
        # 3) Actuaciones de la semana
        # ------------------------------------------------------
        acts_res = (
            supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, crm_actuacion_estado(estado), fecha_accion, trabajador_creadorid, trabajador_asignadoid"
            )
            .in_("crm_actuacionid", act_ids)
            .gte("fecha_accion", semana_ini.isoformat())
            .lte("fecha_accion", semana_fin.isoformat())
            .execute()
        )
        acts = acts_res.data or []

        # 🔹 Si no vemos "todo el equipo", filtramos por usuario
        if not ver_todo and trabajadorid:
            def visible(a):
                asignado = a.get("trabajador_asignadoid")
                creador = a.get("trabajador_creadorid")
                return (asignado == trabajadorid) or (asignado is None and creador == trabajadorid)

            acts = [a for a in acts if visible(a)]

        if not acts:
            return

        # ------------------------------------------------------
        # 4) Construir estadísticas por campaña
        # ------------------------------------------------------
        stats = {}
        trabajadores = set()

        for a in acts:
            camp_id = act_to_camp.get(a["crm_actuacionid"])
            if not camp_id:
                continue

            s = stats.setdefault(
                camp_id, {"total": 0, "completadas": 0, "pendientes": 0, "trab": set()}
            )

            s["total"] += 1

            estado = (a.get("crm_actuacion_estado") or {}).get("estado", "")
            if estado == "Completada":
                s["completadas"] += 1
            else:
                s["pendientes"] += 1

            # Registrar trabajadores implicados
            t1 = a.get("trabajador_creadorid")
            t2 = a.get("trabajador_asignadoid")

            if t1:
                s["trab"].add(t1)
                trabajadores.add(t1)
            if t2:
                s["trab"].add(t2)
                trabajadores.add(t2)

        # ------------------------------------------------------
        # 5) Cargar nombres de trabajadores para mostrar
        # ------------------------------------------------------
        trab_map = {}
        if trabajadores:
            rows = (
                supabase.table("trabajador")
                .select("trabajadorid, nombre, apellidos")
                .in_("trabajadorid", list(trabajadores))
                .execute()
                .data or []
            )
            trab_map = {
                r["trabajadorid"]: f"{r.get('nombre','')} {r.get('apellidos','')}".strip()
                for r in rows
            }

        # ------------------------------------------------------
        # 6) Render tarjetas
        # ------------------------------------------------------
        cont = ""

        camp_info = {c["campaniaid"]: c for c in campanias}

        for camp_id, s in stats.items():
            c = camp_info.get(camp_id)
            if not c:
                continue

            nombre = c["nombre"]
            tipo = c.get("tipo_accion") or "-"
            fi = c.get("fecha_inicio")
            ff = c.get("fecha_fin")

            fechas_txt = (
                f"{safe_date(fi)} → {safe_date(ff)}"
                if (fi and ff)
                else ("Desde " + safe_date(fi) if fi else "Sin fechas")
            )

            trabajadores_txt = ", ".join(
                trab_map.get(tid, f"Trabajador {tid}") for tid in s["trab"]
            ) or "Sin asignar"

            obj_total = c.get("objetivo_total") or "-"
            obj_diario = c.get("objetivo_diario") or "-"

            # -------- HTML tarjeta --------
            cont += f"""
            <div style="
                border-radius:10px;
                border:1px solid #e5e7eb;
                background:#f9fafb;
                padding:10px 12px;
                margin-right:12px;
                margin-bottom:8px;
                box-shadow:0 1px 2px rgba(10,10,10,.06);
                min-width:240px;
            ">
                <div style="font-size:14px;font-weight:600;color:#111827;">
                    📣 {nombre}
                </div>

                <div style="font-size:11px;color:#6b7280;margin-top:2px;margin-bottom:6px;">
                    <span style="
                        padding:2px 6px;
                        background:#dbeafe;
                        color:#1d4ed8;
                        border-radius:999px;
                        font-size:10px;
                    ">
                        {tipo}
                    </span>
                </div>

                <div style="font-size:11px;color:#4b5563;margin-bottom:4px;">
                    🗓️ {fechas_txt}
                </div>

                <div style="font-size:11px;color:#111827;margin-bottom:4px;">
                    ✅ {s['completadas']}  ·  ⏳ {s['pendientes']}  ·  Total {s['total']}
                </div>

                <div style="font-size:10px;color:#6b7280;margin-bottom:4px;">
                    🎯 Objetivo total: {obj_total} &nbsp;&nbsp;·&nbsp;&nbsp; 🗓 Obj/día: {obj_diario}
                </div>

                <div style="font-size:10px;color:#374151;">
                    👥 {trabajadores_txt}
                </div>
            </div>
            """

        if cont:
            st.markdown(
                """
                <div style="margin-top:4px;margin-bottom:10px;">
                    <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:6px;">
                        📣 Campañas activas con actuaciones esta semana
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                """
                + cont
                + "</div></div>",
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.caption(f"⚠️ No se pudieron cargar campañas: {e}")
