# =========================================================
# 💳 FORM · Datos de facturación y métodos de pago (versión pro)
# =========================================================
import streamlit as st

def _verificar_perfil_completo(supabase, clienteid):
    """Comprueba si el cliente tiene perfil completo (dirección, forma de pago, banco si aplica)."""
    try:
        dir_ok = bool(
            supabase.table("cliente_direccion")
            .select("cliente_direccionid")
            .eq("clienteid", clienteid)
            .eq("tipo", "fiscal")
            .neq("cp", "")
            .limit(1)
            .execute()
            .data
        )

        cliente = supabase.table("cliente").select("formapagoid").eq("clienteid", clienteid).single().execute().data
        fpagoid = cliente.get("formapagoid") if cliente else None

        fpago = (
            supabase.table("forma_pago").select("nombre").eq("formapagoid", fpagoid).single().execute().data
        )
        nombre_fp = (fpago or {}).get("nombre", "").lower()
        fpago_ok = bool(nombre_fp)

        banco_ok = True
        if any(p in nombre_fp for p in ["banco", "transferencia", "domiciliación"]):
            banco_ok = bool(
                supabase.table("cliente_banco").select("cliente_bancoid").eq("clienteid", clienteid).limit(1).execute().data
            )

        completo = dir_ok and fpago_ok and banco_ok
        supabase.table("cliente").update({"perfil_completo": completo}).eq("clienteid", clienteid).execute()
    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar perfil completo: {e}")


def render_facturacion_form(supabase, clienteid):
    """Formulario visual de facturación con estilo profesional."""
    st.markdown("### 💳 Facturación y métodos de pago")
    st.caption("Configura la forma de pago del cliente y los datos financieros asociados.")

    with st.expander("⚙️ Configuración general", expanded=True):
        try:
            formas = (
                supabase.table("forma_pago")
                .select("formapagoid, nombre")
                .eq("habilitado", True)
                .order("formapagoid")
                .execute()
            )
            opciones = {f["nombre"]: f["formapagoid"] for f in (formas.data or [])}
        except Exception as e:
            st.error(f"❌ Error cargando formas de pago: {e}")
            return

        formapago_actual_id = None
        try:
            cli = supabase.table("cliente").select("formapagoid").eq("clienteid", clienteid).limit(1).execute()
            if cli.data:
                formapago_actual_id = cli.data[0]["formapagoid"]
        except Exception:
            pass

        nombres = list(opciones.keys())
        default_index = 0
        if formapago_actual_id and formapago_actual_id in opciones.values():
            for i, n in enumerate(nombres):
                if opciones[n] == formapago_actual_id:
                    default_index = i
                    break

        forma_pago_nombre = st.selectbox("💰 Forma de pago", nombres, index=default_index, key=f"fp_nombre_{clienteid}")

    # ====================================================
    # 🏦 DATOS BANCARIOS
    # ====================================================
    campos_banco = any(p in forma_pago_nombre.lower() for p in ["transferencia", "domiciliación", "banco"])
    if campos_banco:
        st.markdown("---")
        st.markdown("#### 🏦 Datos bancarios")
        try:
            banco_res = supabase.table("cliente_banco").select("*").eq("clienteid", clienteid).limit(1).execute()
            row = banco_res.data[0] if banco_res.data else {}
        except Exception:
            row = {}

        with st.container():
            st.markdown(
                """
                <div style="padding:10px;background:#f0f9ff;border-radius:10px;margin-bottom:8px;">
                    💡 <b>Los datos bancarios son obligatorios</b> si el método de pago implica transferencia o domiciliación.
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                iban = st.text_input("IBAN", value=row.get("iban", ""), placeholder="ES12 3456 7890 1234 5678 9012")
                banco = st.text_input("Banco", value=row.get("banco", ""))
            with c2:
                sucursal = st.text_input("Sucursal", value=row.get("sucursal", ""))
                obs_banco = st.text_area("Observaciones bancarias", value=row.get("observaciones", ""))

    # ====================================================
    # 💳 DATOS TARJETA
    # ====================================================
    campos_tarjeta = "tarjeta" in forma_pago_nombre.lower()
    if campos_tarjeta:
        st.markdown("---")
        st.markdown("#### 💳 Datos de tarjeta")
        try:
            t_res = supabase.table("cliente_tarjeta").select("*").eq("clienteid", clienteid).limit(1).execute()
            row = t_res.data[0] if t_res.data else {}
        except Exception:
            row = {}

        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                numero_tarjeta = st.text_input("Número de tarjeta", value=row.get("numero_tarjeta", ""), placeholder="1111 2222 3333 4444")
                caducidad = st.text_input("Caducidad (MM/AA)", value=row.get("caducidad", ""), placeholder="12/27")
            with c2:
                cvv = st.text_input("CVV", type="password", value=row.get("cvv", ""), placeholder="123")
                titular = st.text_input("Titular", value=row.get("titular", ""))

    # ====================================================
    # 💾 GUARDAR CONFIGURACIÓN
    # ====================================================
    st.markdown("---")
    if st.button("💾 Guardar configuración de facturación", use_container_width=True):
        try:
            supabase.rpc("safe_update_cliente", {
                "p_clienteid": clienteid,
                "p_formapagoid": opciones[forma_pago_nombre]
            }).execute()

            # Guardar datos según tipo de forma de pago
            if campos_banco:
                if not iban.strip():
                    st.warning("⚠️ IBAN obligatorio para pagos bancarios.")
                    return
                data_banco = {
                    "clienteid": clienteid,
                    "iban": iban.strip(),
                    "banco": banco.strip(),
                    "sucursal": sucursal.strip(),
                    "observaciones": obs_banco.strip(),
                }
                supabase.table("cliente_banco").upsert(data_banco, on_conflict="clienteid").execute()

            elif campos_tarjeta:
                if not all([numero_tarjeta.strip(), caducidad.strip(), cvv.strip(), titular.strip()]):
                    st.warning("⚠️ Todos los datos de la tarjeta son obligatorios.")
                    return
                supabase.table("cliente_tarjeta").upsert({
                    "clienteid": clienteid,
                    "numero_tarjeta": numero_tarjeta.strip(),
                    "caducidad": caducidad.strip(),
                    "cvv": cvv.strip(),
                    "titular": titular.strip(),
                }, on_conflict="clienteid").execute()

            st.toast("✅ Configuración de facturación guardada correctamente.", icon="✅")
            _verificar_perfil_completo(supabase, clienteid)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")