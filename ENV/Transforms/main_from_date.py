import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
os.environ["PYTHONUTF8"] = "1"

DEFAULT_FROM_DATE = "01-10-2023"

SCRIPTS = [
    ("export_albaran_cabecera_from_date_api_to_xlsx.py", True),   # recibe --from-date
    ("export_albaran_linea_detalle_from_cabecera_from_date_xlsx.py", False),
    ("load_albaran_from_date_xlsx_to_supabase.py", False),
    ("load_albaran_linea_from_date_xlsx_to_supabase.py", False),
]

LOG_FILE_NAME = "pipeline_from_date.log"


def run_step_live(py: Path, log_path: Path, extra_args: list[str]) -> None:
    cmd = [sys.executable, "-X", "utf8", str(py), *extra_args]
    ts = datetime.now(TZ).isoformat()

    # encabezado en log
    with log_path.open("a", encoding="utf-8") as lf:
        lf.write("\n" + "=" * 90 + "\n")
        lf.write(f"[{ts}] RUN: {' '.join(cmd)}\n")
        lf.flush()

    # ejecuta y “tee” stdout+stderr a consola y log
    p = subprocess.Popen(
        cmd,
        cwd=str(py.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
        env=os.environ.copy(),
    )

    with log_path.open("a", encoding="utf-8") as lf:
        try:
            assert p.stdout is not None
            for line in p.stdout:
                # consola
                print(line, end="")
                # log
                lf.write(line)
        except KeyboardInterrupt:
            # si cortas, paramos el proceso hijo limpio
            try:
                p.terminate()
            except Exception:
                pass
            raise
        finally:
            try:
                if p.stdout:
                    p.stdout.close()
            except Exception:
                pass

        code = p.wait()

    if code != 0:
        raise RuntimeError(f"Fallo {py.name} (exit={code}). Mira el log: {log_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-date",
        default=DEFAULT_FROM_DATE,
        help='Fecha desde la que descargar (formato dd-mm-YYYY). Ej: "01-10-2023"',
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    log_path = base_dir / LOG_FILE_NAME

    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "#" * 90 + "\n")
        f.write(f"PIPELINE FROM_DATE START {datetime.now(TZ).isoformat()} | from-date={args.from_date}\n")

    for script_name, needs_from_date in SCRIPTS:
        py = base_dir / script_name
        if not py.exists():
            raise FileNotFoundError(f"No existe el script: {py}")

        extra_args = ["--from-date", args.from_date] if needs_from_date else []

        print(f"\n[RUN] {script_name} {' '.join(extra_args)}".strip())
        run_step_live(py, log_path, extra_args)
        print(f"[OK]  {script_name}")

    print(f"\n[OK] PIPELINE COMPLETADO. Log: {log_path}")


if __name__ == "__main__":
    main()

