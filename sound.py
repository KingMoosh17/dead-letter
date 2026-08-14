"""Tiny standard-library sound manager. Uses winsound on Windows."""
from __future__ import annotations
import os
from pathlib import Path

try:
    import winsound
except ImportError:  # non-Windows
    winsound = None


class SoundManager:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.enabled = True

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled

    def play(self, name: str):
        if not self.enabled:
            return
        path = self.root / f"{name}.wav"
        if winsound is not None and path.exists():
            try:
                winsound.PlaySound(
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
            except RuntimeError:
                pass
