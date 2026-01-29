import os
from pathlib import Path
from pipeline_runner import run_pipeline

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
LOCK_FILE_NAME = "pipeline_daily.lock"
MAX_LOG_BYTES = 10 * 1024 * 1024
KEEP_LOG_FILES = 5

TIMEOUTS = {
    "daily_export_albaran_cabecera_api_to_xlsx.py": 12 * 60,
    "load_albaran_from_api_xlsx_v5_upsert_merge_skip_nulls_daily.py": 12 * 60,
    "daily_export_albaran_linea_detalle_from_cabecera_xlsx_2026.py": 20 * 60,
    "load_albaran_linea_from_xlsx_v1_insert_only_skip_existing.py": 15 * 60,
}
DEFAULT_TIMEOUT = 15 * 60

RETRYABLE_PREFIXES = ("daily_export_", "load_", "sync_")
MAX_ATTEMPTS_RETRYABLE = 3
SLEEP_BETWEEN_RETRIES_S = 60
BACKOFF_MAX_S = 300

AUTO_COMMIT_FILES = [
    "ALBARANES_CABECERA_DAILY_DEL_DIA.xlsx",
    "ALBARANES_CABECERA_GLOBAL.xlsx",
    "ALBARANES_LINEA_DAILY_DEL_DIA.xlsx",
    "ALBARANES_LINEA_GLOBAL.xlsx",
]
AUTO_COMMIT_MESSAGE = "chore: update albaranes excels"


def main():
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parents[1]
    auto_commit_paths = [base_dir / f for f in AUTO_COMMIT_FILES]

    run_pipeline(
        scripts=SCRIPTS,
        log_file_name=LOG_FILE_NAME,
        timeouts=TIMEOUTS,
        default_timeout=DEFAULT_TIMEOUT,
        retryable_prefixes=RETRYABLE_PREFIXES,
        max_attempts_retryable=MAX_ATTEMPTS_RETRYABLE,
        sleep_between_retries_s=SLEEP_BETWEEN_RETRIES_S,
        backoff_max_s=BACKOFF_MAX_S,
        lock_file_name=LOCK_FILE_NAME,
        last_run_file_name=LAST_RUN_FILE,
        skip_if_ran_today=True,
        max_log_bytes=MAX_LOG_BYTES,
        keep_log_files=KEEP_LOG_FILES,
        auto_commit_paths=auto_commit_paths,
        auto_commit_message=AUTO_COMMIT_MESSAGE,
        auto_commit_repo_root=repo_root,
        base_dir=base_dir,
    )


if __name__ == "__main__":
    main()
