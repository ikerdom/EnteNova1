import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

URL_SUPABASE = (os.getenv("URL_SUPABASE") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
if not URL_SUPABASE or not SUPABASE_KEY:
    raise RuntimeError("Faltan URL_SUPABASE/SUPABASE_KEY en ENV/.env")
if URL_SUPABASE.startswith("postgresql://") or not URL_SUPABASE.startswith("http"):
    raise RuntimeError("URL_SUPABASE invalida. Debe ser https://xxxx.supabase.co")

TABLE = "albaran"

# ✅ apunta al excel nuevo "desde fecha"
EXCEL_FILE = "ALBARANES_CABECERA_FROM_DATE.xlsx"
SHEET_NAME = "ALBARAN_CABECERA"

BATCH_SIZE = 500
TIMEOUT = 180
MAX_RETRIES = 6

REST_URL = f"{URL_SUPABASE}/rest/v1/{TABLE}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    # UPSERT + si faltan columnas con DEFAULT, que use default
    "Prefer": "resolution=merge-duplicates,missing=default,return=minimal",
}


def n_str(v: Any) -> Optional[str]:
    if v is None or pd.isna(v):
        return None
    s = str(v).strip()
    if s.upper() in ("NAN", "NONE", ""):
        return None
    return s[:-2] if s.endswith(".0") else s


def n_int(v: Any) -> Optional[int]:
    if v is None or pd.isna(v):
        return None
    try:
        s = str(v).strip()
        if s.endswith(".0"):
            s = s[:-2]
        if not s:
            return None
        return int(float(s))
    except Exception:
        return None


def n_num(v: Any) -> Optional[float]:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        try:
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return float(v)
        except Exception:
            return None

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


def n_dt_utc(v: Any) -> Optional[str]:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, str) and v.strip():
        return v.strip()
    if isinstance(v, datetime):
        return v.isoformat()
    try:
        dt = pd.to_datetime(v, errors="coerce", utc=True)
        if pd.isna(dt):
            return None
        return dt.to_pydatetime().isoformat()
    except Exception:
        return None


def drop_nullish(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Quita nulls/vacios/NaN/inf para no pisar datos existentes."""
    out: Dict[str, Any] = {}
    for k, v in rec.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            continue
        out[k] = v
    return out


def load_excel() -> pd.DataFrame:
    base_dir = Path(__file__).resolve().parent
    excel_path = base_dir / EXCEL_FILE
    if not excel_path.exists():
        excel_path = Path.cwd() / EXCEL_FILE
    if not excel_path.exists():
        raise FileNotFoundError(f"No existe el Excel: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=SHEET_NAME, dtype=object).dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_batch_keys(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    FIX PGRST102:
    En batch insert/upsert, todos los objetos deben tener las mismas keys.
    """
    if not batch:
        return batch

    all_keys = set()
    for r in batch:
        all_keys.update(r.keys())

    normalized: List[Dict[str, Any]] = []
    for r in batch:
        rr = dict(r)
        for k in all_keys:
            rr.setdefault(k, None)
        normalized.append(rr)

    return normalized


def post_with_retry_upsert(payload: List[Dict[str, Any]]) -> None:
    url = f"{REST_URL}?on_conflict=albaran_id"

    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)

        if resp.status_code in (200, 201, 204):
            return

        if resp.status_code in (408, 429, 500, 502, 503, 504):
            time.sleep(min(2 ** attempt, 30))
            continue

        raise RuntimeError(f"UPSERT HTTP {resp.status_code}: {resp.text[:2000]}")

    raise RuntimeError(f"Fallo UPSERT tras {MAX_RETRIES} reintentos. Ultimo: {resp.status_code} {resp.text[:2000]}")


def run():
    df = load_excel()
    rows: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        albaran_id = n_int(r.get("ALBARAN_ID"))
        if albaran_id is None:
            continue

        rec: Dict[str, Any] = {
            "albaran_id": albaran_id,

            "tipo_documento": n_str(r.get("TIPO_DOCUMENTO")),
            "numero": n_int(r.get("NUMERO")),
            "serie": n_str(r.get("SERIE")),

            # ✅ FIX: en tu tabla NO existe id_empresa -> usamos empresa_id
            "empresa_id": n_int(r.get("ID_EMPRESA")),

            "id_tercero": n_int(r.get("ID_TERCERO")),
            "id_tipo_tercero": n_int(r.get("ID_TIPO_TERCERO")),
            "cliente": n_str(r.get("CLIENTE")),
            "cif_cliente": n_str(r.get("CIF_CLIENTE")),
            "cuenta_cliente_proveedor": n_str(r.get("CUENTA_CLIENTE_PROVEEDOR")),
            "id_direccion_origen": n_int(r.get("ID_DIRECCION")),

            "tipo_tercero": n_str(r.get("TIPO_TERCERO")),
            "estado": n_str(r.get("ESTADO")),
            "forma_de_pago": n_str(r.get("FORMA_DE_PAGO")),
            "impuesto_envio": n_num(r.get("IMPUESTO_ENVIO")),

            "base_gastos_envio": n_num(r.get("BASE_GASTOS_ENVIO")),
            "base_imponible": n_num(r.get("BASE_IMPONIBLE")),
            "total_impuestos": n_num(r.get("TOTAL_IMPUESTOS")),
            "total_descuentos": n_num(r.get("TOTAL_DESCUENTOS")),
            "total_recargos": n_num(r.get("TOTAL_RECARGOS")),
            "total_general": n_num(r.get("TOTAL_GENERAL")),

            "fecha_albaran": n_dt_utc(r.get("FECHA_ALBARAN")),
            "fecha_facturar": n_dt_utc(r.get("FECHA_FACTURAR")),
            "fecha_facturacion": n_dt_utc(r.get("FECHA_FACTURACION")),
            "fecha_vencimiento": n_dt_utc(r.get("FECHA_VENCIMIENTO")),

            "observaciones": n_str(r.get("OBSERVACIONES")),
            "observaciones_factura": n_str(r.get("OBSERVACIONES_FACTURA")),
            "resumen_facturacion": n_str(r.get("RESUMEN_FACTURACION")),
            "creado_por": n_str(r.get("CREADO_POR")),
            "actualizado_por": n_str(r.get("ACTUALIZADO_POR")),
        }

        # no pisar con nulls/vacios
        rec = drop_nullish(rec)

        # no tocar campos normalizados
        rec.pop("clienteid", None)
        rec.pop("clientes_direccionid", None)
        rec.pop("forma_pagoid", None)
        rec.pop("albaran_estadoid", None)

        rows.append(rec)

    print(f"[INFO] Preparados: {len(rows)} albaranes (UPSERT merge, sin pisar con NULLs, sin tocar FKs)")

    if not rows:
        print("[OK] Nada que cargar.")
        return

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        batch = normalize_batch_keys(batch)  # FIX PGRST102
        post_with_retry_upsert(batch)
        print(f"[OK]  Lote {i//BATCH_SIZE + 1} | {min(i + len(batch), len(rows))}/{len(rows)}")

    print("[OK] UPSERT COMPLETADO (merge-duplicates, triggers intactos)")


if __name__ == "__main__":
    run()
