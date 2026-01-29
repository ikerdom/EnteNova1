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


def get_supabase_creds() -> tuple[str, str]:
    _load_env()

    url = os.getenv("URL_SUPABASE") or os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("Faltan URL_SUPABASE/SUPABASE_URL y SUPABASE_KEY en .env.")

    url = str(url).strip().strip('"').strip("'")
    key = str(key).strip().strip('"').strip("'")

    if url.startswith("postgresql://") or not url.startswith("http"):
        raise RuntimeError("URL_SUPABASE invalida. Debe ser https://xxxx.supabase.co")

    return url, key
