# modules/dashboard_general.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import requests

from modules.orbe_palette import PRIMARY, SUCCESS, WARNING, DANGER, SECONDARY

# ==== Importaciones nuevas y correctas ====
from modules.dashboard.utils import (
    safe_date,
    contar_registros,
)
from modules.dashboard.actuacion_card import render_actuacion_card
from modules.dashboard.actuacion_form import render_actuacion_form
from modules.dashboard.campaign_strip import render_campaign_strip
from modules.dashboard.incidencias_block import render_incidencias_blocks
from modules.crm_api import listar as api_listar, actualizar as api_actualizar
from modules.pipeline_albaranes import can_run_today, run_pipeline, tail_log


def _api_base():
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def _table_exists(supabase, table: str) -> bool:
    try:
        supabase.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _get_crm_estado_id(supabase, estado: str):
    try:
        row = (
            supabase.table("crm_actuacion_estado")
            .select("crm_actuacion_estadoid, estado")
            .eq("estado", estado)
            .single()
            .execute()
            .data
        )
        return row.get("crm_actuacion_estadoid") if row else None
    except Exception:
        return None


def _get_incidencia_estado_id(supabase, estado: str):
    try:
        row = (
            supabase.table("incidencia_estado")
            .select("incidencia_estadoid, estado")
            .eq("estado", estado)
            .single()
            .execute()
            .data
        )
        return row.get("incidencia_estadoid") if row else None
    except Exception:
        return None

def _count_api_presupuestos():
    try:
        r = requests.get(f"{_api_base()}/api/presupuestos", params={"page": 1, "page_size": 1}, timeout=15)
        r.raise_for_status()
        return r.json().get("total", 0)
    except Exception:
        return "-"


def _count_api_pedidos_activos():
    try:
        r = requests.get(
            f"{_api_base()}/api/pedidos",
            params={"page": 1, "page_size": 1, "estadoid": 2},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("total", 0)
    except Exception:
        return "-"


def _count_api_crm_pendientes(trabajadorid: int | None):
    try:
        params = {"estado": "Pendiente"}
        if trabajadorid:
            params["trabajador_asignadoid"] = trabajadorid
        r = requests.get(f"{_api_base()}/api/crm/acciones", params=params, timeout=15)
        r.raise_for_status()
        return len(r.json().get("data", []))
    except Exception:
        return "-"


def _load_activity_api(fecha_inicio_30: date):
    """
    Fallback de actividad cuando no hay supabase: usa las APIs públicas.
    """
    base = _api_base()
    try:
        # Pedidos (filtramos por fecha_desde disponible en API)
        r_ped = requests.get(
            f"{base}/api/pedidos",
            params={"fecha_desde": fecha_inicio_30.isoformat(), "page": 1, "page_size": 500},
            timeout=20,
        )
        r_ped.raise_for_status()
        ped = r_ped.json().get("data", [])
    except Exception:
        ped = []

    try:
        r_pres = requests.get(f"{base}/api/presupuestos", params={"page": 1, "page_size": 500, "ordenar_por": "creado_en"}, timeout=20)
        r_pres.raise_for_status()
        pres = [
            p for p in r_pres.json().get("data", [])
            if (p.get("fecha_presupuesto") or "") >= fecha_inicio_30.isoformat()
        ]
    except Exception:
        pres = []

    try:
        r_acts = requests.get(f"{base}/api/crm/acciones", timeout=20)
        r_acts.raise_for_status()
        acts = [
            a for a in r_acts.json().get("data", [])
            if (a.get("fecha_accion") or "")[:10] >= fecha_inicio_30.isoformat()
        ]
    except Exception:
        acts = []

    return ped, pres, acts


def _load_albaranes_last_days(supabase, days: int = 7) -> pd.DataFrame:
    if not supabase or not _table_exists(supabase, "albaran"):
        return pd.DataFrame()
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    try:
        res = (
            supabase.table("albaran")
            .select("fecha_albaran")
            .gte("fecha_albaran", start)
            .order("fecha_albaran")
            .execute()
        )
        rows = res.data or []
    except Exception:
        return pd.DataFrame()

    counts: dict[str, int] = {}
    for r in rows:
        raw = r.get("fecha_albaran")
        if not raw:
            continue
        day = str(raw)[:10]
        counts[day] = counts.get(day, 0) + 1

    days_list = [(date.today() - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    data = {"fecha": days_list, "albaranes": [counts.get(d, 0) for d in days_list]}
    return pd.DataFrame(data)


# ======================================================
# 🔧 KPI CARD
# ======================================================
def _kpi_card(title: str, value: str, subtitle: str = "", color: str = PRIMARY):
    st.markdown(
        f"""
        <div style="
            border-radius: 14px;
            padding: 12px 14px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 4px rgba(15,23,42,.06);
            display:flex;
            flex-direction:column;
            gap:4px;
            height:100%;
        ">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#6b7280;">
            {title}
          </div>
          <div style="font-size:26px;font-weight:700;color:#111827;">
            {value}
          </div>
          <div style="font-size:12px;color:#6b7280;">
            {subtitle}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ======================================================
# 📊 DASHBOARD PRINCIPAL
# ======================================================
def render_dashboard(supabase):

    # ------------------------------------------------------
    # 🧱 ENCABEZADO
    # ------------------------------------------------------
    st.markdown(
        f"""
        <div style='background:#ecfdf5;padding:18px 20px;border-radius:12px;
                    border-left:6px solid {PRIMARY};margin-bottom:18px;'>
            <h2 style='margin:0;color:#065f46;'>📊 Panel General — EnteNova Gnosis · Orbe</h2>
            <p style='color:#166534;margin-top:4px;'>Resumen comercial, CRM y actividad.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------
    # ALBARANES PIPELINE
    # ------------------------------------------------------
    can_run, last_run = can_run_today()
    st.markdown("### Albaranes: refresco diario")
    if last_run:
        st.caption(f"Ultima ejecucion: {last_run.isoformat()}")
    if not can_run:
        st.info("Ya se ha ejecutado hoy.")

    if st.button("Refrescar albaranes", disabled=not can_run):
        with st.spinner("Ejecutando refresco..."):
            ok, msg = run_pipeline()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

        log_tail = tail_log()
        if log_tail:
            st.code(log_tail)

    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")

    ver_todo = st.toggle("👀 Ver todo el equipo", False)
    st.caption(
        f"Bienvenido, **{user}** — "
        f"mostrando datos de {'todo el equipo' if ver_todo else 'tu actividad personal'}."
    )

    hoy = date.today()
    fecha_inicio_30 = (datetime.now() - timedelta(days=30)).date()

    # ------------------------------------------------------
    # ESTADO UI
    # ------------------------------------------------------
    st.session_state.setdefault("dash_week_offset", 0)
    st.session_state.setdefault("crm_actuacion_detalle_id", None)
    st.session_state.setdefault("crm_new_act_fecha", None)

    st.markdown("---")

    # ------------------------------------------------------
    # 1️⃣ KPIs
    # ------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if supabase is None or not _table_exists(supabase, "presupuesto"):
            pres_count = _count_api_presupuestos()
        else:
            pres_count = contar_registros(supabase, "presupuesto")
        _kpi_card("Presupuestos", pres_count)
    with c2:
        if supabase is None or not _table_exists(supabase, "pedido"):
            ped_activos = _count_api_pedidos_activos()
        else:
            ped_activos = contar_registros(supabase, "pedido", {"estado_pedidoid": 2})
        _kpi_card("Pedidos activos", ped_activos, color=SUCCESS)
    with c3:
        if supabase is None or not _table_exists(supabase, "crm_actuacion"):
            crm_pend = _count_api_crm_pendientes(trabajadorid)
        else:
            est_id = _get_crm_estado_id(supabase, "Pendiente")
            crm_pend = (
                contar_registros(supabase, "crm_actuacion", {"crm_actuacion_estadoid": est_id})
                if est_id
                else "-"
            )
        _kpi_card("Acciones CRM pendientes", crm_pend, color=WARNING)
    with c4:
        if supabase and _table_exists(supabase, "incidencia"):
            inc_estado_id = _get_incidencia_estado_id(supabase, "Abierta")
            incs = (
                contar_registros(supabase, "incidencia", {"incidencia_estadoid": inc_estado_id})
                if inc_estado_id
                else "-"
            )
        else:
            incs = "-"
        _kpi_card("Incidencias abiertas", incs, color=DANGER)

    st.markdown("---")

    # ------------------------------------------------------
    # ------------------------------------------------------
    # TIRA DE CAMPA?AS / ALBARANES
    # ------------------------------------------------------
    semana_ini = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=st.session_state["dash_week_offset"])
    semana_fin = semana_ini + timedelta(days=6)

    if supabase and _table_exists(supabase, "campania"):
        render_campaign_strip(
            supabase,
            semana_ini=semana_ini,
            semana_fin=semana_fin,
            trabajadorid=trabajadorid,
            ver_todo=ver_todo,
        )
    else:
        st.subheader("Albaranes (ultimos 7 dias)")
        df_alb = _load_albaranes_last_days(supabase, days=7)
        if df_alb.empty:
            st.info("No hay datos de albaranes recientes.")
        else:
            st.line_chart(df_alb.set_index("fecha"))

    st.markdown("---")

    # ------------------------------------------------------
    # 2️⃣ CALENDARIO CRM
    # ------------------------------------------------------
    st.subheader("🗓️ Calendario semanal CRM")

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("◀️ Semana anterior"):
            st.session_state["dash_week_offset"] -= 1
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
    with nav3:
        if st.button("Semana siguiente ▶️"):
            st.session_state["dash_week_offset"] += 1
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
    with nav2:
        if st.button("🔄 Semana actual"):
            st.session_state["dash_week_offset"] = 0
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None

    # Fechas reales de la semana
    semana_ini = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=st.session_state["dash_week_offset"])
    semana_fin = semana_ini + timedelta(days=6)
    days = [semana_ini + timedelta(days=i) for i in range(7)]

    st.caption(f"Semana: **{semana_ini.strftime('%d/%m')} — {semana_fin.strftime('%d/%m')}**")

    # ------------------------------------------------------
    # Cargar actuaciones
    # ------------------------------------------------------
    acts = []
    try:
        if supabase:
            q = (
                supabase.table("crm_actuacion")
                .select(
                    "crm_actuacionid, descripcion, fecha_vencimiento, fecha_accion, "
                    "clienteid, trabajador_creadorid, trabajador_asignadoid, titulo, "
                    "hora_inicio, hora_fin, duracion_segundos, "
                    "crm_actuacion_estado(estado)"
                )
                .gte("fecha_vencimiento", semana_ini.isoformat())
                .lte("fecha_vencimiento", semana_fin.isoformat())
                .order("fecha_vencimiento")
            )
            acts_data = q.execute().data or []
        else:
            payload = {
                "trabajador_asignadoid": trabajadorid,
                "estado": None,
                "buscar": None,
            }
            acts_data = api_listar(payload).get("data", [])
            acts_data = [
                a
                for a in acts_data
                if semana_ini.isoformat() <= (a.get("fecha_vencimiento") or "")[:10] <= semana_fin.isoformat()
            ]

        if not ver_todo and trabajadorid:
            def visible(a):
                return (
                    a.get("trabajador_asignadoid") == trabajadorid
                    or (a.get("trabajador_asignadoid") is None and a.get("trabajador_creadorid") == trabajadorid)
                )
            acts = [a for a in acts_data if visible(a)]
        else:
            acts = acts_data
    except Exception as e:
        st.error(f"No se pudieron cargar las actuaciones: {e}")
        acts = []

    # ------------------------------------------------------
    # Cargar nombres de clientes
    # ------------------------------------------------------
    clientes_map = {}
    try:
        if supabase:
            ids = {a["clienteid"] for a in acts if a.get("clienteid")}
            if ids:
                rows = (
                    supabase.table("cliente")
                    .select("clienteid, razonsocial, nombre")
                    .in_("clienteid", list(ids))
                    .execute()
                    .data
                )
                clientes_map = {
                    r["clienteid"]: (r.get("razonsocial") or r.get("nombre") or "-")
                    for r in rows
                }
        else:
            clientes_map = {}
    except Exception:
        clientes_map = {}

    # ------------------------------------------------------
    # Diseño: calendario + panel lateral
    # ------------------------------------------------------
    col_cal, col_side = st.columns([4, 1])

    # -------- LATERAL --------
    with col_side:
        st.markdown("### 👤 Resumen semanal")
        if not acts:
            st.caption("Sin actuaciones.")
        else:
            total = len(acts)
            por_estado = {}
            for a in acts:
                est = (a.get("crm_actuacion_estado") or {}).get("estado") or "-"
                por_estado[est] = por_estado.get(est, 0) + 1

            st.write(f"**Total:** {total}")
            for est, n in por_estado.items():
                st.write(f"- **{est}**: {n}")

    # -------- CALENDARIO --------
    with col_cal:
        wd = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        cols = st.columns(7)

        for i, d in enumerate(days):
            with cols[i]:
                st.markdown(f"### {wd[i]} {d.strftime('%d/%m')}")
                daily = [a for a in acts if (a.get("fecha_vencimiento") or "")[:10] == d.isoformat()]

                if not daily:
                    st.caption("Sin acciones.")

                for a in daily:
                    cliente = clientes_map.get(a.get("clienteid"), "Sin cliente")
                    clicked_view, clicked_complete = render_actuacion_card(a, cliente)

                    if clicked_view:
                        st.session_state["crm_actuacion_detalle_id"] = a["crm_actuacionid"]
                        st.session_state["crm_new_act_fecha"] = None
                        st.rerun()

                    if clicked_complete:
                        try:
                            if supabase:
                                estado_id = _get_crm_estado_id(supabase, "Completada")
                                payload = {"fecha_accion": date.today().isoformat()}
                                if estado_id:
                                    payload["crm_actuacion_estadoid"] = estado_id
                                supabase.table("crm_actuacion").update(payload).eq(
                                    "crm_actuacionid", a["crm_actuacionid"]
                                ).execute()
                            else:
                                api_actualizar(
                                    a["crm_actuacionid"],
                                    {"estado": "Completada", "fecha_accion": date.today().isoformat()},
                                )
                            st.success("Actuación completada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al completar: {e}")

                # Crear nueva actuación
                if st.button("Nueva acción", key=f"new_{i}"):
                    st.session_state["crm_new_act_fecha"] = d.isoformat()
                    st.session_state["crm_actuacion_detalle_id"] = None
                    st.rerun()

    # ------------------------------------------------------
    # PANEL DE DETALLE/ALTA (parte inferior)
    # ------------------------------------------------------
    act_det = None
    if st.session_state["crm_actuacion_detalle_id"]:
        act_det = next(
            (x for x in acts if x["crm_actuacionid"] == st.session_state["crm_actuacion_detalle_id"]),
            None,
        )

    fecha_default = None
    if st.session_state["crm_new_act_fecha"]:
        try:
            fecha_default = date.fromisoformat(st.session_state["crm_new_act_fecha"])
        except:
            fecha_default = date.today()

    if act_det or fecha_default:
        render_actuacion_form(supabase, act_det, fecha_default)

    st.markdown("---")

    # ------------------------------------------------------
    # 3️⃣ ACTIVIDAD · GRÁFICAS
    # ------------------------------------------------------
    st.subheader("📈 Actividad comercial (últimos 30 días)")
    colA, colB = st.columns(2)

    # -------- Gráficas principales --------
    with colA:
        try:
            if supabase and _table_exists(supabase, "pedido") and _table_exists(supabase, "presupuesto"):
                ped = (
                    supabase.table("pedido")
                    .select("fecha_pedido")
                    .gte("fecha_pedido", fecha_inicio_30.isoformat())
                    .execute()
                    .data
                    or []
                )
                pres = (
                    supabase.table("presupuesto")
                    .select("fecha_presupuesto")
                    .gte("fecha_presupuesto", fecha_inicio_30.isoformat())
                    .execute()
                    .data
                    or []
                )
                act_estado_id = _get_crm_estado_id(supabase, "Completada")
                act_query = (
                    supabase.table("crm_actuacion")
                    .select("fecha_accion, crm_actuacion_estado(estado)")
                    .gte("fecha_accion", fecha_inicio_30.isoformat())
                )
                if act_estado_id:
                    act_query = act_query.eq("crm_actuacion_estadoid", act_estado_id)
                acts30 = act_query.execute().data or []
            else:
                ped, pres, acts30 = _load_activity_api(fecha_inicio_30)

            records = []
            for p in ped or []:
                fecha = p.get("fecha_pedido")
                if fecha:
                    records.append({"fecha": pd.to_datetime(fecha).date(), "tipo": "Pedidos"})
            for p in pres or []:
                fecha = p.get("fecha_presupuesto")
                if fecha:
                    records.append({"fecha": pd.to_datetime(fecha).date(), "tipo": "Presupuestos"})
            for a in acts30 or []:
                fecha = a.get("fecha_accion")
                if fecha:
                    records.append({"fecha": pd.to_datetime(fecha).date(), "tipo": "Acciones CRM"})

            df_all = pd.DataFrame(records)

            st.markdown("### Resumen 30 dias")
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Pedidos", len([r for r in records if r["tipo"] == "Pedidos"]))
            with m2:
                st.metric("Presupuestos", len([r for r in records if r["tipo"] == "Presupuestos"]))
            with m3:
                st.metric("Acciones CRM", len([r for r in records if r["tipo"] == "Acciones CRM"]))

            if df_all.empty:
                st.info("No hay actividad reciente.")
            else:
                df_chart = df_all.groupby(["fecha", "tipo"]).size().unstack(fill_value=0)
                st.line_chart(df_chart, use_container_width=True)

        except Exception as e:
            st.error(f"Error gráfico: {e}")

        # Gráfico estados CRM
        st.markdown("### 🎯 Estado de acciones CRM (últimos 30 días)")
        try:
            if supabase and _table_exists(supabase, "crm_actuacion"):
                rows = (
                    supabase.table("crm_actuacion")
                    .select("crm_actuacion_estado(estado)")
                    .gte("fecha_accion", fecha_inicio_30.isoformat())
                    .execute()
                    .data
                )
            else:
                rows = [{"estado": a.get("estado")} for a in acts30 if a.get("estado")]
            df_est = pd.DataFrame(rows)
            if df_est.empty:
                st.caption("Sin acciones CRM.")
            else:
                if "crm_actuacion_estado" in df_est.columns:
                    df_est["estado"] = df_est["crm_actuacion_estado"].apply(
                        lambda r: (r or {}).get("estado")
                    )
                df_cnt = df_est["estado"].value_counts()
                st.bar_chart(df_cnt)
        except:
            st.caption("Error cargando datos.")

        # ---- Presupuestos -> Pedidos ----
        st.markdown("### Presupuestos convertidos en pedidos")
        try:
            if not (supabase and _table_exists(supabase, "pedido") and _table_exists(supabase, "presupuesto")):
                st.info("Sin datos de pedidos/presupuestos en este entorno.")
            else:
                ped_conv = (
                    supabase.table("pedido")
                    .select("pedidoid, numero, fecha_pedido, presupuesto_origenid, clienteid")
                    .gte("fecha_pedido", fecha_inicio_30.isoformat())
                    .execute()
                    .data
                )

                ped_conv = [p for p in ped_conv if p.get("presupuesto_origenid")]

                if not ped_conv:
                    st.caption("Sin conversiones.")
                else:
                    pres_ids = list({p["presupuesto_origenid"] for p in ped_conv})
                    pres_rows = (
                        supabase.table("presupuesto")
                        .select("presupuestoid, numero, clienteid")
                        .in_("presupuestoid", pres_ids)
                        .execute()
                        .data
                    )
                    pres_map = {r["presupuestoid"]: r["numero"] for r in pres_rows}

                    cli_ids = list({p["clienteid"] for p in ped_conv})
                    cli_rows = (
                        supabase.table("cliente")
                        .select("clienteid, razonsocial, nombre")
                        .in_("clienteid", cli_ids)
                        .execute()
                        .data
                    )
                    cli_map = {
                        c["clienteid"]: (c.get("razonsocial") or c.get("nombre") or "-")
                        for c in cli_rows
                    }

                    for p in ped_conv[:5]:
                        st.markdown(
                            f"**Pedido {p['numero']}** -> presupuesto {pres_map.get(p['presupuesto_origenid'],'-')} - {cli_map.get(p['clienteid'],'-')}"
                        )

        except Exception as e:
            st.error(f"Error en conversiones: {e}")
            st.error(f"Error en conversiones: {e}")

    # -------- INCIDENCIAS --------
    with colB:
        render_incidencias_blocks(supabase, trabajadorid)

    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe — Dashboard comercial y CRM")

