# daily_export_albaran_cabecera_api_to_xlsx.py
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import pandas as pd
import requests


# =========================
# CONFIG
# =========================
EMPRESA_ID = 4

# FECHA
USE_YESTERDAY = True
LOOKBACK_DAYS = 1  # si USE_YESTERDAY=False, usa hoy - LOOKBACK_DAYS
LAST_RUN_FILE = Path(__file__).resolve().parent / "pipeline_last_run.txt"

TZ = ZoneInfo("Europe/Madrid")

PAGE_SIZE = 25

REQUEST_TIMEOUT = 180
BACKOFF_START = 2.0
BACKOFF_MAX = 60.0
HEADERS = {"Content-Type": "application/json"}
STOP_IF_ZERO_NEW = True  # corta si la API repite páginas


# =========================
# SALIDAS: mismo directorio del script
# =========================
BASE_DIR = Path(__file__).resolve().parent

SHEET_NAME = "ALBARAN_CABECERA"
GLOBAL_SHEET_NAME = SHEET_NAME

OUTPUT_DAILY_XLSX = BASE_DIR / "ALBARANES_CABECERA_DAILY_DEL_DIA.xlsx"
OUTPUT_GLOBAL_XLSX = BASE_DIR / "ALBARANES_CABECERA_GLOBAL.xlsx"


# =========================
# Helpers
# =========================
def calc_fecha_desde_str() -> str:
    today = datetime.now(TZ).date()
    if LAST_RUN_FILE.exists():
        try:
            raw = LAST_RUN_FILE.read_text(encoding="utf-8").strip()
            if raw:
                last = date.fromisoformat(raw)
                d = last - timedelta(days=1)
                return d.strftime("%d-%m-%Y")
        except Exception:
            pass
    if USE_YESTERDAY:
        d = today - timedelta(days=1)
    else:
        d = today - timedelta(days=LOOKBACK_DAYS)
    return d.strftime("%d-%m-%Y")


def iso_passthrough(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def fetch_json_until_ok(session: requests.Session, url: str) -> Dict[str, Any]:
    attempt = 0
    sleep_s = BACKOFF_START

    while True:
        attempt += 1
        try:
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"   [WARN] HTTP {resp.status_code} (intento {attempt}) -> {url}")
            else:
                try:
                    return resp.json()
                except Exception as e:
                    print(f"   [WARN] JSON invalido (intento {attempt}) -> {e}")

        except requests.exceptions.Timeout:
            print(f"   [WARN] Timeout ({REQUEST_TIMEOUT}s) (intento {attempt}) -> {url}")
        except Exception as e:
            print(f"   [WARN] Error (intento {attempt}) -> {e}")

        print(f"   [INFO] Reintentando en {sleep_s:.0f}s...")
        time.sleep(sleep_s)
        sleep_s = min(BACKOFF_MAX, sleep_s * 1.5)


def map_item_to_excel_row(it: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ALBARAN_ID": it.get("albaran_id"),
        "TIPO_DOCUMENTO": it.get("tipo_documento"),
        "NUMERO": it.get("numero"),
        "SERIE": it.get("serie"),

        "ID_EMPRESA": it.get("id_empresa"),

        "ID_TERCERO": it.get("id_tercero"),
        "ID_TIPO_TERCERO": it.get("id_tipo_tercero"),

        "CLIENTE": it.get("cliente"),
        "CIF_CLIENTE": it.get("cif_cliente"),
        "EMPRESA": it.get("empresa"),
        "TIPO_TERCERO": it.get("tipo_tercero"),
        "ESTADO": it.get("estado"),
        "FORMA_DE_PAGO": it.get("forma_de_pago"),

        "ID_DIRECCION": it.get("id_direccion"),

        "IMPUESTO_ENVIO": it.get("impuesto_envio"),
        "CUENTA_CLIENTE_PROVEEDOR": it.get("cuenta_cliente_proveedor"),

        "BASE_GASTOS_ENVIO": it.get("base_gastos_envio"),
        "BASE_IMPONIBLE": it.get("base_imponible"),
        "TOTAL_IMPUESTOS": it.get("total_impuestos"),
        "TOTAL_DESCUENTOS": it.get("total_descuentos"),
        "TOTAL_RECARGOS": it.get("total_recargos"),
        "TOTAL_GENERAL": it.get("total_general"),

        "FECHA_ALBARAN": iso_passthrough(it.get("fecha_albaran")),
        "FECHA_FACTURAR": iso_passthrough(it.get("fecha_facturar")),
        "FECHA_FACTURACION": iso_passthrough(it.get("fecha_facturacion")),
        "FECHA_VENCIMIENTO": iso_passthrough(it.get("fecha_vencimiento")),

        "OBSERVACIONES": it.get("observaciones"),
        "OBSERVACIONES_FACTURA": it.get("observaciones_factura"),

        "RESUMEN_FACTURACION": it.get("resumen_facturacion"),

        "CREADO_POR": it.get("creado_por"),
        "ACTUALIZADO_POR": it.get("actualizado_por"),
    }


def _read_excel_if_exists(path: Path, sheet: str) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    df = pd.read_excel(path, sheet_name=sheet, dtype=object).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def merge_into_global(df_in: pd.DataFrame, excel_cols: List[str]) -> None:
    df_global = _read_excel_if_exists(OUTPUT_GLOBAL_XLSX, GLOBAL_SHEET_NAME)
    if df_global is None:
        df_global = pd.DataFrame(columns=excel_cols)
    else:
        for c in excel_cols:
            if c not in df_global.columns:
                df_global[c] = None
        df_global = df_global[excel_cols]

    if df_global.empty:
        df_all = df_in.copy()
    else:
        df_all = pd.concat([df_global, df_in], ignore_index=True)

    if "ALBARAN_ID" in df_all.columns:
        df_all = df_all.drop_duplicates(subset=["ALBARAN_ID"], keep="last")

    sort_cols = [c for c in ["FECHA_ALBARAN", "ALBARAN_ID"] if c in df_all.columns]
    if sort_cols:
        df_all = df_all.sort_values(by=sort_cols, kind="stable")

    tmp = OUTPUT_GLOBAL_XLSX.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
        df_all.to_excel(writer, index=False, sheet_name=GLOBAL_SHEET_NAME)
    tmp.replace(OUTPUT_GLOBAL_XLSX)

    print(f"[OK] GLOBAL actualizado: {OUTPUT_GLOBAL_XLSX.name} | filas: {len(df_all)} | hoja: {GLOBAL_SHEET_NAME}")


def export_to_xlsx() -> str:
    session = requests.Session()

    # 0) Volcar DAILY anterior al GLOBAL antes de sobrescribir
    df_prev_daily = _read_excel_if_exists(OUTPUT_DAILY_XLSX, SHEET_NAME)

    excel_cols = [
        "ALBARAN_ID","TIPO_DOCUMENTO","NUMERO","SERIE","ID_EMPRESA","ID_TERCERO","ID_TIPO_TERCERO",
        "CLIENTE","CIF_CLIENTE","EMPRESA","TIPO_TERCERO","ESTADO","FORMA_DE_PAGO","ID_DIRECCION",
        "IMPUESTO_ENVIO","CUENTA_CLIENTE_PROVEEDOR","BASE_GASTOS_ENVIO","BASE_IMPONIBLE",
        "TOTAL_IMPUESTOS","TOTAL_DESCUENTOS","TOTAL_RECARGOS","TOTAL_GENERAL",
        "FECHA_ALBARAN","FECHA_FACTURAR","FECHA_FACTURACION","FECHA_VENCIMIENTO",
        "OBSERVACIONES","OBSERVACIONES_FACTURA","RESUMEN_FACTURACION","CREADO_POR","ACTUALIZADO_POR"
    ]

    if df_prev_daily is not None and not df_prev_daily.empty:
        print(f"[INFO] Volcando DAILY anterior al GLOBAL: {OUTPUT_DAILY_XLSX.name} ({len(df_prev_daily)} filas)")
        for c in excel_cols:
            if c not in df_prev_daily.columns:
                df_prev_daily[c] = None
        df_prev_daily = df_prev_daily[excel_cols]
        merge_into_global(df_prev_daily, excel_cols)

    # 1) Construir URL con FECHA_DESDE automática
    fecha_desde = calc_fecha_desde_str()
    base_url = (
        f"http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/albaranes/empresa/{EMPRESA_ID}/fecha/{fecha_desde}"
    )

    print(f"[INFO] FECHA_DESDE usada: {fecha_desde}")
    print(f"[INFO] ENDPOINT: {base_url}")

    rows: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    offset = 0
    total_nuevos = 0

    while True:
        url = base_url if offset == 0 else f"{base_url}?offset={offset}"
        print(f"[INFO] Descargando offset={offset} ...")

        data = fetch_json_until_ok(session, url)

        items = data.get("items") or []
        if not items:
            print("[INFO] Fin real: items vacio.")
            break

        nuevos_en_pagina = 0
        repetidos_en_pagina = 0

        for it in items:
            if not isinstance(it, dict):
                continue

            aid = it.get("albaran_id")
            aid_key = str(aid) if aid is not None else None

            row = map_item_to_excel_row(it)

            if aid_key is None:
                rows.append(row)
                nuevos_en_pagina += 1
                continue

            if aid_key in seen_ids:
                repetidos_en_pagina += 1
                continue

            seen_ids.add(aid_key)
            rows.append(row)
            nuevos_en_pagina += 1

        total_nuevos += nuevos_en_pagina
        print(
            f"[INFO] Nuevos en esta pagina: {nuevos_en_pagina} | Repetidos: {repetidos_en_pagina} | Total nuevos: {total_nuevos}"
        )

        if STOP_IF_ZERO_NEW and nuevos_en_pagina == 0:
            print("[WARN] Pagina sin nuevos IDs -> parece repeticion/bucle. Corto.")
            break

        has_more = data.get("hasMore")
        if has_more is False or len(items) < PAGE_SIZE:
            print("[INFO] Ultima pagina.")
            break

        offset += PAGE_SIZE

    if not rows:
        raise RuntimeError("No se descargo ningun item. Revisa el endpoint o conectividad.")

    df = pd.DataFrame(rows, columns=excel_cols)

    # 2) Guardar DAILY (sobrescribe)
    with pd.ExcelWriter(OUTPUT_DAILY_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=SHEET_NAME)

    print(f"[OK] DAILY generado: {OUTPUT_DAILY_XLSX.name} | filas: {len(df)} | hoja: {SHEET_NAME}")

    # 3) Volcar DAILY nuevo al GLOBAL
    merge_into_global(df, excel_cols)

    return str(OUTPUT_DAILY_XLSX)


if __name__ == "__main__":
    export_to_xlsx()
