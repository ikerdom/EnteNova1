# daily_export_clientes_api_to_xlsx.py
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import pandas as pd
import requests

# =========================
# CONFIG
# =========================
EMPRESA_ID = 4
BASE_URL = f"http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/clientes/{EMPRESA_ID}"

PAGE_SIZE = 25  # <-- tu offset va de 25 en 25
REQUEST_TIMEOUT = 180
BACKOFF_START = 2.0
BACKOFF_MAX = 60.0
HEADERS = {"Content-Type": "application/json"}
STOP_IF_ZERO_NEW = True

# =========================
# OUTPUTS
# =========================
BASE_DIR = Path(__file__).resolve().parent
SHEET_NAME = "CLIENTE"
GLOBAL_SHEET_NAME = SHEET_NAME

OUTPUT_DAILY_XLSX = BASE_DIR / "CLIENTES_DAILY_DEL_DIA.xlsx"
OUTPUT_GLOBAL_XLSX = BASE_DIR / "CLIENTES_GLOBAL.xlsx"


# =========================
# Helpers
# =========================
def s(v: Any) -> Optional[str]:
    if v is None:
        return None
    t = str(v).strip()
    if not t or t.upper() in ("NAN", "NONE"):
        return None
    return t[:-2] if t.endswith(".0") else t


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


def get_any(it: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in it and it.get(k) is not None:
            return it.get(k)
    return None


def map_item_to_excel_row(it: Dict[str, Any]) -> Dict[str, Any]:
    # tolerante a mayus/minus
    return {
        "CODIGOCUENTA": s(get_any(it, "CODIGOCUENTA", "codigocuenta")),
        "CODIGOCLIENTEOPROVEEDOR": s(get_any(it, "CODIGOCLIENTEOPROVEEDOR", "codigoclienteoproveedor")),
        "CLIENTEOPROVEEDOR": s(get_any(it, "CLIENTEOPROVEEDOR", "clienteoproveedor")),
        "RAZONSOCIAL": s(get_any(it, "RAZONSOCIAL", "razonsocial")),
        "NOMBRE": s(get_any(it, "NOMBRE", "nombre")),
        "CIFDNI": s(get_any(it, "CIFDNI", "cifdni")),
        "VIAPUBLICA": s(get_any(it, "VIAPUBLICA", "viapublica")),
        "DOMICILIO": s(get_any(it, "DOMICILIO", "domicilio")),
        "IBAN": s(get_any(it, "IBAN", "iban")),
        "CODIGOBANCO": s(get_any(it, "CODIGOBANCO", "codigobanco")),
        "CODIGOAGENCIA": s(get_any(it, "CODIGOAGENCIA", "codigoagencia")),
        "DC": s(get_any(it, "DC", "dc")),
        "CCC": s(get_any(it, "CCC", "ccc")),
        "CODIGOPOSTAL": s(get_any(it, "CODIGOPOSTAL", "codigopostal")),
        "PROVINCIA": s(get_any(it, "PROVINCIA", "provincia")),
        "MUNICIPIO": s(get_any(it, "MUNICIPIO", "municipio")),
        "TELEFONO": s(get_any(it, "TELEFONO", "telefono")),
        "TELEFONO2": s(get_any(it, "TELEFONO2", "telefono2")),
        "TELEFONO3": s(get_any(it, "TELEFONO3", "telefono3")),
        "FAX": s(get_any(it, "FAX", "fax")),
        "CODIGOTIPOEFECTO": s(get_any(it, "CODIGOTIPOEFECTO", "codigotipoefecto")),
        "CODIGOCUENTAEFECTO": s(get_any(it, "CODIGOCUENTAEFECTO", "codigocuentaefecto")),
        "CODIGOCUENTAIMPAGADO": s(get_any(it, "CODIGOCUENTAIMPAGADO", "codigocuentaimpagado")),
        "REMESAHABITUAL": s(get_any(it, "REMESAHABITUAL", "remesahabitual")),
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

    # dedupe por CODIGOCUENTA
    if "CODIGOCUENTA" in df_all.columns:
        df_all["CODIGOCUENTA"] = df_all["CODIGOCUENTA"].astype(str).str.strip()
        df_all.loc[df_all["CODIGOCUENTA"].isin(["None", "nan", "NaN", ""]), "CODIGOCUENTA"] = None
        df_all = df_all.drop_duplicates(subset=["CODIGOCUENTA"], keep="last")

    sort_cols = [c for c in ["CODIGOCUENTA", "RAZONSOCIAL"] if c in df_all.columns]
    if sort_cols:
        df_all = df_all.sort_values(by=sort_cols, kind="stable")

    tmp = OUTPUT_GLOBAL_XLSX.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
        df_all.to_excel(writer, index=False, sheet_name=GLOBAL_SHEET_NAME)
    tmp.replace(OUTPUT_GLOBAL_XLSX)

    print(f"[OK] GLOBAL actualizado: {OUTPUT_GLOBAL_XLSX.name} | filas: {len(df_all)} | hoja: {GLOBAL_SHEET_NAME}")


def export_to_xlsx() -> str:
    session = requests.Session()

    excel_cols = [
        "CODIGOCUENTA","CODIGOCLIENTEOPROVEEDOR","CLIENTEOPROVEEDOR","RAZONSOCIAL","NOMBRE","CIFDNI",
        "VIAPUBLICA","DOMICILIO","IBAN","CODIGOBANCO","CODIGOAGENCIA","DC","CCC","CODIGOPOSTAL",
        "PROVINCIA","MUNICIPIO","TELEFONO","TELEFONO2","TELEFONO3","FAX",
        "CODIGOTIPOEFECTO","CODIGOCUENTAEFECTO","CODIGOCUENTAIMPAGADO","REMESAHABITUAL"
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

    # 1) Descargar paginado
    rows: List[Dict[str, Any]] = []
    seen_codes: Set[str] = set()

    offset = 0
    total_nuevos = 0

    while True:
        url = BASE_URL if offset == 0 else f"{BASE_URL}?offset={offset}"
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

            row = map_item_to_excel_row(it)
            code = row.get("CODIGOCUENTA")
            key = str(code).strip() if code is not None else None

            if not key:
                rows.append(row)
                nuevos_en_pagina += 1
                continue

            if key in seen_codes:
                repetidos_en_pagina += 1
                continue

            seen_codes.add(key)
            rows.append(row)
            nuevos_en_pagina += 1

        total_nuevos += nuevos_en_pagina
        print(f"[INFO] Nuevos: {nuevos_en_pagina} | Repetidos: {repetidos_en_pagina} | Total nuevos: {total_nuevos}")

        if STOP_IF_ZERO_NEW and nuevos_en_pagina == 0:
            print("[WARN] Pagina sin nuevos -> parece repeticion/bucle. Corto.")
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
