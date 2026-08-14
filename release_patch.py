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


def _replace_selector_at_rendered_geometry(frame, old_selector, text, command, selected, accent, target_height):
    """Replace a selector using its *rendered* Windows geometry.

    Tk can report one requested height and then render the difficulty selector
    at a larger physical height after DPI/font scaling. We therefore measure the
    already-rendered difficulty selectors, use that real pixel height as the
    target, grow shorter bank cards by exactly the difference, and place the new
    control at explicit pixel geometry. The packer can no longer squeeze it.
    """
    try:
        x = int(old_selector.winfo_x())
        y = int(old_selector.winfo_y())
        width = int(old_selector.winfo_width())
        old_height = int(old_selector.winfo_height())
        frame_height = int(frame.winfo_height())
    except tk.TclError:
        x, y, width, old_height, frame_height = 14, 0, 1, target_height, 1

    grow = max(0, int(target_height) - max(1, old_height))
    if grow:
        try:
            frame.config(height=max(1, frame_height + grow))
            frame.pack_propagate(False)
        except tk.TclError:
            pass

    try:
        old_selector.destroy()
    except tk.TclError:
        pass

    bg = accent if selected else M.PANEL2
    fg = M.BG if selected else M.TEXT
    label = tk.Label(
        frame,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
        anchor="center",
        bd=0,
        highlightthickness=0,
    )
    label.bind("<Button-1>", lambda _e: command())

    if width > 1:
        # Keep the exact horizontal inset/width of the selector that ui_patch
        # already laid out, but force the physical height to match Difficulty.
        label.place(x=x, y=y, width=width, height=int(target_height))
    else:
        label.place(relx=0, x=14, y=y, relwidth=1, width=-28, height=int(target_height))
    return label


def patched_show_start(self):
    original_show_start(self)

    # Measure what Windows ACTUALLY rendered, not winfo_reqheight(). This is the
    # key difference from v1.1.7 and makes the fix respect DPI/Tk font scaling.
    try:
        self.root.update_idletasks()
        rendered_diff_heights = [
            int(selector.winfo_height())
            for _did, (_frame, selector, _color) in getattr(self, "_start_diff_widgets", {}).items()
            if int(selector.winfo_height()) > 1
        ]
        selector_height = max(rendered_diff_heights) if rendered_diff_heights else 34
    except (tk.TclError, ValueError):
        selector_height = 34

    new_diff = {}
    for did, (frame, selector, color) in list(getattr(self, "_start_diff_widgets", {}).items()):
        chosen = did == self.selected_difficulty
        replacement = _replace_selector_at_rendered_geometry(
            frame,
            selector,
            "SELECTED" if chosen else "SELECT",
            lambda x=did: self.select_difficulty(x),
            chosen,
            color,
            selector_height,
        )
        new_diff[did] = (frame, replacement, color)
    self._start_diff_widgets = new_diff

    new_banks = {}
    for bid, (frame, title, selector) in list(getattr(self, "_start_bank_widgets", {}).items()):
        chosen = bid == self.selected_bank_id
        replacement = _replace_selector_at_rendered_geometry(
            frame,
            selector,
            "SELECTED" if chosen else "SELECT",
            lambda x=bid: self.select_word_bank(x),
            chosen,
            M.ACCENT,
            selector_height,
        )
        new_banks[bid] = (frame, title, replacement)
    self._start_bank_widgets = new_banks

    # Let parent rows react to any bank-card growth, then verify/enforce the
    # physical selector height one more time after Tk has completed layout.
    self.root.update_idletasks()
    for _bid, (_frame, _title, selector) in self._start_bank_widgets.items():
        try:
            if int(selector.winfo_height()) != int(selector_height):
                info = selector.place_info()
                selector.place_configure(height=int(selector_height))
        except tk.TclError:
            pass
    self._refresh_start_selection()


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
