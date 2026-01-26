# backend/app/core/database.py
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# Carga .env desde ENV aunque el backend se ejecute desde otra carpeta.
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


URL_SUPABASE = _get_env("URL_SUPABASE")
SUPABASE_SERVICE_KEY = _get_env("SUPABASE_SERVICE_KEY") or _get_env("SUPABASE_KEY")


@lru_cache
def get_supabase() -> Client:
    if not URL_SUPABASE or not SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "Variables URL_SUPABASE o SUPABASE_SERVICE_KEY/SUPABASE_KEY no definidas"
        )
    if not URL_SUPABASE.startswith("http"):
        raise RuntimeError("URL_SUPABASE invalida (debe empezar por http)")

    return create_client(URL_SUPABASE, SUPABASE_SERVICE_KEY)
