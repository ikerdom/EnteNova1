# modules/tarifa_lista.py
import streamlit as st
import pandas as pd
from datetime import date

# ======================================================
# 🧩 Helpers visuales
# ======================================================
def _pill(text):
    return f"<span style='padding:4px 8px;border-radius:999px;background:#eef2ff;border:1px solid #dbeafe;font-size:12px'>{text}</span>"

def _card(title, subtitle, kpis: list[str]):
    items = "".join([f"<li style='margin:2px 0'>{k}</li>" for k in kpis])
    return f"""
    <div style="border:1px solid #eee;border-radius:12px;padding:14px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,.05);background:#fff">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">{title}</div>
      <div style="color:#666;font-size:12px;margin-bottom:8px">{subtitle}</div>
      <ul style="padding-left:16px;margin:0">{items}</ul>
    </div>
    """

def _opts(supabase, table, idcol, namecol, ordercol=None):
    """Carga datos genéricos para selects (clientes, productos, grupos...)"""
    try:
        q = supabase.table(table).select(f"{idcol}, {namecol}")
        if ordercol:
            q = q.order(ordercol)
        return q.execute().data or []
    except Exception as e:
        st.error(f"Error cargando {table}: {e}")
        return []

# =========================================================
# 🏷️ Módulo principal: Lista de tarifas y promociones
# =========================================================
def render_tarifa_lista(supabase):
    st.header("🏷️ Tarifas y Reglas de Aplicación")
    st.caption("Visualiza las tarifas, sus reglas y promueve combinaciones a niveles superiores.")

    tabs = st.tabs(["📊 Resumen", "🧭 Jerarquías", "⚙️ Promociones"])

    # ======================================================
    # TAB 1 · RESUMEN
    # ======================================================
    with tabs[0]:
        st.subheader("📊 Resumen general de tarifas")
        try:
            data = supabase.table("vw_tarifa_resumen_slim").select("*").execute().data or []
        except Exception as e:
            st.error(f"Error cargando resumen: {e}")
            data = []

        if not data:
            st.info("No hay tarifas definidas todavía.")
        else:
            df = pd.DataFrame(data)
            filtro = st.text_input("🔍 Filtrar por nombre de tarifa...")
            if filtro:
                df = df[df["nombre_tarifa"].str.contains(filtro, case=False, na=False)]

            for _, row in df.iterrows():
                fecha_inicio = row.get("fecha_inicio", "—")
                fecha_fin = row.get("fecha_fin", "Sin fecha final")
                vigencia = f"Vigencia: {fecha_inicio} - {fecha_fin}"

                kpis = [
                    f"💸 Descuento: <b>{row.get('descuento_pct', 0):.0f}%</b>",
                    f"👤 Clientes vinculados: <b>{int(row.get('clientes_tarifa', 0))}</b>",
                    f"📦 Productos cliente: <b>{int(row.get('combos_prod_cli', 0))}</b>",
                    f"📚 Familias cliente: <b>{int(row.get('combos_fam_cli', 0))}</b>",
                    f"🏢 Grupos producto: <b>{int(row.get('combos_prod_grp', 0))}</b>",
                    f"🏷️ Familias grupo: <b>{int(row.get('combos_fam_grp', 0))}</b>",
                    _pill(f"Total combinaciones: {int(row.get('total_combos', 0))}")
                ]
                st.markdown(_card(row["nombre_tarifa"], vigencia, kpis), unsafe_allow_html=True)

    # ======================================================
    # TAB 2 · JERARQUÍAS
    # ======================================================
    with tabs[1]:
        st.subheader("🧭 Jerarquías por tarifa")

        try:
            tarifas = supabase.table("tarifa").select("tarifaid, nombre").order("tarifaid").execute().data or []
        except Exception as e:
            st.error(f"No pude cargar tarifas: {e}")
            tarifas = []

        nombres = [t["nombre"] for t in tarifas]
        nombre_sel = st.selectbox("Selecciona una tarifa", nombres or ["(sin tarifas)"])
        if nombre_sel not in nombres:
            st.stop()

        try:
            jer = (
                supabase.table("vw_tarifa_jerarquias")
                .select("*")
                .eq("nombre_tarifa", nombre_sel)
                .single()
                .execute()
                .data
            )
        except Exception:
            jer = None

        if not jer:
            st.info("Esta tarifa no tiene reglas asociadas.")
        else:
            st.markdown("### 📚 Estructura jerárquica de combinaciones")

            def _jer_card(icon, title, content, color):
                html = f"""
                <div style="border-left:4px solid {color};background:#fff;border-radius:8px;
                            padding:10px 14px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
                    <div style="font-weight:600;margin-bottom:4px;">{icon} {title}</div>
                    <div style="font-size:13px;color:#333;">{content if content else '—'}</div>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                _jer_card("📦", "Producto + Cliente", jer.get("producto_cliente"), "#4f46e5")
                _jer_card("🏢", "Producto + Grupo", jer.get("producto_grupo"), "#2563eb")
            with col2:
                _jer_card("📚", "Familia + Cliente", jer.get("familia_cliente"), "#16a34a")
                _jer_card("🏷️", "Familia + Grupo", jer.get("familia_grupo"), "#d97706")

            st.caption("Las tarjetas muestran las combinaciones activas de esta tarifa según su jerarquía.")

    # ======================================================
    # TAB 3 · PROMOCIONAR COMBINACIÓN
    # ======================================================
    with tabs[2]:
        st.subheader("⚙️ Promocionar combinación a tarifa superior")
        st.caption("Selecciona un cliente y producto que actualmente usan la **Tarifa General** y promociónalos a otra tarifa activa.")

        clientes = _opts(supabase, "cliente", "clienteid", "razonsocial", "razonsocial")
        prods = _opts(supabase, "producto", "productoid", "nombre", "nombre")
        tarifas = _opts(supabase, "tarifa", "tarifaid", "nombre", "tarifaid")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            cliente_nom = st.selectbox("👤 Cliente", ["(Selecciona)"] + [c["razonsocial"] for c in clientes])
        with col2:
            producto_nom = st.selectbox("📦 Producto", ["(Selecciona)"] + [p["nombre"] for p in prods])
        with col3:
            nueva_tarifa = st.selectbox("🏷️ Tarifa destino", ["(Selecciona)"] + [t["nombre"] for t in tarifas])

        colf1, colf2, colf3 = st.columns([1, 1, 1])
        with colf1:
            fd = st.date_input("Desde", value=date.today())
        with colf2:
            fh = st.date_input("Hasta (opcional)", value=None)
        with colf3:
            infinito = st.checkbox("📆 Sin caducidad", value=False)

        if infinito:
            fh = date(2999, 12, 31)

        if st.button("🚀 Promocionar combinación", width="stretch"):
            if "(Selecciona)" in (cliente_nom, producto_nom, nueva_tarifa):
                st.warning("⚠️ Selecciona cliente, producto y tarifa destino antes de continuar.")
            else:
                try:
                    clienteid = next(c["clienteid"] for c in clientes if c["razonsocial"] == cliente_nom)
                    productoid = next(p["productoid"] for p in prods if p["nombre"] == producto_nom)
                    tarifaid = next(t["tarifaid"] for t in tarifas if t["nombre"] == nueva_tarifa)

                    supabase.table("tarifa_regla").insert({
                        "tarifaid": tarifaid,
                        "clienteid": clienteid,
                        "productoid": productoid,
                        "fecha_inicio": fd.isoformat(),
                        "fecha_fin": fh.isoformat() if fh else None,
                        "prioridad": 1,
                        "habilitada": True
                    }).execute()

                    st.success(f"✅ Combinación '{cliente_nom} · {producto_nom}' promovida a **{nueva_tarifa}**.")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al promocionar: {e}")

        st.info("💡 Usa esta función para ascender combinaciones a tarifas específicas (por ejemplo, campañas especiales).")
