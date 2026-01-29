# daily_export_albaran_linea_detalle_from_cabecera_xlsx_2026.py
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import pandas as pd
import requests


# =========================
# CONFIG
# =========================
CABECERA_XLSX = "ALBARANES_CABECERA_DAILY_DEL_DIA.xlsx"
CABECERA_SHEET = "ALBARAN_CABECERA"
CABECERA_COL_ID = "ALBARAN_ID"

LINEA_URL_TMPL = "http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/albaranes/{albaran_id}/linea_detalle"

SHEET_NAME = "ALBARAN_LINEA"

REQUEST_TIMEOUT = 180
BACKOFF_START = 2.0
BACKOFF_MAX = 60.0
HEADERS = {"Content-Type": "application/json"}

PAGE_SIZE = 25
STOP_IF_ZERO_NEW = True

# =========================
# OUTPUTS: mismo directorio del script
# =========================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DAILY_XLSX = BASE_DIR / "ALBARANES_LINEA_DAILY_DEL_DIA.xlsx"
OUTPUT_GLOBAL_XLSX = BASE_DIR / "ALBARANES_LINEA_GLOBAL.xlsx"
GLOBAL_SHEET_NAME = SHEET_NAME


# =========================
# Helpers
# =========================
def n_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return int(float(s))
    except Exception:
        return None


def n_num(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace("\u00A0", "").replace(" ", "").replace("'", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


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


def load_albaran_ids_from_cabecera_xlsx() -> List[int]:
    excel_path = BASE_DIR / CABECERA_XLSX
    if not excel_path.exists():
        excel_path = Path.cwd() / CABECERA_XLSX
    if not excel_path.exists():
        raise FileNotFoundError(f"No existe el Excel cabecera en: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=CABECERA_SHEET, dtype=object).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    if CABECERA_COL_ID not in df.columns:
        raise RuntimeError(
            f"No existe columna '{CABECERA_COL_ID}' en cabecera. Columnas: {list(df.columns)[:50]}"
        )

    ids: List[int] = []
    for v in df[CABECERA_COL_ID].tolist():
        aid = n_int(v)
        if aid is not None:
            ids.append(aid)

    ids = sorted(set(ids))
    print(f"[INFO] Albaranes en cabecera: {len(ids)}")
    return ids


def map_linea_to_excel_row(it: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "LINEA_ID": it.get("linea_id"),
        "ALBARAN_ID": it.get("albaran_id"),
        "PRODUCTO_ID_ORIGEN": None,
        "ALBARAN_NUMERO": it.get("albaran_numero"),
        "ALBARAN_SERIE": it.get("albaran_serie"),
        "PRODUCTO_REF_ORIGEN": it.get("producto_ref_id"),
        "IDPRODUCTO": it.get("idproducto"),
        "DESCRIPCION": it.get("descripcion_linea"),
        "CANTIDAD": it.get("cantidad"),
        "PRECIO": it.get("precio"),
        "DESCUENTO_PCT": it.get("descuento_pct"),
        "PRECIO_TRAS_DTO": it.get("precio_tras_dto"),
        "SUBTOTAL": it.get("subtotal"),
        "TASA_IMPUESTO": it.get("tasa_impuesto"),
        "CUOTA_IMPUESTO": it.get("cuota_impuesto"),
        "TASA_RECARGO": it.get("tasa_recargo"),
        "CUOTA_RECARGO": it.get("cuota_recargo"),
        "PEDIDO_LINEA_ID": it.get("pedido_linea_id"),
        "CUENTA_INGRESO": it.get("cuenta_ingreso"),
        "PRODUCTO_EXTERNO": False,
        "PRODUCTO_OBSERVACION": None,
        "PRODUCTO_ID": None,
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

    if "LINEA_ID" in df_all.columns:
        df_all = df_all.drop_duplicates(subset=["LINEA_ID"], keep="last")

    sort_cols = [c for c in ["ALBARAN_ID", "LINEA_ID"] if c in df_all.columns]
    if sort_cols:
        df_all = df_all.sort_values(by=sort_cols, kind="stable")

    tmp = OUTPUT_GLOBAL_XLSX.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
        df_all.to_excel(writer, index=False, sheet_name=GLOBAL_SHEET_NAME)
    tmp.replace(OUTPUT_GLOBAL_XLSX)

    print(f"[OK] GLOBAL actualizado: {OUTPUT_GLOBAL_XLSX.name} | filas: {len(df_all)} | hoja: {GLOBAL_SHEET_NAME}")


def export_lineas_to_xlsx() -> str:
    session = requests.Session()
    albaran_ids = load_albaran_ids_from_cabecera_xlsx()

    excel_cols = [
        "LINEA_ID","ALBARAN_ID","PRODUCTO_ID_ORIGEN","ALBARAN_NUMERO","ALBARAN_SERIE",
        "PRODUCTO_REF_ORIGEN","IDPRODUCTO","DESCRIPCION","CANTIDAD","PRECIO","DESCUENTO_PCT",
        "PRECIO_TRAS_DTO","SUBTOTAL","TASA_IMPUESTO","CUOTA_IMPUESTO","TASA_RECARGO","CUOTA_RECARGO",
        "PEDIDO_LINEA_ID","CUENTA_INGRESO","PRODUCTO_EXTERNO","PRODUCTO_OBSERVACION","PRODUCTO_ID"
    ]

    # 0) Volcar DAILY anterior al GLOBAL antes de sobrescribir
    df_prev_daily = _read_excel_if_exists(OUTPUT_DAILY_XLSX, SHEET_NAME)
    if df_prev_daily is not None and not df_prev_daily.empty:
        print(f"[INFO] Volcando DAILY anterior al GLOBAL: {OUTPUT_DAILY_XLSX.name} ({len(df_prev_daily)} filas)")
        for c in excel_cols:
            if c not in df_prev_daily.columns:
                df_prev_daily[c] = None
        df_prev_daily = df_prev_daily[excel_cols]
        merge_into_global(df_prev_daily, excel_cols)

    rows: List[Dict[str, Any]] = []
    seen_linea_ids: Set[str] = set()

    for idx, aid in enumerate(albaran_ids, start=1):
        base_url = LINEA_URL_TMPL.format(albaran_id=aid)
        print(f"[INFO] ({idx}/{len(albaran_ids)}) Descargando lineas de albaran_id={aid}")

        offset = 0
        total_nuevos_albaran = 0

        while True:
            url = base_url if offset == 0 else f"{base_url}?offset={offset}"
            data = fetch_json_until_ok(session, url)

            items = data.get("items") or []
            if not items:
                break

            nuevos_en_pagina = 0
            repetidos_en_pagina = 0

            for it in items:
                if not isinstance(it, dict):
                    continue

                lid = it.get("linea_id")
                lid_key = str(lid) if lid is not None else None

                row = map_linea_to_excel_row(it)

                if lid_key is None:
                    rows.append(row)
                    nuevos_en_pagina += 1
                    continue

                if lid_key in seen_linea_ids:
                    repetidos_en_pagina += 1
                    continue

                seen_linea_ids.add(lid_key)
                rows.append(row)
                nuevos_en_pagina += 1

            total_nuevos_albaran += nuevos_en_pagina
            print(
                f"   [INFO] Nuevas: {nuevos_en_pagina} | Repetidas: {repetidos_en_pagina} | Total albaran: {total_nuevos_albaran}"
            )

            if STOP_IF_ZERO_NEW and nuevos_en_pagina == 0:
                print("[WARN] Pagina sin nuevas lineas -> parece repeticion/bucle. Corto este albaran.")
                break

            has_more = data.get("hasMore")
            if has_more is False or len(items) < PAGE_SIZE:
                break

            offset += PAGE_SIZE

    if not rows:
        raise RuntimeError("No se descargo ninguna linea. Revisa cabecera, endpoint o conectividad.")

    df = pd.DataFrame(rows, columns=excel_cols)

    # Normaliza numericos
    num_cols = ["CANTIDAD","PRECIO","DESCUENTO_PCT","PRECIO_TRAS_DTO","SUBTOTAL","TASA_IMPUESTO","CUOTA_IMPUESTO","TASA_RECARGO","CUOTA_RECARGO"]
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].apply(n_num)

    int_cols = ["LINEA_ID","ALBARAN_ID","PRODUCTO_REF_ORIGEN","IDPRODUCTO","ALBARAN_NUMERO","PEDIDO_LINEA_ID"]
    for c in int_cols:
        if c in df.columns:
            df[c] = df[c].apply(n_int)

    # 1) Guardar DAILY (sobrescribe)
    with pd.ExcelWriter(OUTPUT_DAILY_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=SHEET_NAME)

    print(f"[OK] DAILY generado: {OUTPUT_DAILY_XLSX.name} | filas: {len(df)} | hoja: {SHEET_NAME}")

    # 2) Volcar DAILY nuevo al GLOBAL
    merge_into_global(df, excel_cols)

    return str(OUTPUT_DAILY_XLSX)


if __name__ == "__main__":
    export_lineas_to_xlsx()
