import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")


def now_ts() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def tail_file(path: Path, n_lines: int = 300) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-n_lines:])
    except Exception:
        return ""


def run_pipeline(
    scripts: list[str],
    log_file_name: str,
    timeouts: dict[str, int] | None = None,
    default_timeout: int = 15 * 60,
    retryable_prefixes: tuple[str, ...] = (),
    max_attempts_retryable: int = 3,
    sleep_between_retries_s: int = 60,
    backoff_max_s: int = 300,
    base_dir: Path | None = None,
    lock_file_name: str | None = None,
    lock_timeout_s: int = 6 * 60 * 60,
    last_run_file_name: str | None = None,
    skip_if_ran_today: bool = False,
    max_log_bytes: int | None = None,
    keep_log_files: int = 5,
    auto_commit_paths: list[Path] | None = None,
    auto_commit_message: str | None = None,
    auto_commit_repo_root: Path | None = None,
) -> None:
    base_dir = base_dir or Path(__file__).resolve().parent
    log_path = base_dir / log_file_name
    timeouts = timeouts or {}

    if max_log_bytes:
        _rotate_logs(log_path, max_log_bytes=max_log_bytes, keep=keep_log_files)

    lock_path = base_dir / lock_file_name if lock_file_name else None
    if lock_path:
        _acquire_lock(lock_path, lock_timeout_s=lock_timeout_s)

    try:
        if last_run_file_name and skip_if_ran_today:
            last_run_path = base_dir / last_run_file_name
            if _ran_today(last_run_path):
                print(f"[INFO] Ya se ejecutó hoy ({last_run_path.read_text().strip()}).")
                return

        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "#" * 90 + "\n")
            f.write(f"PIPELINE START {now_ts()}\n")

        for name in scripts:
            py = base_dir / name
            if not py.exists():
                raise FileNotFoundError(f"No existe el script: {py}")
            _run_step(
                py=py,
                log_path=log_path,
                timeout_s=timeouts.get(name, default_timeout),
                retryable_prefixes=retryable_prefixes,
                max_attempts_retryable=max_attempts_retryable,
                sleep_between_retries_s=sleep_between_retries_s,
                backoff_max_s=backoff_max_s,
            )

        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"PIPELINE END   {now_ts()}\n")

        if last_run_file_name:
            last_run_path = base_dir / last_run_file_name
            try:
                last_run_path.write_text(_today().isoformat(), encoding="utf-8")
            except Exception:
                pass

        if auto_commit_paths and auto_commit_message and auto_commit_repo_root:
            _auto_commit_files(
                repo_root=auto_commit_repo_root,
                file_paths=auto_commit_paths,
                message=auto_commit_message,
            )

        print(f"[OK] PIPELINE COMPLETADO. Log: {log_path}")
    finally:
        if lock_path:
            _release_lock(lock_path)


def _run_step(
    py: Path,
    log_path: Path,
    timeout_s: int,
    retryable_prefixes: tuple[str, ...],
    max_attempts_retryable: int,
    sleep_between_retries_s: int,
    backoff_max_s: int,
) -> None:
    cmd = [sys.executable, "-X", "utf8", str(py)]
    attempts = max_attempts_retryable if _is_retryable(py.name, retryable_prefixes) else 1

    last_code = None
    last_error = None

    for attempt in range(1, attempts + 1):
        start = time.time()
        ts = now_ts()

        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 90 + "\n")
            f.write(f"[{ts}] RUN (attempt {attempt}/{attempts}) | timeout={timeout_s}s\n")
            f.write(f"[{ts}] CMD: {' '.join(cmd)}\n")
            f.flush()

            p = subprocess.Popen(
                cmd,
                cwd=str(py.parent),
                stdout=f,
                stderr=f,
                text=True,
                env=os.environ.copy(),
            )

            try:
                code = p.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                f.write(f"[{now_ts()}] TIMEOUT -> KILL {py.name}\n")
                try:
                    p.kill()
                except Exception:
                    pass
                code = 124
                last_error = "timeout"
            except Exception as e:
                f.write(f"[{now_ts()}] ERROR waiting process: {repr(e)}\n")
                try:
                    p.kill()
                except Exception:
                    pass
                code = 125
                last_error = repr(e)

            dur = time.time() - start
            f.write(f"[{now_ts()}] EXIT={code} | dur={dur:.1f}s | {py.name}\n")

        last_code = code

        if code == 0:
            return

        if not _is_retryable(py.name, retryable_prefixes):
            break

        if attempt < attempts:
            delay = min(sleep_between_retries_s * (2 ** (attempt - 1)), backoff_max_s)
            time.sleep(delay)

    print("\n" + "!" * 90)
    print(f"[ERROR] Fallo: {py.name} (exit={last_code})")
    if last_error:
        print(f"[INFO] Motivo: {last_error}")
    print("[INFO] Ultimas lineas del log:\n")
    print(tail_file(log_path, n_lines=350))
    print("!" * 90 + "\n")
    raise RuntimeError(f"Fallo {py.name} (exit={last_code}). Mira el log: {log_path}")


def _is_retryable(script_name: str, prefixes: tuple[str, ...]) -> bool:
    return script_name.startswith(prefixes)


def _rotate_logs(log_path: Path, max_log_bytes: int, keep: int) -> None:
    try:
        if not log_path.exists():
            return
        if log_path.stat().st_size < max_log_bytes:
            return
        ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
        rotated = log_path.with_name(f"{log_path.stem}.{ts}{log_path.suffix}")
        log_path.rename(rotated)

        rotated_logs = sorted(
            log_path.parent.glob(f"{log_path.stem}.*{log_path.suffix}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in rotated_logs[keep:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass


def _today() -> date:
    return datetime.now(TZ).date()


def _ran_today(last_run_path: Path) -> bool:
    try:
        raw = last_run_path.read_text(encoding="utf-8").strip()
        if not raw:
            return False
        return date.fromisoformat(raw) == _today()
    except Exception:
        return False


def _acquire_lock(lock_path: Path, lock_timeout_s: int) -> None:
    if lock_path.exists():
        age = time.time() - lock_path.stat().st_mtime
        if age < lock_timeout_s:
            raise RuntimeError(f"Pipeline en ejecucion (lock activo): {lock_path}")
        try:
            lock_path.unlink()
        except Exception:
            pass
    payload = f"pid={os.getpid()} time={now_ts()}\n"
    lock_path.write_text(payload, encoding="utf-8")


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except Exception:
        pass


def _auto_commit_files(repo_root: Path, file_paths: list[Path], message: str) -> None:
    repo_root = repo_root.resolve()
    existing = [p for p in file_paths if p.exists()]
    if not existing:
        return

    rel_paths = [str(p.resolve().relative_to(repo_root)) for p in existing]

    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--"] + rel_paths,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0 or not status.stdout.strip():
        return

    add = subprocess.run(
        ["git", "-C", str(repo_root), "add", "--"] + rel_paths,
        capture_output=True,
        text=True,
    )
    if add.returncode != 0:
        return

    commit = subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-m", message],
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0:
        return
