"""Out-of-process updater used by Dead Letter public builds.

The updater deliberately runs from the newly downloaded release rather than the
installed copy.  PyInstaller one-file applications can leave their outer
bootloader alive for a short moment after the Python child exits, so replacement
of DeadLetter.exe is retried instead of treating the first Windows file-lock
error as a fatal update failure.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            WAIT_TIMEOUT = 0x00000102
            result = ctypes.windll.kernel32.WaitForSingleObject(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
            return result == WAIT_TIMEOUT
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _data_dir() -> Path:
    if os.name == "nt" and os.environ.get("APPDATA"):
        path = Path(os.environ["APPDATA"]) / "DeadLetter"
    else:
        path = Path.home() / ".dead_letter"
    path.mkdir(parents=True, exist_ok=True)
    return path


LOG_PATH = _data_dir() / "update.log"


def _log(message: str):
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def _show_error(message: str):
    """Do not let a windowed updater fail silently."""
    _log(f"ERROR: {message}")
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                f"{message}\n\nDetails were written to:\n{LOG_PATH}",
                "Dead Letter Update Failed",
                0x10,
            )
        except Exception:
            pass


def _wait_for_game(pid: int, timeout: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            # A PyInstaller one-file bootloader can outlive the Python child
            # very briefly.  Give it a head start before replacing the EXE.
            time.sleep(0.8)
            return True
        time.sleep(0.25)
    return False


def _replace_file(src: Path, dest: Path, timeout: float = 30.0):
    """Atomically replace one file, retrying while Windows releases old images."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + ".deadletter-update")
    try:
        temp.unlink(missing_ok=True)
    except OSError:
        pass

    # Copy to a different filename first.  This can succeed even while the old
    # destination executable is still locked by the exiting bootloader.
    shutil.copy2(src, temp)
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            os.replace(temp, dest)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.25)
    try:
        temp.unlink(missing_ok=True)
    except OSError:
        pass
    if last_error:
        raise last_error
    raise OSError(f"Could not replace {dest.name}")


def _copy_release(source: Path, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    # Directories contain data/source files, not the running executable, so
    # merging them is safer than deleting the destination tree first.
    for item in source.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            _log(f"Installing {item.name}")
            _replace_file(item, dest)

    expected_version = (source / "VERSION.txt").read_text(encoding="utf-8").strip()
    installed_version = (target / "VERSION.txt").read_text(encoding="utf-8").strip()
    if installed_version != expected_version:
        raise OSError(
            f"Version verification failed (expected {expected_version}, found {installed_version})."
        )

    # These were visible release files in older builds but are now obsolete or
    # embedded inside the main executable.
    for obsolete in ("run_game.bat", "DeadLetter.ico", "DeadLetterUpdater.ico"):
        try:
            (target / obsolete).unlink(missing_ok=True)
        except OSError:
            pass


def _launch_game(target: Path):
    exe = target / "DeadLetter.exe"
    if exe.exists():
        subprocess.Popen([str(exe)], cwd=str(target))
        return
    pyw = target / "DeadLetter.pyw"
    main_py = target / "main.py"
    if os.name == "nt":
        candidate = pyw if pyw.exists() else main_py
        if candidate.exists():
            os.startfile(str(candidate))  # type: ignore[attr-defined]
        return
    candidate = pyw if pyw.exists() else main_py
    if candidate.exists() and not getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable, str(candidate)], cwd=str(target))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", required=True)
    args = ap.parse_args()
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()

    _log("=" * 60)
    _log(f"Updater started. source={source} target={target} pid={args.pid}")
    try:
        if not source.exists():
            raise FileNotFoundError(f"Staged release folder no longer exists: {source}")
        if not _wait_for_game(args.pid):
            raise TimeoutError("The previous Dead Letter process did not close in time.")

        _log("Previous game process closed; installing release.")
        _copy_release(source, target)
        version = (target / "VERSION.txt").read_text(encoding="utf-8").strip()
        _log(f"Installation verified as v{version}; relaunching.")
        _launch_game(target)
        _log("Update completed successfully.")
        return 0
    except Exception as exc:
        _log(traceback.format_exc())
        _show_error(str(exc) or exc.__class__.__name__)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
