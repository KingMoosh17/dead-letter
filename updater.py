"""Small out-of-process updater used by update_manager.py."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", required=True)
    args = ap.parse_args()
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()

    for _ in range(120):
        if not process_alive(args.pid):
            break
        time.sleep(0.25)
    else:
        return 2

    # Preserve only files that are intentionally local to the install and are
    # not part of the release package. Player data is elsewhere in AppData.
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

    # Relaunch through the GUI entry point when possible.
    entry = target / "DeadLetter.pyw"
    if not entry.exists():
        entry = target / "main.py"
    try:
        subprocess.Popen([sys.executable, str(entry)], cwd=str(target))
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
