# modules/presupuesto_pdf.py
import io
import os
import base64
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet

from modules.presupuesto_context import build_presupuesto_context

BUCKET_DEFAULT = "presupuestos"


# =========================================================
# Helpers
# =========================================================
def _money(v):
    try:
        return f"{float(v):,.2f} €"
    except Exception:
        return "-"


def _safe(v, default="-"):
    return v if v not in (None, "", "null") else default


def _bold(text: str) -> str:
    return f"<b>{text}</b>"


def _fmt_fecha_ddmmaaaa(fecha_val):
    """
    Recibe:
      - string ISO (2025-11-11)
      - datetime
      - date
      - string dd/mm/aaaa
    y devuelve dd/mm/aaaa si puede.
    """
    if not fecha_val:
        return "-"
    # Ya viene en formato dd/mm/aaaa
    if isinstance(fecha_val, str) and "/" in fecha_val:
        return fecha_val
    try:
        if isinstance(fecha_val, datetime):
            d = fecha_val.date()
        else:
            d = datetime.fromisoformat(str(fecha_val)).date()
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(fecha_val)


def _build_data_real(supabase, presupuestoid: int) -> dict:
    """
    Construye el data_real FINAL a partir del contexto unificado del presupuesto.
    Este data_real es el que consume build_pdf_bytes().
    """
    ctx = build_presupuesto_context(supabase, presupuestoid)

    empresa = ctx.get("empresa", {}) or {}
    cli_ctx = ctx.get("cliente", {}) or {}
    pres = ctx.get("presupuesto", {}) or {}
    tot = ctx.get("totales", {}) or {}

    dir_fiscal = ctx.get("direccion_fiscal") or {}
    dir_envio = ctx.get("direccion_envio") or {}

    # ---------------------------------------------
    # USAR DIRECTAMENTE LAS LÍNEAS DEL CONTEXTO
    # ---------------------------------------------
    lineas_pdf = []
    for item in ctx.get("lineas", []):
        # item YA contiene los campos correctos
        lineas_pdf.append(
            {
                "concepto": item.get("concepto"),
                "unidades": item.get("unidades"),
                "precio": item.get("precio"),
                "dto": item.get("dto"),
                "iva": item.get("iva"),
                "base": item.get("base"),
                "total": item.get("total"),
            }
        )

    data_real = {
        "empresa": empresa,
        "cliente": cli_ctx,
        "presupuesto": pres,
        "lineas": lineas_pdf,
        "totales": {
            "base": tot.get("base") or 0.0,
            "iva": tot.get("iva") or 0.0,
            "total": tot.get("total") or 0.0,
            "desglose": tot.get("desglose") or {},
        },
        "direccion_fiscal": dir_fiscal,
        "direccion_envio": dir_envio,
    }

    return data_real


# =========================================================
# BUILD PDF – Modelo ORBE (muy similar al ejemplo)
# =========================================================
def build_pdf_bytes(data_real: dict):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    # Colores corporativos ORBE
    ORBE_BLUE = colors.HexColor("#003865")
    ORBE_LIGHT = colors.HexColor("#E8EEF3")
    ORBE_GREY = colors.HexColor("#6B7280")

    # Documento base
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    emp = data_real.get("empresa", {}) or {}
    cli = data_real.get("cliente", {}) or {}
    pres = data_real.get("presupuesto", {}) or {}
    lineas = data_real.get("lineas", []) or []
    tot = data_real.get("totales", {}) or {}
    dfisc = data_real.get("direccion_fiscal") or {}
    denv = data_real.get("direccion_envio") or {}

    elements = []

    # =====================================================
    # 1️⃣ LOGO + CABECERA CORPORATIVA (como modelo)
    # =====================================================
    style_title = styles["Title"].clone("OrbeTitle")
    style_title.fontSize = 18
    style_title.textColor = ORBE_BLUE

    # Logo: se asume logo_orbe.png en el directorio raíz del proyecto
    logo_path = emp.get("logo_path") or "logo_orbe.png"
    if not os.path.exists(logo_path):
        # fallback: intenta un path relativo común en Streamlit Cloud
        alt = os.path.join(os.path.dirname(__file__), "..", "logo_orbe.png")
        if os.path.exists(alt):
            logo_path = alt

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=45 * mm, height=15 * mm)
    else:
        logo = None

    cab_left = logo if logo else Paragraph(emp.get("nombre", "ORBE"), styles["Heading3"])
    cab_right = Paragraph("PRESUPUESTO", style_title)

    cabecera = Table(
        [[cab_left, cab_right]],
        colWidths=[70 * mm, 90 * mm],
        hAlign="LEFT",
    )
    cabecera.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(cabecera)
    elements.append(Spacer(1, 8))

    # Línea azul bajo cabecera
    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            lineCap="round",
            color=ORBE_BLUE,
            spaceBefore=2,
            spaceAfter=10,
        )
    )

    # =====================================================
    # 2️⃣ BLOQUE CLIENTE (como el modelo: nombre, ATT, dir, CIF)
    # =====================================================
    style_small = styles["Normal"].clone("small")
    style_small.fontSize = 9
    style_small.leading = 11

    cliente_block = []

    razon_social = _safe(cli.get("razon_social") or cli.get("nombre_comercial"), "")
    if razon_social:
        cliente_block.append(Paragraph(_bold(razon_social), styles["Heading3"]))

    # ATT + teléfono
    att = cli.get("contacto_att") or pres.get("contacto_att")
    tel_att = cli.get("telefono_contacto") or pres.get("telefono_contacto")
    if att:
        if tel_att:
            att_txt = f"{att} ({tel_att})"
        else:
            att_txt = att
        cliente_block.append(Paragraph(f"ATT. {att_txt}", style_small))

    # Dirección fiscal
    if dfisc:
        df_dir = dfisc.get("direccion", "") or ""
        df_cp = dfisc.get("cp", "") or ""
        df_ciudad = dfisc.get("ciudad", "") or ""
        df_prov = dfisc.get("provincia", "") or ""
        df_pais = dfisc.get("pais", "") or "ESPAÑA"
        if df_dir:
            cliente_block.append(Paragraph(df_dir, style_small))
        loc_line = " ".join(
            [df_cp, df_ciudad, df_prov if df_prov else "", df_pais]
        ).strip()
        if loc_line:
            cliente_block.append(Paragraph(loc_line, style_small))

    # CIF/NIF
    cif = cli.get("cif") or cli.get("cif_nif") or ""
    if cif:
        cliente_block.append(Paragraph(cif, style_small))

    t_cli = Table([[cliente_block]], colWidths=[170 * mm])
    t_cli.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), ORBE_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, ORBE_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(t_cli)
    elements.append(Spacer(1, 10))

    # =====================================================
    # 3️⃣ Fila FECHA / PROFORMA / NUMERO (igual que el modelo)
    # =====================================================
    fecha_str = _fmt_fecha_ddmmaaaa(pres.get("fecha"))
    numero = _safe(pres.get("numero"), "-")
    # PROFORMA: si quieres puedes mapear referencia_cliente aquí
    proforma_num = pres.get("proforma") or pres.get("referencia_cliente") or ""

    info_header = ["FECHA", "PROFORMA", "NUMERO"]
    info_body = [fecha_str, proforma_num, numero]

    t_info = Table(
        [info_header, info_body],
        colWidths=[35 * mm, 50 * mm, 60 * mm],
        hAlign="LEFT",
    )
    t_info.setStyle(
        TableStyle(
            [
                # Cabecera
                ("BACKGROUND", (0, 0), (-1, 0), ORBE_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 0), (-1, 0), 2),
                # Cuerpo
                ("FONTSIZE", (0, 1), (-1, 1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ]
        )
    )
    elements.append(t_info)
    elements.append(Spacer(1, 8))

    # =====================================================
    # 4️⃣ TABLA DE LÍNEAS (Cant. / Producto / Precio / Dto.% / P./Dto. / Subtotal)
    # =====================================================
    table_lines = [["Cant.", "Producto", "Precio", "Dto. %", "P./Dto.", "Subtotal"]]

    for l in lineas:
        cant = float(l.get("unidades") or 0)
        desc = _safe(l.get("concepto"), "-")
        precio = float(l.get("precio") or 0)
        dto = float(l.get("dto") or 0)
        base = float(l.get("base") or 0)
        precio_dto = base / cant if cant else 0.0

        table_lines.append(
            [
                f"{cant:.0f}",
                desc,
                _money(precio),
                f"{dto:.2f}%",
                _money(precio_dto),
                _money(base),
            ]
        )

    t_lines = Table(
        table_lines,
        colWidths=[18 * mm, 75 * mm, 22 * mm, 18 * mm, 22 * mm, 25 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    t_lines.setStyle(
        TableStyle(
            [
                # Cabecera
                ("BACKGROUND", (0, 0), (-1, 0), ORBE_LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Celdas
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (0, -1), "RIGHT"),  # Cant.
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # Números
            ]
        )
    )
    elements.append(t_lines)
    elements.append(Spacer(1, 10))

    # =====================================================
    # 5️⃣ DIRECCION DE ENVIO (texto en mayúsculas como modelo)
    # =====================================================
    elements.append(Paragraph(_bold("DIRECCION DE ENVIO"), styles["Heading4"]))

    if denv:
        e_dir = denv.get("direccion", "") or ""
        e_cp = denv.get("cp", "") or ""
        e_ciudad = denv.get("ciudad", "") or ""
        e_prov = denv.get("provincia", "") or ""
        e_pais = denv.get("pais", "") or "ESPAÑA"

        t_env = "<br/>".join(
            [
                e_dir,
                f"{e_cp} {e_ciudad} ({e_prov})" if (e_cp or e_ciudad or e_prov) else "",
                e_pais,
            ]
        )
        elements.append(Paragraph(t_env, style_small))
    else:
        elements.append(Paragraph("—", style_small))

    elements.append(Spacer(1, 8))

    # =====================================================
    # 6️⃣ RESUMEN DE IVA (IMPUESTO / BASE IMPONIBLE / IMPORTE IVA)
    # =====================================================
    elements.append(Paragraph(_bold("IMPUESTO BASE IMPONIBLE IMPORTE IVA"), styles["Heading4"]))

    desg = tot.get("desglose") or {}

    if desg:
        iva_rows = [["Impuesto", "Base imponible", "Importe IVA"]]
        for iva_pct, vals in sorted(desg.items(), key=lambda x: float(str(x[0]).replace("%", ""))):
            base_iva = vals.get("base", 0)
            imp_iva = vals.get("iva", 0)
            iva_rows.append(
                [
                    f"IVA {iva_pct}",
                    _money(base_iva),
                    _money(imp_iva),
                ]
            )

        t_iva = Table(iva_rows, colWidths=[30 * mm, 45 * mm, 45 * mm])
        t_iva.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), ORBE_LIGHT),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ]
            )
        )
        elements.append(t_iva)
    else:
        elements.append(Paragraph("Sin impuestos calculados.", style_small))

    elements.append(Spacer(1, 10))

    # =====================================================
    # 7️⃣ OBSERVACIONES (bloque similar al ejemplo)
    # =====================================================
    obs = pres.get("observaciones") or "—"
    elements.append(Paragraph(_bold("OBSERVACIONES:"), styles["Heading4"]))

    obs_box = Table([[Paragraph(obs, style_small)]], colWidths=[170 * mm])
    obs_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), ORBE_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(obs_box)
    elements.append(Spacer(1, 10))

    # =====================================================
    # 8️⃣ TOTALES (BASE / GASTOS / IMPUESTOS / RECARGOS / TOTAL)
    # =====================================================
    base_t = tot.get("base") or 0.0
    iva_t = tot.get("iva") or 0.0
    gastos_envio = tot.get("gastos_envio") or 0.0
    recargos = tot.get("total_recargos") or 0.0
    total_factura = tot.get("total") or (base_t + iva_t + gastos_envio + recargos)

    elements.append(Paragraph(_bold("TOTALES:"), styles["Heading4"]))

    tot_rows = [
        ["BASE IMPONIBLE:", _money(base_t)],
        ["GASTOS ENVIO:", _money(gastos_envio)],
        ["TOTAL IMPUESTOS:", _money(iva_t)],
        ["TOTAL RECARGOS:", _money(recargos)],
        ["TOTAL FACTURA:", _money(total_factura)],
    ]

    t_tot = Table(tot_rows, colWidths=[60 * mm, 40 * mm], hAlign="LEFT")
    t_tot.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), ORBE_LIGHT),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    elements.append(t_tot)
    elements.append(Spacer(1, 10))

    # =====================================================
    # 9️⃣ Pie bancario + legal + datos empresa (similar al modelo)
    # =====================================================
    # Texto bancario
    banco_txt = emp.get(
        "texto_banco",
        "Datos Bancarios de ORBE Distribuidora Formación (IBAN): ES89 0049 6729 2623 1623 1833",
    )
    elements.append(Paragraph(banco_txt, style_small))
    elements.append(Spacer(1, 4))

    # Texto de validez / condiciones
    legal_main = emp.get(
        "texto_legal_principal",
        (
            "El presente documento tiene una validez de 30 días a partir de la fecha de emisión. "
            "Transcurrido ese plazo, los términos del mismo podrían estar sujetos a revisión y ajuste "
            "debido a posibles cambios en las condiciones del mercado y los costes de los materiales y "
            "servicios involucrados."
        ),
    )
    legal_main_p = Paragraph(f"<font size=7 color='{ORBE_GREY}'>{legal_main}</font>", styles["Normal"])
    elements.append(legal_main_p)
    elements.append(Spacer(1, 6))

    # Texto de protección de datos
    legal_dp = emp.get(
        "texto_proteccion_datos",
        (
            "A los efectos de lo dispuesto en la normativa de protección de datos, le informamos de que sus datos "
            "forman parte de un fichero responsabilidad de ORBE FORMACIÓN TECNOLÓGICA Y DISTRIBUCIÓN S.L. y se "
            "utilizarán para la prestación de los servicios y el envío de información que pudiera resultar de su interés. "
            "Puede ejercer sus derechos de acceso, rectificación, cancelación y oposición en nuestro domicilio."
        ),
    )
    legal_dp_p = Paragraph(f"<font size=6 color='{ORBE_GREY}'>{legal_dp}</font>", styles["Normal"])
    elements.append(legal_dp_p)
    elements.append(Spacer(1, 6))

    # Línea final con datos de contacto (tel / email / web / dirección)
    tel = emp.get("telefono") or "TEL +34 951 171 028"
    fax = emp.get("fax") or "FAX +34 916 094 479"
    email = emp.get("email") or "pedidos@orbeformacion.com"
    web = emp.get("web") or "www.orbeformacion.com"

    dir_emp = emp.get("direccion") or "C/ Marie Curie, 20. Planta baja, Puerta D · Conjunto Possibilia Edificio B"
    loc_emp = (
        f"{emp.get('cp','29590')} {emp.get('ciudad','Málaga')} ({emp.get('provincia','Málaga')})"
    )

    footer_txt_1 = f"{tel}   {fax}   {email}"
    footer_txt_2 = f"{dir_emp} · {loc_emp} · {web}"

    footer_p1 = Paragraph(f"<font size=7>{footer_txt_1}</font>", styles["Normal"])
    footer_p2 = Paragraph(f"<font size=7>{footer_txt_2}</font>", styles["Normal"])

    elements.append(footer_p1)
    elements.append(footer_p2)

    # =====================================================
    # 🔚 Construir PDF
    # =====================================================
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    file_name = f"presupuesto_{pres.get('numero','sin_numero')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return pdf_bytes, file_name


# =========================================================
# SUBIDA A STORAGE
# =========================================================
def upload_pdf_to_storage(supabase, pdf_bytes, file_name, bucket=BUCKET_DEFAULT):
    """Sube el PDF al bucket indicado y devuelve la URL pública (si hay policy)."""
    supabase.storage.from_(bucket).upload(
        file_name,
        pdf_bytes,
        {"content-type": "application/pdf"},
    )
    return supabase.storage.from_(bucket).get_public_url(file_name)


# =========================================================
# Preview en Streamlit (por si quieres usarlo en algún panel)
# =========================================================
def generate_pdf_for_download(supabase, presupuestoid: int):
    """Genera el PDF, lo muestra embebido en Streamlit y añade botón de descarga."""
    data_real = _build_data_real(supabase, presupuestoid)
    pdf_bytes, fname = build_pdf_bytes(data_real)

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    import streamlit as st

    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="720px"></iframe>',
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Descargar PDF",
        pdf_bytes,
        file_name=fname,
        mime="application/pdf",
        use_container_width=True,
    )

    return pdf_bytes, fname
