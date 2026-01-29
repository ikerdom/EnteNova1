import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

# Fuerza UTF-8 en Windows
os.environ["PYTHONUTF8"] = "1"

SCRIPTS = [
    "daily_export_albaran_cabecera_api_to_xlsx.py",
    "load_albaran_from_api_xlsx_v5_upsert_merge_skip_nulls_daily.py",
    "daily_export_albaran_linea_detalle_from_cabecera_xlsx_2026.py",
    "load_albaran_linea_from_xlsx_v1_insert_only_skip_existing.py",
]

LOG_FILE_NAME = "pipeline_daily.log"
LAST_RUN_FILE = "pipeline_last_run.txt"


def tail_file(path: Path, n_lines: int = 200) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-n_lines:])
    except Exception:
        return ""


def run_step(py: Path, log_path: Path) -> None:
    cmd = [sys.executable, "-X", "utf8", str(py)]
    ts = datetime.now(TZ).isoformat()

    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "=" * 90 + "\n")
        f.write(f"[{ts}] RUN: {' '.join(cmd)}\n")
        f.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(py.parent),
            stdout=f,
            stderr=f,
            text=True,
            env=os.environ.copy(),
        )
        code = p.wait()

    if code != 0:
        print("\n" + "!" * 90)
        print(f"[ERROR] Fallo: {py.name} (exit={code})")
        print("[INFO] Ultimas lineas del log:\n")
        print(tail_file(log_path, n_lines=260))
        print("!" * 90 + "\n")
        raise RuntimeError(f"Fallo {py.name} (exit={code}). Mira el log: {log_path}")


def main():
    base_dir = Path(__file__).resolve().parent
    log_path = base_dir / LOG_FILE_NAME
    last_run_path = base_dir / LAST_RUN_FILE

    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "#" * 90 + "\n")
        f.write(f"PIPELINE START {datetime.now(TZ).isoformat()}\n")

    for name in SCRIPTS:
        py = base_dir / name
        if not py.exists():
            raise FileNotFoundError(f"No existe el script: {py}")

        print(f"[RUN] {name}")
        run_step(py, log_path)
        print(f"[OK]  {name}")

    try:
        last_run_path.write_text(datetime.now(TZ).date().isoformat(), encoding="utf-8")
    except Exception:
        pass

    print(f"[OK] PIPELINE COMPLETADO. Log: {log_path}")


if __name__ == "__main__":
    main()
