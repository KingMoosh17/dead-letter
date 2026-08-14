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

BANK_EXAMPLES = {
    "standard": "ELEPHANT • QUARTZ • RHYTHM",
    "common_tongue": "HOUSE • MARKET • GARDEN",
    "bookish": "ARCHITECTURE • OBSERVATORY • MAGNITUDE",
    "quickfire": "JAZZ • GYM • SAFE",
    "labyrinth": "MYRRH • SYZYGY • QUEUE",
}


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
    old = GLYPHS["recovery_room"]
    GLYPHS["recovery_room"] = GlyphDef(
        old.id,
        old.name,
        old.rarity,
        "After your second mistake added to the meter each word, immediately restore 6 seconds.",
        old.category,
    )


def _selector(parent, text, command, selected=False, accent=None):
    """One shared selector control for difficulty and word-bank cards.

    It deliberately uses natural geometry: no fixed holder, no measured pixel
    height, no place() calls, and no native Button redraw state. This keeps the
    two sections visually identical while avoiding the Windows white flash that
    motivated the original Label-based selectors.
    """
    accent = accent or M.ACCENT
    bg = accent if selected else M.PANEL2
    fg = M.BG if selected else M.TEXT
    label = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        anchor="center",
        cursor="hand2",
        pady=8,
        bd=0,
        highlightthickness=0,
    )
    label.bind("<Button-1>", lambda _e: command())
    return label


def patched_show_start(self):
    """Simple natural-height New Run layout.

    v1.1.8 demonstrated that fixed-height cards plus post-layout geometry hacks
    were fighting Tk rather than helping it. There is ample screen space, so the
    entire screen now lets Tk size cards naturally. Difficulty and bank cards use
    the exact same selector component and no widget is repositioned after draw.
    """
    self.screen = "new_run"
    self.presentation_paused = True
    self.clear(self.main)
    self.clear(self.side)
    self._menu_chrome("New Run")

    outer = tk.Frame(self.main, bg=M.BG, padx=50, pady=20)
    outer.pack(fill="both", expand=True)

    top = tk.Frame(outer, bg=M.BG)
    top.pack(fill="x")
    tk.Label(
        top,
        text="NEW RUN",
        bg=M.BG,
        fg=M.TEXT,
        font=("Georgia", 28, "bold"),
    ).pack(side="left")
    self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")

    self._start_diff_widgets = {}
    self._start_bank_widgets = {}

    # Difficulty -----------------------------------------------------------
    tk.Label(
        outer,
        text="DIFFICULTY",
        bg=M.BG,
        fg=M.ACCENT,
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", pady=(15, 7))

    diff_row = tk.Frame(outer, bg=M.BG)
    diff_row.pack(fill="x")
    for col in range(3):
        diff_row.grid_columnconfigure(col, weight=1, uniform="difficulty")

    colors = {"easy": M.GOOD, "medium": M.ACCENT, "hard": M.BAD}
    for col, did in enumerate(("easy", "medium", "hard")):
        d = M.DIFFICULTIES[did]
        chosen = did == self.selected_difficulty
        color = colors[did]
        frame = tk.Frame(
            diff_row,
            bg=M.PANEL,
            padx=14,
            pady=11,
            highlightbackground=color if chosen else "#3b3b42",
            highlightthickness=2,
        )
        frame.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(
            frame,
            text=d.name.upper(),
            bg=M.PANEL,
            fg=color,
            font=("Georgia", 14, "bold"),
        ).pack(anchor="w")
        timing = "Standard time" if d.time_delta == 0 else f"{d.time_delta:+.0f}s starting time"
        plural = "s" if d.glyph_choices != 1 else ""
        options = f"{d.glyph_choices} Glyph / {d.axiom_choices} Axiom option{plural}"
        tk.Label(
            frame,
            text=f"{timing}  •  {options}",
            bg=M.PANEL,
            fg=M.MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 9))

        control = _selector(
            frame,
            "SELECTED" if chosen else "SELECT",
            lambda x=did: self.select_difficulty(x),
            chosen,
            color,
        )
        control.pack(fill="x")
        self._start_diff_widgets[did] = (frame, control, color)

    # Word banks -----------------------------------------------------------
    tk.Label(
        outer,
        text="WORD BANK",
        bg=M.BG,
        fg=M.ACCENT,
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", pady=(17, 7))

    bank_items = list(M.BANKS.items())
    bank_area = tk.Frame(outer, bg=M.BG)
    bank_area.pack(fill="x")

    for row_index, row_items in enumerate((bank_items[:3], bank_items[3:])):
        row = tk.Frame(bank_area, bg=M.BG)
        row.pack(fill="x", pady=(0, 8 if row_index == 0 else 0))
        for col in range(len(row_items)):
            row.grid_columnconfigure(col, weight=1, uniform=f"bank{row_index}")

        for col, (bid, bdef) in enumerate(row_items):
            chosen = bid == self.selected_bank_id
            frame = tk.Frame(
                row,
                bg=M.PANEL,
                padx=14,
                pady=11,
                highlightbackground=M.ACCENT if chosen else "#3b3b42",
                highlightthickness=2,
            )
            frame.grid(row=0, column=col, sticky="nsew", padx=4)

            title = tk.Label(
                frame,
                text=bdef.name.upper(),
                bg=M.PANEL,
                fg=M.ACCENT if chosen else M.TEXT,
                font=("Segoe UI", 11, "bold"),
            )
            title.pack(anchor="w")

            # Natural-height copy. Each row's grid automatically adopts the
            # tallest card, while the selector stays at the bottom via pack().
            tk.Label(
                frame,
                text=bdef.description,
                bg=M.PANEL,
                fg="#c7c7cd",
                wraplength=520,
                justify="left",
                anchor="nw",
                font=("Segoe UI", 10),
            ).pack(anchor="w", fill="x", pady=(5, 3))
            tk.Label(
                frame,
                text=f"Examples: {BANK_EXAMPLES.get(bid, '')}",
                bg=M.PANEL,
                fg=M.ACCENT,
                wraplength=520,
                justify="left",
                font=("Segoe UI", 8, "bold"),
            ).pack(anchor="w", pady=(0, 9))

            control = _selector(
                frame,
                "SELECTED" if chosen else "SELECT",
                lambda x=bid: self.select_word_bank(x),
                chosen,
                M.ACCENT,
            )
            control.pack(side="bottom", fill="x")
            self._start_bank_widgets[bid] = (frame, title, control)

    # Seed + start ---------------------------------------------------------
    setup = tk.Frame(
        outer,
        bg=M.PANEL,
        padx=18,
        pady=13,
        highlightbackground="#3b3b42",
        highlightthickness=1,
    )
    setup.pack(fill="x", pady=(16, 13))
    inner = tk.Frame(setup, bg=M.PANEL)
    inner.pack(anchor="center")
    tk.Label(
        inner,
        text="Seed (optional)",
        bg=M.PANEL,
        fg=M.TEXT,
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left", padx=(0, 12))
    self.seed_entry = tk.Entry(
        inner,
        bg=M.PANEL2,
        fg=M.TEXT,
        insertbackground=M.TEXT,
        relief="flat",
        width=32,
        font=("Consolas", 10),
    )
    self.seed_entry.pack(side="left", ipady=7, padx=(0, 14))
    tk.Label(
        inner,
        text="Same setup + seed reproduces the same rolls.",
        bg=M.PANEL,
        fg=M.MUTED,
        font=("Segoe UI", 9),
    ).pack(side="left")

    actions = tk.Frame(outer, bg=M.BG)
    actions.pack(fill="x")
    start = tk.Button(
        actions,
        text="START RUN",
        command=self.new_run,
        bg=M.ACCENT,
        fg=M.BG,
        activebackground="#e7be72",
        activeforeground=M.BG,
        relief="flat",
        bd=0,
        highlightthickness=0,
        takefocus=0,
        padx=36,
        pady=14,
        width=26,
        font=("Segoe UI", 13, "bold"),
        cursor="hand2",
    )
    start.pack(anchor="center")
    self._refresh_start_selection()


def patched_show_boss_intro(self):
    original_show_boss_intro(self)
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
