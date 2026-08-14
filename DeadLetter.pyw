"""Dead Letter public launcher.

When a packaged executable is present, source-mode double-clicks hand off to it.
The frozen executable runs the same module directly and applies the current
release presentation patches before constructing the Tkinter app.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VERSION = "1.1.6"


def _launch():
    here = Path(__file__).resolve().parent
    if not getattr(sys, "frozen", False) and os.environ.get("DEADLETTER_FORCE_SOURCE") != "1":
        exe = here / "DeadLetter.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(here))
            return

    import storage
    storage.GAME_VERSION = VERSION

    import telemetry
    telemetry.GAME_VERSION = VERSION

    import main
    main.GAME_VERSION = VERSION

    from ui_patch import apply_patch
    apply_patch(main)

    from release_patch import apply_patch as apply_release_patch
    apply_release_patch(main)

    main.main()


if __name__ == "__main__":
    _launch()
