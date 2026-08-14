"""Out-of-process updater used by Dead Letter public builds."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
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
            try:
                os.startfile(str(candidate))  # type: ignore[attr-defined]
            except OSError:
                pass
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

    for _ in range(160):
        if not process_alive(args.pid):
            break
        time.sleep(0.25)
    else:
        return 2

    target.mkdir(parents=True, exist_ok=True)
    for obsolete in ("run_game.bat",):
        try:
            (target / obsolete).unlink(missing_ok=True)
        except OSError:
            pass

    for item in source.iterdir():
        dest = target / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        except OSError:
            return 3

    _launch_game(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
