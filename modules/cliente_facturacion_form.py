# =========================================================
# 💳 FORM · Datos de facturación y métodos de pago (API)
# =========================================================

import requests
import streamlit as st

from modules.api_base import get_api_base


def _api_get(path: str, params: dict | None = None):
    r = requests.get(f"{get_api_base()}{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _api_post(path: str, payload: dict):
    r = requests.post(f"{get_api_base()}{path}", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def render_facturacion_form(_supabase_unused, clienteid):
    """Formulario visual de facturación con estilo profesional (vía API)."""
    st.markdown("### 💳 Facturación y métodos de pago")
    st.caption("Configura la forma de pago del cliente y los datos financieros asociados.")

    try:
        formas = _api_get("/api/clientes/facturacion/catalogos")
    except Exception as e:
        st.error(f"❌ Error cargando formas de pago: {e}")
        return

    opciones = {f.get("nombre"): f.get("formapagoid") for f in (formas or []) if f.get("formapagoid")}
    nombres = list(opciones.keys()) or ["(sin formas de pago)"]

    try:
        fact = _api_get(f"/api/clientes/{clienteid}/facturacion")
    except Exception:
        fact = {}

    formapago_actual_id = fact.get("formapagoid")
    banco_row = fact.get("banco") or {}
    tarjeta_row = fact.get("tarjeta") or {}

    with st.expander("⚙️ Configuración general", expanded=True):
        default_index = 0
        if formapago_actual_id and formapago_actual_id in opciones.values():
            for i, n in enumerate(nombres):
                if opciones.get(n) == formapago_actual_id:
                    default_index = i
                    break

        forma_pago_nombre = st.selectbox("💰 Forma de pago", nombres, index=default_index, key=f"fp_nombre_{clienteid}")

    campos_banco = any(p in (forma_pago_nombre or "").lower() for p in ["transferencia", "domiciliación", "domiciliacion", "banco"])
    campos_tarjeta = "tarjeta" in (forma_pago_nombre or "").lower()

    iban = banco = sucursal = obs_banco = ""
    if campos_banco:
        st.markdown("---")
        st.markdown("#### 🏦 Datos bancarios")
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
                iban = st.text_input("IBAN", value=banco_row.get("iban", ""), placeholder="ES12 3456 7890 1234 5678 9012")
                banco = st.text_input("Banco", value=banco_row.get("banco", ""))
            with c2:
                sucursal = st.text_input("Sucursal", value=banco_row.get("sucursal", ""))
                obs_banco = st.text_area("Observaciones bancarias", value=banco_row.get("observaciones", ""))

    numero_tarjeta = caducidad = cvv = titular = ""
    if campos_tarjeta:
        st.markdown("---")
        st.markdown("#### 💳 Datos de tarjeta")
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                numero_tarjeta = st.text_input("Número de tarjeta", value=tarjeta_row.get("numero_tarjeta", ""), placeholder="1111 2222 3333 4444")
                caducidad = st.text_input("Caducidad (MM/AA)", value=tarjeta_row.get("caducidad", ""), placeholder="12/27")
            with c2:
                cvv = st.text_input("CVV", type="password", value=tarjeta_row.get("cvv", ""), placeholder="123")
                titular = st.text_input("Titular", value=tarjeta_row.get("titular", ""))

    st.markdown("---")
    if st.button("💾 Guardar configuración de facturación", width="stretch"):
        if campos_banco and not iban.strip():
            st.warning("⚠️ IBAN obligatorio para pagos bancarios.")
            return
        if campos_tarjeta and not all([numero_tarjeta.strip(), caducidad.strip(), cvv.strip(), titular.strip()]):
            st.warning("⚠️ Todos los datos de la tarjeta son obligatorios.")
            return

        payload = {"formapagoid": opciones.get(forma_pago_nombre)}
        if campos_banco:
            payload["banco"] = {
                "iban": iban.strip(),
                "banco": banco.strip(),
                "sucursal": sucursal.strip(),
                "observaciones": obs_banco.strip(),
            }
        if campos_tarjeta:
            payload["tarjeta"] = {
                "numero_tarjeta": numero_tarjeta.strip(),
                "caducidad": caducidad.strip(),
                "cvv": cvv.strip(),
                "titular": titular.strip(),
            }

        try:
            _api_post(f"/api/clientes/{clienteid}/facturacion", payload)
            st.toast("✅ Configuración de facturación guardada correctamente.", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")
