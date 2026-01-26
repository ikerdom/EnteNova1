from __future__ import annotations

import os
import sys
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

BASE_DIR = Path(__file__).resolve().parents[1]
PIPELINE_DIR = BASE_DIR / "Transforms"
PIPELINE_SCRIPT = PIPELINE_DIR / "main_pipeline.py"
LOG_FILE = PIPELINE_DIR / "pipeline_daily.log"
LAST_RUN_FILE = PIPELINE_DIR / "pipeline_last_run.txt"


def _today() -> date:
    return datetime.now(TZ).date()


def get_last_run_date() -> date | None:
    try:
        raw = LAST_RUN_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        return date.fromisoformat(raw)
    except Exception:
        return None


def can_run_today() -> tuple[bool, date | None]:
    last = get_last_run_date()
    today = _today()
    if last == today:
        return False, last
    return True, last


def run_pipeline() -> tuple[bool, str]:
    if not PIPELINE_SCRIPT.exists():
        return False, f"Missing pipeline script: {PIPELINE_SCRIPT}"

    cmd = [sys.executable, "-X", "utf8", str(PIPELINE_SCRIPT)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PIPELINE_DIR),
            env=os.environ.copy(),
            check=False,
        )
    except Exception as exc:
        return False, f"Failed to start pipeline: {exc}"

    if proc.returncode != 0:
        return False, f"Pipeline failed with exit code {proc.returncode}"

    try:
        LAST_RUN_FILE.write_text(_today().isoformat(), encoding="utf-8")
    except Exception:
        pass

    finished_at = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    return True, f"Refresco completado correctamente ({finished_at})"


def tail_log(n_lines: int = 200) -> str:
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-n_lines:])
    except Exception:
        return ""
