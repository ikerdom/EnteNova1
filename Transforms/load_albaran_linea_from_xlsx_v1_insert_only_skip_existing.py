import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import requests
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

URL_SUPABASE = (os.getenv("URL_SUPABASE") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
if not URL_SUPABASE or not SUPABASE_KEY:
    raise RuntimeError("Faltan URL_SUPABASE/SUPABASE_KEY en ENV/.env")
if URL_SUPABASE.startswith("postgresql://") or not URL_SUPABASE.startswith("http"):
    raise RuntimeError("URL_SUPABASE invalida. Debe ser https://xxxx.supabase.co")

TABLE = "albaran_linea"

EXCEL_FILE = "ALBARANES_LINEA_DAILY_DEL_DIA.xlsx"
SHEET_NAME = "ALBARAN_LINEA"

BATCH_SIZE = 500
TIMEOUT = 180
MAX_RETRIES = 6

REST_URL = f"{URL_SUPABASE}/rest/v1/{TABLE}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
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


def n_bool(v: Any) -> Optional[bool]:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "t", "1", "si", "sí", "yes", "y", "verdadero"):
        return True
    if s in ("false", "f", "0", "no", "n", "falso"):
        return False
    return None


def clean_nan(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in rec.items():
        if v is None:
            out[k] = None
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        else:
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


def quote_for_in(values: List[str]) -> str:
    # PostgREST in.(...) con TEXT => necesita comillas
    out = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip().replace('"', '\\"')
        if not s:
            continue
        out.append(f'"{s}"')
    return ",".join(out)


def fetch_existing_linea_ids(linea_ids: List[str], chunk_size: int = 300) -> Set[str]:
    """
    Devuelve el conjunto de linea_id que YA existen.
    IMPORTANTE: construye in.( "1","2" ) para columnas text.
    """
    session = requests.Session()
    existing: Set[str] = set()

    ids = sorted({str(x).strip() for x in linea_ids if x is not None and str(x).strip() != ""})
    if not ids:
        return existing

    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        in_list = quote_for_in(chunk)

        url = f"{REST_URL}?select=linea_id&linea_id=in.({in_list})"

        for attempt in range(1, MAX_RETRIES + 1):
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)

            if resp.status_code == 200:
                data = resp.json() or []
                for row in data:
                    v = row.get("linea_id")
                    if v is not None:
                        existing.add(str(v))
                break

            if resp.status_code in (408, 429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 30))
                continue

            # 🔥 aquí damos pista exacta
            raise RuntimeError(
                f"GET existing_linea_ids HTTP {resp.status_code}: {resp.text[:2000]}\nURL={url}"
            )

    return existing


def post_with_retry_insert_only(payload: List[Dict[str, Any]]) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(REST_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)

        if resp.status_code in (200, 201, 204):
            return

        if resp.status_code in (408, 409, 429, 500, 502, 503, 504):
            time.sleep(min(2 ** attempt, 30))
            continue

        raise RuntimeError(f"INSERT HTTP {resp.status_code}: {resp.text[:2000]}")

    raise RuntimeError(f"Fallo INSERT tras {MAX_RETRIES} reintentos. Ultimo: {resp.status_code} {resp.text[:2000]}")


def run():
    df = load_excel()

    for c in ["LINEA_ID", "ALBARAN_ID"]:
        if c not in df.columns:
            raise RuntimeError(f"Falta columna obligatoria '{c}' en el Excel. Columnas: {list(df.columns)}")

    rows: List[Dict[str, Any]] = []
    ids_in_excel: List[str] = []

    for _, r in df.iterrows():
        # ✅ ids como string para compat con BD text
        linea_id = n_str(r.get("LINEA_ID"))
        albaran_id = n_str(r.get("ALBARAN_ID"))

        if linea_id is None or albaran_id is None:
            continue

        rec = {
            "linea_id": linea_id,
            "albaran_id": albaran_id,

            "producto_id_origen": n_int(r.get("PRODUCTO_ID_ORIGEN")),
            "albaran_numero": n_int(r.get("ALBARAN_NUMERO")),
            "albaran_serie": n_str(r.get("ALBARAN_SERIE")),
            "producto_ref_origen": n_int(r.get("PRODUCTO_REF_ORIGEN")),
            "idproducto": n_int(r.get("IDPRODUCTO")),
            "descripcion": n_str(r.get("DESCRIPCION")),
            "cantidad": n_num(r.get("CANTIDAD")),
            "precio": n_num(r.get("PRECIO")),
            "descuento_pct": n_num(r.get("DESCUENTO_PCT")),
            "precio_tras_dto": n_num(r.get("PRECIO_TRAS_DTO")),
            "subtotal": n_num(r.get("SUBTOTAL")),
            "tasa_impuesto": n_num(r.get("TASA_IMPUESTO")),
            "cuota_impuesto": n_num(r.get("CUOTA_IMPUESTO")),
            "tasa_recargo": n_num(r.get("TASA_RECARGO")),
            "cuota_recargo": n_num(r.get("CUOTA_RECARGO")),
            "pedido_linea_id": n_int(r.get("PEDIDO_LINEA_ID")),
            "cuenta_ingreso": n_str(r.get("CUENTA_INGRESO")),

            "producto_externo": (n_bool(r.get("PRODUCTO_EXTERNO")) if "PRODUCTO_EXTERNO" in df.columns else None),
            "producto_observacion": (n_str(r.get("PRODUCTO_OBSERVACION")) if "PRODUCTO_OBSERVACION" in df.columns else None),
            "producto_id": (n_int(r.get("PRODUCTO_ID")) if "PRODUCTO_ID" in df.columns else None),
        }

        rec = clean_nan(rec)

        if rec.get("producto_externo") is None:
            rec.pop("producto_externo", None)

        rows.append(rec)
        ids_in_excel.append(linea_id)

    print(f"[INFO] Preparadas: {len(rows)} lineas con PK (sin tocar FKs)")

    if not rows:
        print("[OK] Nada que cargar.")
        return

    existing_ids = fetch_existing_linea_ids(ids_in_excel, chunk_size=300)
    print(f"[INFO] Ya existen en BD: {len(existing_ids)} lineas")

    new_rows = [r for r in rows if str(r["linea_id"]) not in existing_ids]
    print(f"[INFO] Nuevas a insertar: {len(new_rows)}")

    if not new_rows:
        print("[OK] Nada que insertar.")
        return

    for i in range(0, len(new_rows), BATCH_SIZE):
        batch = new_rows[i : i + BATCH_SIZE]
        post_with_retry_insert_only(batch)
        print(f"[OK]  Lote {i//BATCH_SIZE + 1} | {min(i + len(batch), len(new_rows))}/{len(new_rows)}")

    print("[OK] INSERT-ONLY COMPLETADO (sin tocar registros existentes)")


if __name__ == "__main__":
    run()
