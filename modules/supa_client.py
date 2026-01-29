"""
Supabase client for UI and scripts.
Credentials loaded from (in order):
1) Streamlit secrets (if present)
2) .env in current directory
3) URL_SUPABASE/SUPABASE_KEY env vars
"""
from supabase import create_client
import os
import streamlit as st
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

_SUPABASE_CACHED = None


def _load_env() -> str:
    cwd_env = Path(os.getcwd()) / ".env"
    env_dir_env = Path(__file__).resolve().parents[1] / ".env"
    env_path = cwd_env if cwd_env.is_file() else env_dir_env
    if env_path.is_file():
        # Prioriza el .env local sobre variables del sistema
        load_dotenv(env_path, override=True)
    return str(env_path)


def _get_creds():
    env_path = _load_env()

    # Try Streamlit secrets first (if available)
    try:
        url = st.secrets.get("URL_SUPABASE")  # type: ignore[attr-defined]
        key = st.secrets.get("SUPABASE_KEY")  # type: ignore[attr-defined]
        if url and key:
            return url, key
    except Exception:
        pass

    # Fallback to environment variables
    url = os.getenv("URL_SUPABASE")
    key = os.getenv("SUPABASE_KEY")

    # Fallback to .env values if still missing
    if not url or not key:
        file_vals = dotenv_values(env_path) if os.path.isfile(env_path) else {}
        url = url or file_vals.get("URL_SUPABASE")
        key = key or file_vals.get("SUPABASE_KEY")

    if not url or not key:
        msg = "Faltan credenciales Supabase. Rellena URL_SUPABASE/SUPABASE_KEY en .env o secrets.toml."
        try:
            st.error(msg)
            st.stop()
        except Exception:
            raise ValueError(msg)

    url = str(url).strip().strip('"').strip("'")
    key = str(key).strip().strip('"').strip("'")

    if url.startswith("postgresql://"):
        msg = (
            "URL_SUPABASE invalida: parece una cadena Postgres. "
            "Debes usar la URL HTTPS del proyecto (https://xxxx.supabase.co). "
            f"Valor actual: {url!r}."
        )
        try:
            st.error(msg)
            st.stop()
        except Exception:
            raise ValueError(msg)

    if not url.startswith("http"):
        msg = (
            "URL_SUPABASE invalida. Debe empezar por http(s). "
            f"Valor actual: {url!r}. Revisa .env o secrets.toml."
        )
        try:
            st.error(msg)
            st.stop()
        except Exception:
            raise ValueError(msg)

    return url, key


def get_supabase_client():
    """
    Reusable Supabase client for Streamlit UI.
    """
    global _SUPABASE_CACHED
    if _SUPABASE_CACHED is None:
        url, key = _get_creds()
        _SUPABASE_CACHED = create_client(url, key)
    return _SUPABASE_CACHED


def get_client():
    """
    Supabase client for scripts/terminal (non-Streamlit).
    """
    global _SUPABASE_CACHED
    if _SUPABASE_CACHED is None:
        url, key = _get_creds()
        _SUPABASE_CACHED = create_client(url, key)
    return _SUPABASE_CACHED
