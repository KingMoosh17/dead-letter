"""Dead Letter targeted release fixes.

Applied after ui_patch.py so small gameplay/UI hotfixes can ship without
rewriting the larger presentation module.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from content import BOSSES, GLYPHS, BossDef, GlyphDef
from game_logic import GameState

M = None


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def _replace_player_facing_definitions():
    # The Forbidden hides the identity of its blocked present letter until the
    # player actually tries it. That blocked attempt itself is harmless.
    BOSSES["forbidden"] = BossDef(
        "forbidden",
        "The Forbidden",
        "One present letter cannot be guessed directly. Its identity stays hidden until you try it; that blocked attempt does not count as a mistake.",
    )

    # "Charged mistake" was an internal distinction between an attempted
    # penalty and a penalty that survives protection such as Pencil Eraser.
    # Player-facing text now describes the meter directly instead.
    old = GLYPHS["recovery_room"]
    GLYPHS["recovery_room"] = GlyphDef(
        old.id,
        old.name,
        old.rarity,
        "After your second mistake added to the meter each word, immediately restore 6 seconds.",
        old.category,
    )


def patched_show_start(self):
    original_show_start(self)

    # Word-bank cards have a fixed height. The selector used to be packed after
    # all of the descriptive text, so Tk could squeeze the last-packed widget to
    # whatever vertical space happened to remain. Repack each card with the
    # selector FIRST on the bottom, which reserves exactly the same requested
    # selector height used by the difficulty cards before laying out the copy.
    for _bid, (frame, _title, selector) in getattr(self, "_start_bank_widgets", {}).items():
        try:
            packed = []
            for child in frame.winfo_children():
                if child.winfo_manager() == "pack":
                    packed.append((child, child.pack_info()))
            for child, _info in packed:
                child.pack_forget()

            selector.config(font=("Segoe UI", 9, "bold"), pady=6)
            selector_info = next((info for child, info in packed if child is selector), None)
            if selector_info is not None:
                selector.pack(**selector_info)
            else:
                selector.pack(side="bottom", fill="x")

            for child, info in packed:
                if child is selector:
                    continue
                child.pack(**info)
        except (tk.TclError, StopIteration):
            # Fallback for any platform-specific Tk geometry quirk.
            try:
                selector.config(font=("Segoe UI", 9, "bold"), pady=6)
            except tk.TclError:
                pass


def patched_show_boss_intro(self):
    original_show_boss_intro(self)
    # The Forbidden's identity must not be spoiled by the pre-Boss screen.
    if not self.game or not self.game.round or self.game.round.boss_id != "forbidden":
        return
    for widget in list(_walk(self.main)):
        try:
            text = str(widget.cget("text"))
        except (tk.TclError, AttributeError):
            continue
        if text.startswith("FORBIDDEN LETTER:"):
            widget.destroy()


def patched_show_tutorial(self, page=0):
    original_show_tutorial(self, page)
    if page != 0:
        return
    for widget in _walk(self.main):
        try:
            text = str(widget.cget("text"))
        except (tk.TclError, AttributeError):
            continue
        if "Six charged mistakes" in text:
            widget.config(text=text.replace(
                "Six charged mistakes or an empty timer ends the run.",
                "Six mistakes added to your meter, or an empty timer, ends the run.",
            ))


def patched_can_guess_letter(game, ch):
    # Let the existing Forbidden validation reject the letter, but remember that
    # the player has discovered its identity. No guessed-letter or mistake state
    # is changed, so the probing attempt remains harmless.
    letter = str(ch).lower()
    if (
        game.status == "playing"
        and game.round is not None
        and game.round.boss_id == "forbidden"
        and letter == game.round.forbidden_letter
    ):
        game.round.forbidden_revealed = True
    return original_can_guess_letter(game, ch)


def patched_round_info_text(game):
    text = original_round_info_text(game)
    r = game.round
    if (
        r is not None
        and r.boss_id == "forbidden"
        and getattr(r, "forbidden_revealed", False)
        and r.forbidden_letter
    ):
        reveal = f"Forbidden letter: {r.forbidden_letter.upper()}"
        return f"{text}  •  {reveal}" if text else reveal
    return text


def patched_check_updates_async(self, notify=False):
    """Keep network failure distinct from a genuine up-to-date result."""
    if self.update_checking:
        return
    self.update_checking = True

    def worker():
        info = self.update_manager.check_latest()
        error = getattr(self.update_manager, "last_error", "")

        def done():
            self.update_checking = False
            self.available_update = info
            if self.screen == "menu" and info:
                self._show_update_button()
            if notify:
                if info:
                    messagebox.showinfo("Update available", f"Dead Letter v{info.version} is available.")
                elif error:
                    messagebox.showwarning(
                        "Update check failed",
                        "Dead Letter could not reach the release service.\n\n"
                        f"{error}\n\nTry again in a moment.",
                    )
                else:
                    messagebox.showinfo("Updates", f"Dead Letter v{M.GAME_VERSION} is up to date.")

        self.root.after(0, done)

    threading.Thread(target=worker, daemon=True).start()


def apply_patch(main_module):
    global M
    global original_show_start, original_show_boss_intro, original_show_tutorial
    global original_can_guess_letter, original_round_info_text

    M = main_module
    _replace_player_facing_definitions()

    cls = main_module.DeadLetterApp
    original_show_start = cls.show_start
    original_show_boss_intro = cls.show_boss_intro
    original_show_tutorial = cls.show_tutorial
    original_can_guess_letter = GameState.can_guess_letter
    original_round_info_text = GameState.round_info_text

    cls.show_start = patched_show_start
    cls.show_boss_intro = patched_show_boss_intro
    cls.show_tutorial = patched_show_tutorial
    cls._check_updates_async = patched_check_updates_async
    GameState.can_guess_letter = patched_can_guess_letter
    GameState.round_info_text = patched_round_info_text
