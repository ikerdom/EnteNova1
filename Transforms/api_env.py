import os
from pathlib import Path
from dotenv import load_dotenv


def _load_env() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for p in candidates:
        if p.is_file():
            load_dotenv(p, override=True)
            return


def get_cloudia_base_url() -> str:
    _load_env()
    base = os.getenv("CLOUDIA_BASE_URL") or os.getenv("ORBE_CLOUDIA_BASE_URL")
    if not base:
        raise RuntimeError("Falta CLOUDIA_BASE_URL/ORBE_CLOUDIA_BASE_URL en .env.")
    base = str(base).strip().rstrip("/")
    if not base.startswith("http"):
        raise RuntimeError("CLOUDIA_BASE_URL invalida. Debe empezar por http(s).")
    return base
