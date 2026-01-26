# ======================================================
# 📦 PRODUCTO · Formulario de alta / edición (Orbe UI)
# ======================================================
import streamlit as st
from datetime import date

from modules.ui.section import section
from modules.producto_models import (
    load_familias,
    load_tipos_producto,
    load_impuestos,
    load_estados_producto,
)


def render_producto_form(supabase, productoid=None, on_saved_rerun=True):
    modo_titulo = "✏️ Editar producto" if productoid else "➕ Nuevo producto"
    modo_caption = (
        "Modifica la información del producto existente."
        if productoid
        else "Crea un nuevo producto en el catálogo."
    )

    with section("Producto", icon="📦"):
        st.markdown(f"#### {modo_titulo}")
        st.caption(modo_caption)

        # ---------------------------
        # Catálogos
        # ---------------------------
        familias = load_familias(supabase)
        tipos = load_tipos_producto(supabase)
        impuestos = load_impuestos(supabase)
        estados = load_estados_producto(supabase)

        producto = {}
        if productoid:
            try:
                r = (
                    supabase.table("producto")
                    .select("*")
                    .eq("productoid", productoid)
                    .single()
                    .execute()
                )
                producto = r.data or {}
            except Exception as e:
                st.error(f"❌ Error cargando producto: {e}")
                return

        # ---------------------------
        # FORMULARIO
        # ---------------------------
        with st.form(f"form_producto_{productoid or 'new'}"):

            # =================================================
            # 🧱 IDENTIDAD
            # =================================================
            st.markdown("### 🧱 Identidad del producto")
            c1, c2 = st.columns(2)

            with c1:
                nombre = st.text_input("Nombre *", producto.get("nombre", ""))
                referencia = st.text_input(
                    "Referencia / SKU", producto.get("referencia", "")
                )
                isbn = st.text_input("ISBN", producto.get("isbn", ""))
                ean = st.text_input("EAN", producto.get("ean", ""))

            with c2:
                titulo = st.text_input(
                    "Título / nombre comercial", producto.get("titulo", "")
                )
                tipo_txt = st.text_input(
                    "Tipo (texto libre)", producto.get("tipo", "")
                )
                versatilidad = st.text_input(
                    "Versatilidad", producto.get("versatilidad", "")
                )

            # =================================================
            # 💶 COMERCIAL / PUBLICACIÓN
            # =================================================
            st.markdown("### 💶 Comercial y publicación")
            c3, c4 = st.columns(2)

            with c3:
                precio = st.number_input(
                    "Precio genérico (€)",
                    min_value=0.0,
                    step=0.01,
                    value=float(producto.get("precio_generico", 0.0)),
                )
                publico = st.checkbox(
                    "Visible al público",
                    value=bool(producto.get("publico", True)),
                )

            with c4:
                fecha_pub = st.date_input(
                    "Fecha de publicación",
                    value=date.fromisoformat(producto["fecha_publicacion"])
                    if producto.get("fecha_publicacion")
                    else date.today(),
                )
                portada_url = st.text_input(
                    "URL portada", producto.get("portada_url", "")
                )

            # =================================================
            # 📝 DESCRIPCIÓN
            # =================================================
            st.markdown("### 📝 Descripción")
            sinopsis = st.text_area(
                "Sinopsis / descripción",
                producto.get("sinopsis", ""),
                height=120,
            )

            # =================================================
            # 🏷️ CLASIFICACIÓN
            # =================================================
            st.markdown("### 🏷️ Clasificación")
            cA, cB, cC, cD = st.columns(4)

            prefill_fid = None
            if not productoid:
                prefill_fid = st.session_state.get("prefill_familia_productoid")

            familia_val = producto.get("familia_productoid") or prefill_fid

            with cA:
                familia_sel = st.selectbox(
                    "Familia",
                    ["(sin familia)"] + list(familias.keys()),
                    index=_sel_idx(familias, familia_val),
                )

            with cB:
                tipo_sel = st.selectbox(
                    "Tipo de producto",
                    ["(sin tipo)"] + list(tipos.keys()),
                    index=_sel_idx(tipos, producto.get("producto_tipoid")),
                )

            with cC:
                imp_sel = st.selectbox(
                    "Impuesto",
                    ["(sin impuesto)"] + list(impuestos.keys()),
                    index=_sel_idx(impuestos, producto.get("impuestoid")),
                )

            with cD:
                est_sel = st.selectbox(
                    "Estado",
                    ["(sin estado)"] + list(estados.keys()),
                    index=_sel_idx(estados, producto.get("estado_productoid")),
                )

            # =================================================
            # 💾 GUARDAR
            # =================================================
            guardar = st.form_submit_button(
                "💾 Guardar producto", use_container_width=True
            )

        # ---------------------------
        # SUBMIT
        # ---------------------------
        if guardar:
            if not nombre.strip():
                st.warning("⚠️ El nombre del producto es obligatorio.")
                return

            payload = {
                "nombre": nombre.strip(),
                "titulo": titulo.strip() or None,
                "referencia": referencia.strip() or None,
                "isbn": isbn.strip() or None,
                "ean": ean.strip() or None,
                "precio_generico": float(precio),
                "publico": publico,
                "tipo": tipo_txt.strip() or None,
                "versatilidad": versatilidad.strip() or None,
                "fecha_publicacion": fecha_pub.isoformat(),
                "portada_url": portada_url.strip() or None,
                "sinopsis": sinopsis.strip() or None,
                "familia_productoid": familias.get(familia_sel),
                "producto_tipoid": tipos.get(tipo_sel),
                "impuestoid": impuestos.get(imp_sel),
                "estado_productoid": estados.get(est_sel),
            }

            try:
                if productoid:
                    supabase.table("producto").update(payload).eq(
                        "productoid", productoid
                    ).execute()
                    st.toast("✅ Producto actualizado correctamente.", icon="✅")
                else:
                    res = supabase.table("producto").insert(payload).execute()
                    nuevo_id = res.data[0]["productoid"] if res.data else None
                    st.toast(
                        f"✅ Producto creado correctamente (ID {nuevo_id}).",
                        icon="✅",
                    )

                if "prefill_familia_productoid" in st.session_state:
                    del st.session_state["prefill_familia_productoid"]

                if on_saved_rerun:
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Error guardando producto: {e}")


def _sel_idx(d, val):
    for i, (_, v) in enumerate(d.items()):
        if v == val:
            return i + 1
    return 0
