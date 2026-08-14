from __future__ import annotations
import time
import os
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from content import GLYPHS, AXIOMS, BOSSES, DIFFICULTIES
from wordbank import WordBank, BANKS
from game_logic import GameState
from sound import SoundManager
from storage import Storage, GAME_VERSION
from update_manager import UpdateManager

BG = "#171719"
PANEL = "#222226"
PANEL2 = "#2b2b31"
TEXT = "#f2eee5"
MUTED = "#aaa7a0"
ACCENT = "#d8aa55"
BAD = "#d26767"
GOOD = "#79b98a"
BLUE = "#6f9fc9"
PURPLE = "#a98bd4"
RARITY_COLOR = {"Common": MUTED, "Uncommon": BLUE, "Rare": PURPLE}


class DeadLetterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.storage = Storage()
        self.settings = self.storage.settings
        self.root.title(f"Dead Letter — Hangman Roguelike v{GAME_VERSION}")
        self.root.geometry(self.settings.get("resolution", "1280x800"))
        self.root.minsize(1060, 700)
        self.root.configure(bg=BG)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.data_path = Path(__file__).resolve().parent / "data" / "words.csv"
        self.sound = SoundManager(self.data_path.parent / "sfx")
        self.sound.enabled = bool(self.settings.get("sound_enabled", True))
        try:
            self.bank = WordBank(self.data_path, "standard")
        except Exception as exc:
            messagebox.showerror("Word bank error", str(exc))
            raise
        self.game: GameState | None = None
        self.screen = "title"
        self.selected_difficulty = "medium"
        self.selected_bank_id = "standard"
        self.update_manager = UpdateManager(Path(__file__).resolve().parent, GAME_VERSION)
        self.available_update = None
        self.update_checking = False
        self.last_clock = time.perf_counter()
        self.letter_buttons = {}
        self.presentation_paused = False
        self.boss_intro_seen: set[int] = set()
        # Presentation-only state. None of this changes gameplay rules.
        self.danger_sound_round = None
        self.danger_pulse_phase = False
        self._animation_jobs: set[str] = set()
        self._build_shell()
        self.apply_display_settings()
        self.show_title()
        self.root.bind("<KeyPress>", self.on_key)
        self.root.bind("<F11>", self._quick_display_toggle)
        self.root.protocol("WM_DELETE_WINDOW", self.request_quit)
        self.root.after(50, self.loop)

    def _build_shell(self):
        self.header = tk.Frame(self.root, bg=BG, padx=24, pady=16)
        self.header.pack(fill="x")
        self.title_label = tk.Label(self.header, text="DEAD LETTER", bg=BG, fg=TEXT,
                                    font=("Georgia", 22, "bold"))
        self.title_label.pack(side="left")
        self.header_info = tk.Label(self.header, text="", bg=BG, fg=MUTED,
                                    font=("Segoe UI", 10))
        self.header_info.pack(side="right")
        self.sound_button = tk.Button(self.header, text="SOUND ON", command=self.toggle_sound,
                                      bg=PANEL2, fg=MUTED, activebackground=PANEL2,
                                      activeforeground=TEXT, relief="flat", padx=9, pady=3,
                                      font=("Segoe UI", 8, "bold"))
        self.sound_button.pack(side="right", padx=(0, 12))
        self.sound_button.config(text="SOUND ON" if self.sound.enabled else "SOUND OFF",
                                 fg=MUTED if self.sound.enabled else BAD)
        self.restart_button = tk.Button(self.header, text="RESTART", command=self.restart_run,
                                        bg="#352326", fg="#efb7b7", activebackground="#4a2d31",
                                        activeforeground=TEXT, relief="flat", padx=9, pady=3,
                                        font=("Segoe UI", 8, "bold"))

        # Thin letterpress-style rule gives the otherwise simple UI a stronger frame.
        self.header_rule = tk.Frame(self.root, bg=ACCENT, height=2)
        self.header_rule.pack(fill="x")

        self.body = tk.Frame(self.root, bg=BG, padx=20, pady=4)
        self.body.pack(fill="both", expand=True)
        self.main = tk.Frame(self.body, bg=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self.side = tk.Frame(self.body, bg=PANEL, width=365, padx=14, pady=14)
        self.side.pack(side="right", fill="y")
        self.side.pack_propagate(False)

    def clear(self, widget):
        for child in widget.winfo_children():
            child.destroy()

    def _hide_side(self):
        if self.side.winfo_manager():
            self.side.pack_forget()

    def _show_side(self):
        if not self.side.winfo_manager():
            self.side.pack(side="right", fill="y")

    def _menu_chrome(self, info=""):
        self._hide_side()
        self.title_label.config(text="")
        self.header_info.config(text=info)
        self.sound_button.pack_forget()
        self.restart_button.pack_forget()

    def _run_chrome(self):
        self._show_side()
        self.title_label.config(text="DEAD LETTER")
        if not self.sound_button.winfo_manager():
            self.sound_button.pack(side="right", padx=(0, 12), before=self.header_info)
        if not self.restart_button.winfo_manager():
            self.restart_button.pack(side="right", padx=(0, 8), before=self.sound_button)
        self.sound_button.config(text="SOUND ON" if self.sound.enabled else "SOUND OFF",
                                 fg=MUTED if self.sound.enabled else BAD)

    def _menu_button(self, parent, text, command, primary=False, state="normal", width=26):
        bg = ACCENT if primary else PANEL2
        fg = BG if primary else TEXT
        active = "#e7be72" if primary else "#393940"
        btn = tk.Button(parent, text=text, command=command, state=state,
                        bg=bg, fg=fg, activebackground=active, activeforeground=fg,
                        disabledforeground="#64646c", relief="flat", bd=0,
                        padx=18, pady=9, width=width,
                        font=("Segoe UI", 10, "bold"), cursor="hand2" if state == "normal" else "")
        if state == "normal" and not primary:
            btn.bind("<Enter>", lambda _e, b=btn: b.config(bg="#34343b"))
            btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=PANEL2))
        return btn

    def apply_display_settings(self):
        mode = self.settings.get("display_mode", "fullscreen")
        if os.environ.get("DEADLETTER_TEST_MODE"):
            mode = "windowed"
        try:
            self.root.attributes("-fullscreen", False)
            self.root.overrideredirect(False)
        except tk.TclError:
            pass
        self.root.update_idletasks()
        if mode == "fullscreen":
            try:
                self.root.attributes("-fullscreen", True)
            except tk.TclError:
                pass
        elif mode == "borderless":
            try:
                self.root.overrideredirect(True)
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                self.root.geometry(f"{sw}x{sh}+0+0")
            except tk.TclError:
                pass
        else:
            resolution = self.settings.get("resolution", "1280x800")
            try:
                w, h = [int(x) for x in resolution.lower().split("x", 1)]
            except (ValueError, TypeError):
                w, h = 1280, 800
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _quick_display_toggle(self, _event=None):
        self.settings["display_mode"] = (
            "windowed" if self.settings.get("display_mode") in {"fullscreen", "borderless"} else "fullscreen"
        )
        self.storage.save_settings()
        self.apply_display_settings()
        return "break"

    def request_quit(self):
        if self.game and self.game.status == "playing":
            if not messagebox.askyesno(
                "Quit Dead Letter",
                "A word is currently timed and cannot be saved. Quit and lose this run?",
            ):
                return
            self.storage.finalize_run(self.game)
        elif self.game and self.game.can_save() and self.game.status != "won":
            choice = messagebox.askyesnocancel(
                "Quit Dead Letter",
                "This is a safe screen. Save this run before quitting?",
            )
            if choice is None:
                return
            if choice:
                try:
                    payload = self.game.to_save_dict()
                    if not self.storage.save_run_payload(payload):
                        messagebox.showerror("Save failed", "Could not write the run save file.")
                        return
                except (TypeError, ValueError) as exc:
                    messagebox.showerror("Save failed", str(exc))
                    return
            else:
                self.storage.finalize_run(self.game)
        elif self.game and self.game.status == "won":
            self.storage.finalize_run(self.game)
        self.root.destroy()

    def show_title(self):
        self.screen = "title"
        self.presentation_paused = True
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome(f"v{GAME_VERSION}")
        canvas = tk.Canvas(self.main, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.title_canvas = canvas

        def redraw(_event=None):
            if self.screen != "title" or not canvas.winfo_exists():
                return
            canvas.delete("static")
            w = max(900, canvas.winfo_width())
            h = max(620, canvas.winfo_height())
            # Subtle page frame / letterpress rules.
            canvas.create_rectangle(42, 34, w - 42, h - 34, outline="#2f2f34", width=1, tags="static")
            canvas.create_line(72, 80, w - 72, 80, fill="#6a5432", width=1, tags="static")
            canvas.create_line(72, h - 78, w - 72, h - 78, fill="#6a5432", width=1, tags="static")
            # Stylized gallows built from basic shapes.
            gx = int(w * 0.73)
            gy = int(h * 0.30)
            fg = "#746f67"
            canvas.create_line(gx - 120, gy + 245, gx + 95, gy + 245, fill=fg, width=5, tags="static")
            canvas.create_line(gx - 80, gy + 245, gx - 80, gy - 65, fill=fg, width=5, tags="static")
            canvas.create_line(gx - 82, gy - 65, gx + 55, gy - 65, fill=fg, width=5, tags="static")
            canvas.create_line(gx + 55, gy - 65, gx + 55, gy - 10, fill=fg, width=3, tags="static")
            canvas.create_oval(gx + 25, gy - 10, gx + 85, gy + 50, outline="#b0aaa0", width=3, tags="static")
            canvas.create_line(gx + 55, gy + 50, gx + 55, gy + 145, fill="#b0aaa0", width=3, tags="static")
            canvas.create_line(gx + 55, gy + 80, gx + 12, gy + 118, fill="#b0aaa0", width=3, tags="static")
            canvas.create_line(gx + 55, gy + 80, gx + 98, gy + 118, fill="#b0aaa0", width=3, tags="static")
            canvas.create_line(gx + 55, gy + 145, gx + 20, gy + 205, fill="#b0aaa0", width=3, tags="static")
            canvas.create_line(gx + 55, gy + 145, gx + 90, gy + 205, fill="#b0aaa0", width=3, tags="static")
            # Wax-seal-like circle gives the mark some identity without sprite art.
            canvas.create_oval(gx + 118, gy + 176, gx + 172, gy + 230, fill="#6f2c31", outline="#a64a50", width=2, tags="static")
            canvas.create_text(gx + 145, gy + 203, text="DL", fill="#e8d8c7",
                               font=("Georgia", 12, "bold"), tags="static")

            tx = int(w * 0.31)
            canvas.create_text(tx, int(h * 0.35), text="DEAD LETTER", fill=TEXT,
                               font=("Georgia", 48, "bold"), tags="static")
            canvas.create_text(tx, int(h * 0.35) + 62, text="A  H A N G M A N  R O G U E L I K E",
                               fill=ACCENT, font=("Segoe UI", 11, "bold"), tags="static")
            canvas.create_text(tx, int(h * 0.35) + 108,
                               text="Every letter is information. Every mistake has a cost.",
                               fill=MUTED, font=("Segoe UI", 11), tags="static")
            canvas.create_text(tx, h - 128, text="PRESS ANY KEY",
                               fill=ACCENT, font=("Segoe UI", 11, "bold"), tags=("static", "prompt"))
            canvas.create_text(tx, h - 100, text="or click to continue",
                               fill="#6e6b66", font=("Segoe UI", 8), tags="static")

        canvas.bind("<Configure>", redraw)
        canvas.bind("<Button-1>", lambda _e: self.show_main_menu())
        redraw()

        def pulse(on=True):
            if self.screen != "title" or not canvas.winfo_exists():
                return
            canvas.itemconfigure("prompt", fill=ACCENT if on else "#7a6849")
            self.root.after(620, lambda: pulse(not on))
        pulse()
        self.root.focus_set()

    def show_main_menu(self):
        self.screen = "menu"
        self.presentation_paused = True
        self.game = None
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome(f"v{GAME_VERSION}  •  5 word banks")

        outer = tk.Frame(self.main, bg=BG, padx=55, pady=32)
        outer.pack(fill="both", expand=True)
        left = tk.Frame(outer, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(20, 45))
        right = tk.Frame(outer, bg=PANEL, width=360, padx=22, pady=22,
                         highlightbackground="#393940", highlightthickness=1)
        right.pack(side="right", fill="y", padx=(0, 20))
        right.pack_propagate(False)

        tk.Label(left, text="DEAD LETTER", bg=BG, fg=TEXT,
                 font=("Georgia", 38, "bold")).pack(anchor="w", pady=(32, 2))
        tk.Label(left, text="A HANGMAN ROGUELIKE", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 28))

        buttons = tk.Frame(left, bg=BG)
        buttons.pack(anchor="w")
        has_save = self.storage.has_run_save()
        self._menu_button(buttons, "CONTINUE RUN", self.continue_saved_run,
                          primary=has_save, state="normal" if has_save else "disabled").pack(pady=4, anchor="w")
        self._menu_button(buttons, "NEW RUN", self.show_start, primary=not has_save).pack(pady=4, anchor="w")
        self._menu_button(buttons, "TUTORIAL", lambda: self.show_tutorial(0)).pack(pady=4, anchor="w")
        self._menu_button(buttons, "STATS", self.show_stats).pack(pady=4, anchor="w")
        self._menu_button(buttons, "COMPENDIUM", lambda: self.show_compendium("glyphs")).pack(pady=4, anchor="w")
        self._menu_button(buttons, "SETTINGS", self.show_settings).pack(pady=4, anchor="w")
        self.update_button_holder = tk.Frame(buttons, bg=BG)
        self.update_button_holder.pack(anchor="w")
        if self.available_update:
            self._show_update_button()
        self._menu_button(buttons, "QUIT", self.request_quit).pack(pady=(18, 4), anchor="w")
        if self.settings.get("check_updates", True) and not self.available_update:
            self._check_updates_async()

        stats = self.storage.stats
        tk.Label(right, text="PLAYER RECORD", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        record_lines = [
            ("Longest run", f"{stats['longest_run_words']} words"),
            ("Highest Chapter", str(stats['highest_chapter'])),
            ("Main-run wins", f"{stats['main_wins']}"),
            ("Words solved", f"{stats['words_solved']:,}"),
            ("Best run score", f"{stats['best_run_points']:,}"),
        ]
        for label, value in record_lines:
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, bg=PANEL, fg=MUTED).pack(side="left")
            tk.Label(row, text=value, bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 9, "bold")).pack(side="right")

        tk.Frame(right, bg="#3a3a40", height=1).pack(fill="x", pady=16)
        tk.Label(right, text="CONTENTS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(right, text=f"{len(GLYPHS)} Glyphs\n{len(AXIOMS)} Axioms\n{len(BOSSES)} Bosses",
                 bg=PANEL, fg=TEXT, justify="left", font=("Segoe UI", 10)).pack(anchor="w", pady=8)
        tk.Label(right, text="F11 toggles fullscreen/windowed.", bg=PANEL, fg="#77777e",
                 font=("Segoe UI", 8)).pack(anchor="w", side="bottom")
        self.sound.play("menu")

    def show_tutorial(self, page=0):
        self.screen = "tutorial"
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome("Tutorial")
        pages = [
            ("1. Solve the word",
             "Guess A–Z. Six charged mistakes or an empty timer ends the run.",
             ["Press / for a full-word guess.", "Wrong full-word guesses normally cost 2 mistakes."]),
            ("2. Read the difficulty",
             "Complexity estimates Hangman difficulty, not word length.",
             ["Complexity rises while time falls.", "Cleaner, faster solves earn more Points."]),
            ("3. Build with Glyphs",
             "After each solve, take one Glyph. Slots are limited; spend Points to reroll.",
             ["Glyphs alter information, time, accuracy, economy, structure, risk, and scaling.", "Trash unwanted Glyphs on safe screens."]),
            ("4. Prepare for Bosses",
             "Every Chapter ends with a previewed Boss that changes a rule.",
             ["Some Bosses strongly punish specific builds.", "Beat a Boss to choose a permanent Axiom."]),
            ("5. Saves & Endless",
             "Save & Exit is available only while the timer is stopped.",
             ["Beat Chapter 8 to win.", "Continue into Endless if you want to push the run farther."]),
        ]
        page = max(0, min(len(pages) - 1, page))
        title, body, bullets = pages[page]
        outer = tk.Frame(self.main, bg=BG, padx=65, pady=40)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="HOW TO PLAY", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(outer, text=title, bg=BG, fg=TEXT,
                 font=("Georgia", 26, "bold")).pack(anchor="w", pady=(5, 16))
        card = tk.Frame(outer, bg=PANEL, padx=24, pady=24,
                        highlightbackground="#3d3d44", highlightthickness=1)
        card.pack(fill="x")
        tk.Label(card, text=body, bg=PANEL, fg=TEXT, justify="left",
                 wraplength=800, font=("Segoe UI", 11)).pack(anchor="w")
        for item in bullets:
            tk.Label(card, text=f"•  {item}", bg=PANEL, fg=MUTED, justify="left",
                     wraplength=800, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        progress = tk.Canvas(outer, bg=BG, height=24, highlightthickness=0)
        progress.pack(fill="x", pady=18)
        for i in range(len(pages)):
            x = 14 + i * 30
            progress.create_oval(x, 7, x + 10, 17,
                                 fill=ACCENT if i == page else PANEL2, outline="")
        nav = tk.Frame(outer, bg=BG)
        nav.pack(fill="x")
        self._menu_button(nav, "BACK", lambda: self.show_tutorial(page - 1) if page else self.show_main_menu(), width=12).pack(side="left")
        if page < len(pages) - 1:
            self._menu_button(nav, "NEXT", lambda: self.show_tutorial(page + 1), primary=True, width=12).pack(side="right")
        else:
            def finish():
                self.settings["tutorial_seen"] = True
                self.storage.save_settings()
                self.show_main_menu()
            self._menu_button(nav, "DONE", finish, primary=True, width=12).pack(side="right")

    def show_stats(self):
        self.screen = "stats"
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome("Player Stats")
        stats = self.storage.stats
        outer = tk.Frame(self.main, bg=BG, padx=55, pady=35)
        outer.pack(fill="both", expand=True)
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="PLAYER STATS", bg=BG, fg=TEXT,
                 font=("Georgia", 27, "bold")).pack(side="left")
        self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")

        metrics = [
            ("Runs started", f"{stats['runs_started']:,}"),
            ("Main wins", f"{stats['main_wins']:,}"),
            ("Longest run", f"{stats['longest_run_words']} words"),
            ("Highest Chapter", f"{stats['highest_chapter']}"),
            ("Words solved", f"{stats['words_solved']:,}"),
            ("Bosses defeated", f"{stats['bosses_defeated']:,}"),
            ("Perfect words", f"{stats['perfect_words']:,}"),
            ("Full-word solves", f"{stats['full_word_solves']:,}"),
            ("Best run Points", f"{stats['best_run_points']:,}"),
            ("Total Points earned", f"{stats['total_points_earned']:,}"),
            ("Highest Complexity", f"{float(stats['highest_complexity_solved']):.2f}"),
            ("Endless entries", f"{stats['endless_runs']:,}"),
        ]
        grid = tk.Frame(outer, bg=BG)
        grid.pack(fill="x", pady=24)
        for i, (label, value) in enumerate(metrics):
            card = tk.Frame(grid, bg=PANEL, padx=16, pady=13,
                            highlightbackground="#3b3b42", highlightthickness=1)
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=5, pady=5)
            grid.grid_columnconfigure(i % 4, weight=1)
            tk.Label(card, text=value, bg=PANEL, fg=ACCENT,
                     font=("Georgia", 16, "bold")).pack(anchor="w")
            tk.Label(card, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")

        tk.Label(outer, text="BY DIFFICULTY", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 5))
        row = tk.Frame(outer, bg=BG)
        row.pack(fill="x")
        for did in ("easy", "medium", "hard"):
            d = stats["best_by_difficulty"].get(did, {})
            card = tk.Frame(row, bg=PANEL, padx=16, pady=13,
                            highlightbackground="#3b3b42", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(card, text=DIFFICULTIES[did].name.upper(), bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card,
                     text=f"Runs {d.get('runs',0)}  •  Wins {d.get('wins',0)}\nLongest {d.get('longest_words',0)} words  •  Best {d.get('best_points',0):,} Points",
                     bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", pady=(5,0))

    def show_compendium(self, tab="glyphs"):
        self.screen = "compendium"
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome("Compendium")
        outer = tk.Frame(self.main, bg=BG, padx=45, pady=28)
        outer.pack(fill="both", expand=True)
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="COMPENDIUM", bg=BG, fg=TEXT,
                 font=("Georgia", 26, "bold")).pack(side="left")
        self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")

        tabs = tk.Frame(outer, bg=BG)
        tabs.pack(fill="x", pady=(15, 8))
        for key, label in (("glyphs", f"GLYPHS ({len(GLYPHS)})"),
                           ("axioms", f"AXIOMS ({len(AXIOMS)})"),
                           ("bosses", f"BOSSES ({len(BOSSES)})")):
            btn = tk.Button(tabs, text=label, command=lambda k=key: self.show_compendium(k),
                            bg=ACCENT if key == tab else PANEL2,
                            fg=BG if key == tab else TEXT, relief="flat", padx=16, pady=6,
                            font=("Segoe UI", 9, "bold"))
            btn.pack(side="left", padx=(0, 6))

        filter_row = tk.Frame(outer, bg=BG)
        filter_row.pack(fill="x", pady=(0, 8))
        tk.Label(filter_row, text="Search:", bg=BG, fg=MUTED).pack(side="left", padx=(0, 6))
        search_var = tk.StringVar()
        entry = tk.Entry(filter_row, textvariable=search_var, bg=PANEL2, fg=TEXT,
                         insertbackground=TEXT, relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=5)

        wrap = tk.Frame(outer, bg=BG)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        def render(*_):
            self.clear(inner)
            q = search_var.get().strip().lower()
            if tab == "glyphs":
                items = sorted(GLYPHS.values(), key=lambda g: (g.rarity != "Rare", g.rarity != "Uncommon", g.category, g.name))
                for g in items:
                    hay = f"{g.name} {g.rarity} {g.category} {g.description}".lower()
                    if q and q not in hay: continue
                    card = tk.Frame(inner, bg=PANEL, padx=14, pady=10,
                                    highlightbackground=RARITY_COLOR[g.rarity], highlightthickness=1)
                    card.pack(fill="x", pady=4, padx=2)
                    line = tk.Frame(card, bg=PANEL); line.pack(fill="x")
                    tk.Label(line, text=g.name, bg=PANEL, fg=TEXT,
                             font=("Segoe UI", 10, "bold")).pack(side="left")
                    tk.Label(line, text=f"{g.category} • {g.rarity}", bg=PANEL,
                             fg=RARITY_COLOR[g.rarity], font=("Segoe UI", 8, "bold")).pack(side="right")
                    tk.Label(card, text=g.description, bg=PANEL, fg=MUTED, justify="left",
                             wraplength=900).pack(anchor="w", pady=(4,0))
            elif tab == "axioms":
                for a in sorted(AXIOMS.values(), key=lambda x: x.name):
                    hay=f"{a.name} {a.description}".lower()
                    if q and q not in hay: continue
                    card=tk.Frame(inner,bg=PANEL,padx=14,pady=10,highlightbackground="#6d5934",highlightthickness=1)
                    card.pack(fill="x",pady=4,padx=2)
                    tk.Label(card,text=a.name,bg=PANEL,fg=ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w")
                    tk.Label(card,text=a.description,bg=PANEL,fg=MUTED,justify="left",wraplength=900).pack(anchor="w",pady=(4,0))
            else:
                for b in sorted(BOSSES.values(), key=lambda x: x.name):
                    hay=f"{b.name} {b.description}".lower()
                    if q and q not in hay: continue
                    card=tk.Frame(inner,bg="#2a2022",padx=14,pady=10,highlightbackground="#704045",highlightthickness=1)
                    card.pack(fill="x",pady=4,padx=2)
                    tk.Label(card,text=b.name,bg="#2a2022",fg="#efc0c3",font=("Segoe UI",10,"bold")).pack(anchor="w")
                    tk.Label(card,text=b.description,bg="#2a2022",fg="#c9aaac",justify="left",wraplength=900).pack(anchor="w",pady=(4,0))
            canvas.yview_moveto(0)
        search_var.trace_add("write", render)
        render()
        entry.focus_set()

    def show_settings(self):
        self.screen = "settings"
        self.clear(self.main)
        self.clear(self.side)
        self._menu_chrome("Settings")
        outer = tk.Frame(self.main, bg=BG, padx=60, pady=36)
        outer.pack(fill="both", expand=True)
        top = tk.Frame(outer, bg=BG); top.pack(fill="x")
        tk.Label(top, text="SETTINGS", bg=BG, fg=TEXT,
                 font=("Georgia", 27, "bold")).pack(side="left")
        self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")
        panel = tk.Frame(outer, bg=PANEL, padx=24, pady=22,
                         highlightbackground="#3b3b42", highlightthickness=1)
        panel.pack(fill="x", pady=24)

        display_var = tk.StringVar(value=self.settings.get("display_mode", "fullscreen"))
        res_var = tk.StringVar(value=self.settings.get("resolution", "1280x800"))
        sound_var = tk.BooleanVar(value=bool(self.settings.get("sound_enabled", True)))
        motion_var = tk.BooleanVar(value=bool(self.settings.get("reduced_motion", False)))
        telemetry_var = tk.BooleanVar(value=bool(self.settings.get("telemetry_enabled", True)))
        updates_var = tk.BooleanVar(value=bool(self.settings.get("check_updates", True)))

        def label(text, row):
            tk.Label(panel,text=text,bg=PANEL,fg=TEXT,font=("Segoe UI",10,"bold")).grid(row=row,column=0,sticky="w",pady=10,padx=(0,30))
        label("Display mode",0)
        om=tk.OptionMenu(panel,display_var,"fullscreen","borderless","windowed")
        om.config(bg=PANEL2,fg=TEXT,activebackground=PANEL2,activeforeground=TEXT,relief="flat",width=18,highlightthickness=0)
        om["menu"].config(bg=PANEL2,fg=TEXT)
        om.grid(row=0,column=1,sticky="w")
        label("Window resolution",1)
        rm=tk.OptionMenu(panel,res_var,"1280x720","1280x800","1440x900","1600x900","1920x1080")
        rm.config(bg=PANEL2,fg=TEXT,activebackground=PANEL2,activeforeground=TEXT,relief="flat",width=18,highlightthickness=0)
        rm["menu"].config(bg=PANEL2,fg=TEXT)
        rm.grid(row=1,column=1,sticky="w")
        label("Sound effects",2)
        tk.Checkbutton(panel,text="Enabled",variable=sound_var,bg=PANEL,fg=MUTED,selectcolor=PANEL2,
                       activebackground=PANEL,activeforeground=TEXT).grid(row=2,column=1,sticky="w")
        label("Reduced motion",3)
        tk.Checkbutton(panel,text="Reduce shakes, pulses, and burst animations",variable=motion_var,bg=PANEL,fg=MUTED,selectcolor=PANEL2,
                       activebackground=PANEL,activeforeground=TEXT).grid(row=3,column=1,sticky="w")
        label("Local play telemetry",4)
        tk.Checkbutton(panel,text="Record anonymous run data on this computer",variable=telemetry_var,bg=PANEL,fg=MUTED,selectcolor=PANEL2,
                       activebackground=PANEL,activeforeground=TEXT).grid(row=4,column=1,sticky="w")
        tk.Label(panel,text="Telemetry stays on this computer unless you share it manually.",
                 bg=PANEL,fg="#77777e",font=("Segoe UI",8),wraplength=500,justify="left").grid(row=5,column=1,sticky="w",pady=(0,8))
        label("Update checks",6)
        tk.Checkbutton(panel,text="Check GitHub Releases on the main menu",variable=updates_var,bg=PANEL,fg=MUTED,selectcolor=PANEL2,
                       activebackground=PANEL,activeforeground=TEXT).grid(row=6,column=1,sticky="w")

        def apply():
            self.settings.update({
                "display_mode": display_var.get(), "resolution": res_var.get(),
                "sound_enabled": bool(sound_var.get()), "reduced_motion": bool(motion_var.get()),
                "telemetry_enabled": bool(telemetry_var.get()),
                "check_updates": bool(updates_var.get()),
            })
            self.storage.save_settings()
            self.sound.enabled = bool(sound_var.get())
            self.apply_display_settings()
            self.sound.play("select")
        setting_actions = tk.Frame(outer, bg=BG); setting_actions.pack(anchor="w")
        self._menu_button(setting_actions,"APPLY SETTINGS",apply,primary=True,width=20).pack(side="left")
        self._menu_button(setting_actions,"CHECK FOR UPDATES",self.check_updates_manual,width=20).pack(side="left",padx=8)
        tk.Label(outer,text=f"Player data folder: {self.storage.root}",bg=BG,fg="#6e6b66",font=("Segoe UI",8)).pack(anchor="w",pady=(12,0))

    def save_and_main_menu(self):
        if not self.game or not self.game.can_save():
            messagebox.showwarning("Cannot save", "Runs can only be saved while the timer is paused.")
            return
        try:
            payload = self.game.to_save_dict()
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        if not self.storage.save_run_payload(payload):
            messagebox.showerror("Save failed", "Could not write the run save file.")
            return
        self.sound.play("save")
        self.show_main_menu()

    def _safe_screen_button(self, parent):
        if self.game and self.game.can_save():
            self._menu_button(parent, "SAVE & EXIT", self.save_and_main_menu, width=18).pack(side="right", padx=5)

    def continue_saved_run(self):
        payload = self.storage.load_run_payload()
        if not payload:
            messagebox.showwarning("No saved run", "No valid saved run was found.")
            self.show_main_menu()
            return
        try:
            saved_bank_id = str(payload.get("attrs", {}).get("bank_id", "standard"))
            if saved_bank_id not in BANKS:
                saved_bank_id = "standard"
            self.selected_bank_id = saved_bank_id
            self.bank = WordBank(self.data_path, saved_bank_id)
            self.game = GameState.from_save_dict(
                self.bank, payload, data_dir=self.storage.root,
                telemetry_enabled=bool(self.settings.get("telemetry_enabled", True)),
            )
        except Exception as exc:
            messagebox.showerror("Could not load run", str(exc))
            return
        self.presentation_paused = self.game.status != "playing"
        self.boss_intro_seen.clear()
        self.danger_sound_round = None
        self.sound.play("select")
        self.continue_from_choice()

    def restart_run(self):
        if not self.game:
            return
        diff=self.game.difficulty
        bank_id=getattr(self.game,"bank_id",getattr(self.bank,"bank_id","standard"))
        if not messagebox.askyesno("Restart run",
            f"Restart this run?\n\nCurrent progress will be lost. A new {DIFFICULTIES[diff].name} run using {BANKS[bank_id].name} will begin with a new random seed."):
            return
        self.storage.finalize_run(self.game)
        self.storage.delete_run_save()
        self.selected_difficulty=diff; self.selected_bank_id=bank_id
        self.bank=WordBank(self.data_path,bank_id)
        self.game=GameState(self.bank,None,difficulty=diff,bank_id=bank_id,data_dir=self.storage.root,telemetry_enabled=bool(self.settings.get("telemetry_enabled",True)))
        self.storage.record_run_started(diff)
        self.presentation_paused=False; self.boss_intro_seen.clear(); self.danger_sound_round=None
        self.game.start_round(); self.sound.play("select"); self.continue_from_choice()

    def _show_update_button(self):
        if not hasattr(self,"update_button_holder") or not self.update_button_holder.winfo_exists() or not self.available_update:
            return
        self.clear(self.update_button_holder)
        self._menu_button(self.update_button_holder,f"UPDATE TO v{self.available_update.version}",self.confirm_update,primary=True,width=26).pack(pady=(10,4),anchor="w")

    def _check_updates_async(self, notify=False):
        if self.update_checking:
            return
        self.update_checking=True
        def worker():
            info=self.update_manager.check_latest()
            def done():
                self.update_checking=False; self.available_update=info
                if self.screen=="menu" and info: self._show_update_button()
                if notify:
                    if info: messagebox.showinfo("Update available",f"Dead Letter v{info.version} is available.")
                    else: messagebox.showinfo("Updates",f"Dead Letter v{GAME_VERSION} is up to date, or the release server could not be reached.")
            self.root.after(0,done)
        threading.Thread(target=worker,daemon=True).start()

    def check_updates_manual(self):
        self._check_updates_async(notify=True)

    def confirm_update(self):
        info=self.available_update
        if not info: return
        has_save=self.storage.has_run_save()
        warning="\n\nYour saved Continue Run will be deleted by this update." if has_save else ""
        if not messagebox.askyesno("Update Dead Letter",f"Install Dead Letter v{info.version}?{warning}\n\nPlayer stats, settings, and telemetry will be preserved."):
            return
        def worker():
            try:
                staged=self.update_manager.stage_update(info)
            except Exception as exc:
                self.root.after(0,lambda:messagebox.showerror("Update failed",str(exc)))
                return
            def install():
                try:
                    if has_save:
                        self.storage.delete_run_save()
                    self.update_manager.launch_installer(staged)
                except Exception as exc:
                    messagebox.showerror("Update failed",str(exc))
                    return
                self.root.destroy()
            self.root.after(0,install)
        threading.Thread(target=worker,daemon=True).start()

    def toggle_sound(self):
        enabled = self.sound.toggle()
        self.settings["sound_enabled"] = enabled
        self.storage.save_settings()
        self.sound_button.config(text="SOUND ON" if enabled else "SOUND OFF",
                                 fg=MUTED if enabled else BAD)
        if enabled:
            self.sound.play("select")

    def _chapter_label(self, g: GameState):
        if g.endless or g.chapter > 8:
            return f"Chapter {g.chapter} • ENDLESS"
        return f"Chapter {g.chapter}/8"

    def _boss_banner(self, parent, boss_id: str, mode="upcoming"):
        boss = BOSSES[boss_id]
        if mode == "active":
            bg, title_fg, desc_fg = "#3a2527", "#f2c9c9", "#e1b3b3"
            title = f"BOSS — {boss.name}"
        elif mode == "defeated":
            bg, title_fg, desc_fg = "#26382b", "#bfe2c8", "#a7cbb0"
            title = f"BOSS DEFEATED — {boss.name}"
        else:
            bg, title_fg, desc_fg = PANEL, ACCENT, MUTED
            title = f"UPCOMING BOSS — {boss.name}"
        banner = tk.Frame(parent, bg=bg, padx=12, pady=8)
        banner.pack(fill="x", pady=(0, 8))
        tk.Label(banner, text=title, bg=bg, fg=title_fg,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(banner, text=boss.description, bg=bg, fg=desc_fg,
                 justify="left", wraplength=760).pack(anchor="w", pady=(2, 0))
        return banner

    def _chapter_progress(self, parent, solved_current=False):
        """Persistent four-step tracker so the player always knows when the Boss is next."""
        if not self.game:
            return None
        g = self.game
        current = g.round_in_chapter
        boss = BOSSES[g.current_boss_id]
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", pady=(0, 9))

        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x", pady=(0, 5))
        chapter_text = f"CHAPTER {g.chapter}" + (" • ENDLESS" if g.endless or g.chapter > 8 else f" / {g.CHAPTERS}")
        tk.Label(top, text=chapter_text, bg=BG, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        if solved_current and current < 4:
            next_text = "BOSS NEXT" if current == 3 else f"NEXT: WORD {current + 1}"
        elif solved_current and current == 4:
            next_text = "CHAPTER COMPLETE"
        elif current == 4:
            next_text = "BOSS ROUND"
        else:
            next_text = f"WORD {current} OF 4"
        tk.Label(top, text=next_text, bg=BG,
                 fg=BAD if "BOSS" in next_text else MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="right")

        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x")
        for idx in range(1, 5):
            if idx < 4:
                label = f"WORD {idx}"
            else:
                label = f"BOSS\n{boss.name.upper()}"

            completed = idx < current or (solved_current and idx == current)
            active = idx == current and not solved_current
            next_stage = solved_current and idx == current + 1

            if completed:
                bg, fg, border = "#25372a", GOOD, "#3e7050"
                prefix = "✓  "
            elif active and idx == 4:
                bg, fg, border = "#412426", "#f1caca", BAD
                prefix = "▶  "
            elif active:
                bg, fg, border = "#393224", ACCENT, "#6d5934"
                prefix = "▶  "
            elif next_stage and idx == 4:
                bg, fg, border = "#352326", BAD, "#704045"
                prefix = "NEXT  "
            elif next_stage:
                bg, fg, border = PANEL2, ACCENT, "#5a513e"
                prefix = "NEXT  "
            else:
                bg, fg, border = PANEL, MUTED, "#34343a"
                prefix = ""

            cell = tk.Frame(row, bg=bg, padx=8, pady=6,
                            highlightbackground=border, highlightthickness=1)
            cell.pack(side="left", fill="x", expand=True, padx=(0 if idx == 1 else 3, 0))
            tk.Label(cell, text=prefix + label, bg=bg, fg=fg,
                     justify="center", font=("Segoe UI", 8, "bold")).pack(expand=True)
        return wrap

    def _boss_next_callout(self, parent):
        if not self.game or self.game.round_in_chapter != 3 or self.game.round.boss_id:
            return
        boss = BOSSES[self.game.current_boss_id]
        box = tk.Frame(parent, bg="#352326", padx=12, pady=8,
                       highlightbackground=BAD, highlightthickness=1)
        box.pack(fill="x", pady=(2, 9))
        tk.Label(box, text=f"⚠ NEXT ROUND: BOSS — {boss.name}", bg="#352326", fg="#f1caca",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(box, text=boss.description, bg="#352326", fg="#d8b1b3",
                 justify="left", wraplength=760).pack(anchor="w", pady=(2, 0))

    def show_boss_intro(self):
        """Hard stop before every Boss so the player cannot accidentally stumble into it."""
        if not self.game or self.game.status != "boss_ready" or not self.game.round or not self.game.round.boss_id:
            self.continue_from_choice()
            return
        self.screen = "boss_intro"
        self.presentation_paused = True
        self._run_chrome()
        g = self.game
        boss = BOSSES[g.round.boss_id]
        self.boss_intro_seen.add(g.round_index)
        self.clear(self.main)
        self.clear(self.side)
        self.header_info.config(text=f"{self._chapter_label(g)}  •  BOSS APPROACHING  •  {g.difficulty_def.name}  •  Seed {g.seed}")
        self._chapter_progress(self.main)

        outer = tk.Frame(self.main, bg="#25191b", padx=26, pady=24,
                         highlightbackground=BAD, highlightthickness=2)
        outer.pack(fill="both", expand=True, pady=(12, 18))
        warning_bar = tk.Canvas(outer, height=8, bg="#25191b", highlightthickness=0)
        warning_bar.pack(fill="x", pady=(0, 12))
        warning_bar.update_idletasks()
        ww = max(300, warning_bar.winfo_width())
        for x in range(-20, ww + 30, 42):
            warning_bar.create_polygon(x, 8, x + 18, 0, x + 31, 0, x + 13, 8, fill=BAD, outline="")
        tk.Label(outer, text="BOSS APPROACHING", bg="#25191b", fg=BAD,
                 font=("Segoe UI", 12, "bold")).pack(pady=(18, 6))
        boss_title = tk.Label(outer, text=boss.name.upper(), bg="#25191b", fg=TEXT,
                              font=("Georgia", 30, "bold"))
        boss_title.pack(pady=3)
        tk.Label(outer, text=boss.description, bg="#25191b", fg="#e2c4c5",
                 justify="center", wraplength=680, font=("Segoe UI", 12)).pack(pady=(8, 18))
        if boss.id == "forbidden" and g.round.forbidden_letter:
            tk.Label(outer, text=f"FORBIDDEN LETTER: {g.round.forbidden_letter.upper()}", bg="#25191b", fg=ACCENT,
                     font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))

        info = tk.Frame(outer, bg="#312124", padx=14, pady=10)
        info.pack(pady=7)
        tk.Label(info, text=self.game.complexity_display(), bg="#312124", fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack()
        tk.Label(info, text=f"{g.round.max_mistakes} mistake capacity  •  {g.round.initial_time:.0f}s starting time",
                 bg="#312124", fg=MUTED).pack(pady=(3, 0))

        actions = tk.Frame(outer, bg="#25191b")
        actions.pack(pady=(20, 12))
        tk.Button(actions, text="ENTER BOSS", command=self.enter_boss,
                  bg=BAD, fg="#1a1213", activebackground="#e07b7b", relief="flat",
                  padx=34, pady=11, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        self._safe_screen_button(actions)
        tk.Label(outer, text="The timer is paused until you enter. This screen can be safely saved.", bg="#25191b", fg="#8f7779",
                 font=("Segoe UI", 8)).pack()
        self._build_side_panel()
        self.sound.play("boss")

        if not self.settings.get("reduced_motion", False):
            def pulse(on=True):
                if self.screen != "boss_intro" or not boss_title.winfo_exists():
                    return
                boss_title.config(fg="#fff0f0" if on else "#d9b9bb")
                self.root.after(520, lambda: pulse(not on))
            pulse()

    def enter_boss(self):
        if not self.game or not self.game.enter_boss():
            return
        self.storage.delete_run_save()
        self.presentation_paused = False
        self.sound.play("select")
        self.show_play()

    def show_start(self):
        """New-run setup: difficulty, word bank, and optional seed."""
        self.screen = "new_run"
        self.presentation_paused = True
        self.clear(self.main); self.clear(self.side)
        self._menu_chrome("New Run")
        outer = tk.Frame(self.main, bg=BG, padx=48, pady=24); outer.pack(fill="both", expand=True)
        top = tk.Frame(outer, bg=BG); top.pack(fill="x")
        tk.Label(top, text="NEW RUN", bg=BG, fg=TEXT, font=("Georgia", 28, "bold")).pack(side="left")
        self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")

        tk.Label(outer, text="DIFFICULTY", bg=BG, fg=ACCENT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(16,6))
        cards = tk.Frame(outer, bg=BG); cards.pack(fill="x")
        colors = {"easy": GOOD, "medium": ACCENT, "hard": BAD}
        for did in ("easy", "medium", "hard"):
            d=DIFFICULTIES[did]; chosen=did==self.selected_difficulty
            f=tk.Frame(cards,bg=PANEL,padx=12,pady=10,highlightbackground=colors[did] if chosen else "#3b3b42",highlightthickness=2 if chosen else 1)
            f.pack(side="left",fill="x",expand=True,padx=4)
            tk.Label(f,text=d.name.upper(),bg=PANEL,fg=colors[did],font=("Georgia",14,"bold")).pack(anchor="w")
            t="Standard time" if d.time_delta==0 else f"{d.time_delta:+.0f}s per word"
            tk.Label(f,text=f"{t}  •  {d.glyph_choices} Glyph / {d.axiom_choices} Axiom option{'s' if d.glyph_choices!=1 else ''}",bg=PANEL,fg=MUTED,font=("Segoe UI",8)).pack(anchor="w",pady=(3,6))
            tk.Button(f,text="SELECTED" if chosen else "SELECT",command=lambda x=did:self.select_difficulty(x),bg=colors[did] if chosen else PANEL2,fg=BG if chosen else TEXT,relief="flat",pady=4).pack(fill="x")

        tk.Label(outer, text="WORD BANK", bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(20, 7))
        bank_area = tk.Frame(outer, bg=BG)
        bank_area.pack(fill="x")
        bank_items = list(BANKS.items())
        bank_rows = (bank_items[:3], bank_items[3:])
        for row_index, row_items in enumerate(bank_rows):
            row = tk.Frame(bank_area, bg=BG)
            row.pack(fill="x", pady=(0, 8 if row_index == 0 else 0))
            for bid, bdef in row_items:
                chosen = bid == self.selected_bank_id
                f = tk.Frame(
                    row,
                    bg=PANEL,
                    padx=16,
                    pady=13,
                    highlightbackground=ACCENT if chosen else "#3b3b42",
                    highlightthickness=2 if chosen else 1,
                )
                f.pack(side="left", fill="both", expand=True, padx=4)
                tk.Label(
                    f,
                    text=bdef.name.upper(),
                    bg=PANEL,
                    fg=ACCENT if chosen else TEXT,
                    font=("Segoe UI", 11, "bold"),
                ).pack(anchor="w")
                tk.Label(
                    f,
                    text=bdef.description,
                    bg=PANEL,
                    fg="#c7c7cd",
                    wraplength=520,
                    justify="left",
                    anchor="nw",
                    font=("Segoe UI", 10),
                ).pack(anchor="w", fill="x", expand=True, pady=(6, 12))
                tk.Button(
                    f,
                    text="SELECTED" if chosen else "SELECT",
                    command=lambda x=bid: self.select_word_bank(x),
                    bg=ACCENT if chosen else PANEL2,
                    fg=BG if chosen else TEXT,
                    relief="flat",
                    pady=5,
                    font=("Segoe UI", 9, "bold"),
                ).pack(fill="x")

        setup=tk.Frame(outer,bg=PANEL,padx=14,pady=12,highlightbackground="#3b3b42",highlightthickness=1); setup.pack(fill="x",pady=16)
        tk.Label(setup,text="Seed (optional)",bg=PANEL,fg=TEXT,font=("Segoe UI",9,"bold")).pack(side="left")
        self.seed_entry=tk.Entry(setup,bg=PANEL2,fg=TEXT,insertbackground=TEXT,relief="flat",width=18); self.seed_entry.pack(side="left",padx=10,ipady=4)
        tk.Label(setup,text="Same seed + difficulty + word bank reproduces the same rolls.",bg=PANEL,fg=MUTED,font=("Segoe UI",8)).pack(side="left")

        actions=tk.Frame(outer,bg=BG); actions.pack(fill="x")
        self._menu_button(actions,"START RUN",self.new_run,primary=True,width=18).pack(side="left")
        self._menu_button(actions,"TUTORIAL",lambda:self.show_tutorial(0),width=14).pack(side="left",padx=8)
        tk.Label(outer,text=f"8 Chapters • 16 unique Bosses before repeats • {len(GLYPHS)} Glyphs • {len(AXIOMS)} Axioms",bg=BG,fg="#77777e",font=("Segoe UI",8)).pack(anchor="w",pady=(10,0))

    def select_word_bank(self, bid):
        if bid in BANKS:
            self.selected_bank_id=bid
            self.sound.play("select")
            self.show_start()

    def select_difficulty(self, did):
        if did in DIFFICULTIES:
            self.selected_difficulty = did
            self.sound.play("select")
            self.show_start()

    def new_run(self):
        text = self.seed_entry.get().strip() if hasattr(self, "seed_entry") else ""
        try:
            seed = int(text) if text else None
        except ValueError:
            messagebox.showwarning("Invalid seed", "Seed must be an integer.")
            return
        if self.storage.has_run_save():
            if not messagebox.askyesno("Overwrite saved run", "Starting a new run will delete the saved Continue Run. Start anyway?"):
                return
            self.storage.delete_run_save()
        self.sound.play("select")
        self.presentation_paused = False
        self.boss_intro_seen.clear()
        self.danger_sound_round = None
        try:
            self.bank = WordBank(self.data_path, self.selected_bank_id)
        except Exception as exc:
            messagebox.showerror("Word bank error", str(exc))
            return
        self.game = GameState(
            self.bank, seed, difficulty=self.selected_difficulty, bank_id=self.selected_bank_id,
            data_dir=self.storage.root,
            telemetry_enabled=bool(self.settings.get("telemetry_enabled", True)),
        )
        self.storage.record_run_started(self.selected_difficulty)
        self.game.start_round()
        self.continue_from_choice()

    def show_play(self):
        if not self.game or self.game.status != "playing":
            return
        self.screen = "play"
        self.presentation_paused = False
        self._run_chrome()
        # A timed word is intentionally never a resume point. Once play begins,
        # any previous safe-screen save is consumed.
        self.storage.delete_run_save()
        self.clear(self.main)
        self.clear(self.side)
        g, r = self.game, self.game.round
        boss = BOSSES[r.boss_id] if r.boss_id else None
        self.header_info.config(
            text=f"{self._chapter_label(g)}  •  {'BOSS' if boss else 'Word'} {g.round_in_chapter}/4  •  {g.difficulty_def.name}  •  {BANKS.get(g.bank_id, BANKS['standard']).name}  •  Seed {g.seed}"
        )

        self._chapter_progress(self.main)
        if boss:
            self._boss_banner(self.main, r.boss_id, "active")
        else:
            self._boss_banner(self.main, g.current_boss_id, "upcoming")

        stats = tk.Frame(self.main, bg=BG)
        stats.pack(fill="x", pady=4)
        self.complexity_label = tk.Label(stats, text=g.complexity_display(), bg=BG, fg=MUTED,
                                         font=("Segoe UI", 10, "bold"))
        self.complexity_label.pack(side="left")
        self.mistake_label = tk.Label(stats, text="", bg=BG, fg=TEXT,
                                      font=("Segoe UI", 11, "bold"))
        self.mistake_label.pack(side="right")

        self.danger_frame = tk.Frame(self.main, bg=BG, height=38,
                                     highlightthickness=1, highlightbackground=BG)
        self.danger_frame.pack(fill="x", pady=(2, 6))
        self.danger_frame.pack_propagate(False)
        self.danger_label = tk.Label(self.danger_frame, text="", bg=BG, fg=BG,
                                     font=("Segoe UI", 11, "bold"))
        self.danger_label.pack(expand=True)

        self.timer_canvas = tk.Canvas(self.main, height=20, bg=PANEL2, highlightthickness=1, highlightbackground="#3a3a40")
        self.timer_canvas.pack(fill="x", pady=(5, 12))

        self.word_panel = tk.Frame(self.main, bg=BG, padx=12, pady=7,
                                   highlightbackground=BG, highlightthickness=2)
        self.word_panel.pack(pady=(10, 3))
        self.word_label = tk.Label(self.word_panel, text=g.visible_word(), bg=BG, fg=TEXT,
                                   font=("Consolas", 31, "bold"))
        self.word_label.pack()
        self.pos_label = tk.Label(self.main, text="", bg=BG, fg=BLUE, font=("Segoe UI", 10))
        self.pos_label.pack()
        self.feedback = tk.Label(self.main, text="Choose a letter.", bg=BG, fg=MUTED,
                                 font=("Segoe UI", 10))
        self.feedback.pack(pady=(6, 2))
        self.effect_label = tk.Label(self.main, text="", bg=BG, fg=ACCENT,
                                     font=("Segoe UI", 9, "bold"))
        self.effect_label.pack(pady=(0, 2))
        self.fx_canvas = tk.Canvas(self.main, height=28, bg=BG, highlightthickness=0)
        self.fx_canvas.pack(fill="x", pady=(0, 4))

        alpha = tk.Frame(self.main, bg=BG)
        alpha.pack(pady=4)
        self.letter_buttons = {}
        for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            b = tk.Button(alpha, text=ch, width=3, height=1,
                          command=lambda c=ch.lower(): self.guess_letter(c),
                          bg=PANEL2, fg=TEXT, activebackground=ACCENT, relief="flat",
                          font=("Consolas", 11, "bold"))
            b.grid(row=i // 13, column=i % 13, padx=3, pady=3)
            self.letter_buttons[ch.lower()] = b

        entryrow = tk.Frame(self.main, bg=BG)
        entryrow.pack(pady=(13, 3))
        examiner = bool(r.boss_id == "examiner")
        tk.Label(entryrow, text="Full word:", bg=BG, fg=MUTED).pack(side="left", padx=5)
        self.word_entry = tk.Entry(entryrow, width=24, bg=PANEL2, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", font=("Consolas", 12),
                                   state="disabled" if examiner else "normal")
        self.word_entry.pack(side="left", ipady=6, padx=5)
        self.word_entry.bind("<Return>", self._entry_submit)
        self.word_entry.bind("<Escape>", self._entry_escape)
        tk.Button(entryrow, text="DISABLED BY BOSS" if examiner else "GUESS WORD",
                  command=self.guess_word, bg=PANEL2 if examiner else ACCENT,
                  fg=MUTED if examiner else BG, state="disabled" if examiner else "normal",
                  relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        helper = "The Examiner forbids full-word guesses." if examiner else "/ = full-word mode   •   Esc = return to letter keys"
        tk.Label(self.main, text=helper, bg=BG, fg=BAD if examiner else "#77777e",
                 font=("Segoe UI", 8, "bold" if examiner else "normal")).pack()

        self._build_side_panel()
        self.refresh_play()
        self.root.focus_set()

    def _entry_submit(self, _event=None):
        self.guess_word()
        return "break"

    def _entry_escape(self, _event=None):
        self.leave_full_word_mode()
        return "break"

    def leave_full_word_mode(self):
        if hasattr(self, "word_entry"):
            self.root.focus_set()
        if hasattr(self, "feedback"):
            self.feedback.config(text="Letter-guess mode.", fg=MUTED)

    def _build_side_panel(self):
        self.points_label = tk.Label(self.side, text="", bg=PANEL, fg=ACCENT,
                                     font=("Georgia", 19, "bold"))
        self.points_label.pack(anchor="w")
        self.total_label = tk.Label(self.side, text="", bg=PANEL, fg=MUTED)
        self.total_label.pack(anchor="w", pady=(0, 8))
        self.hangman = tk.Canvas(self.side, height=220, bg=PANEL, highlightthickness=2, highlightbackground="#34343a")
        self.hangman.pack(fill="x", pady=(3, 6))

        inventory_wrap = tk.Frame(self.side, bg=PANEL)
        inventory_wrap.pack(fill="both", expand=True, pady=(2, 0))
        self.inventory_canvas = tk.Canvas(inventory_wrap, bg=PANEL, highlightthickness=0, bd=0)
        self.inventory_scroll = tk.Scrollbar(inventory_wrap, orient="vertical",
                                             command=self.inventory_canvas.yview)
        self.inventory_canvas.configure(yscrollcommand=self.inventory_scroll.set)
        self.inventory_scroll.pack(side="right", fill="y")
        self.inventory_canvas.pack(side="left", fill="both", expand=True)

        self.inventory_inner = tk.Frame(self.inventory_canvas, bg=PANEL)
        self.inventory_window = self.inventory_canvas.create_window((0, 0), window=self.inventory_inner,
                                                                     anchor="nw")
        self.inventory_inner.bind("<Configure>", self._sync_inventory_scrollregion)
        self.inventory_canvas.bind("<Configure>", self._sync_inventory_width)
        self.inventory_canvas.bind("<Enter>", self._bind_inventory_wheel)
        self.inventory_canvas.bind("<Leave>", self._unbind_inventory_wheel)

        tk.Label(self.inventory_inner, text="GLYPHS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(3, 5))
        self.glyph_frame = tk.Frame(self.inventory_inner, bg=PANEL)
        self.glyph_frame.pack(fill="x")
        tk.Label(self.inventory_inner, text="AXIOMS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(13, 5))
        self.axiom_frame = tk.Frame(self.inventory_inner, bg=PANEL)
        self.axiom_frame.pack(fill="x")

        self._side_inventory_signature = None
        self._refresh_side()

    def _sync_inventory_scrollregion(self, _event=None):
        if hasattr(self, "inventory_canvas"):
            self.inventory_canvas.configure(scrollregion=self.inventory_canvas.bbox("all"))

    def _sync_inventory_width(self, event):
        if hasattr(self, "inventory_window"):
            self.inventory_canvas.itemconfigure(self.inventory_window, width=max(1, event.width))

    def _bind_inventory_wheel(self, _event=None):
        self.root.bind_all("<MouseWheel>", self._inventory_mousewheel)
        self.root.bind_all("<Button-4>", self._inventory_mousewheel)
        self.root.bind_all("<Button-5>", self._inventory_mousewheel)

    def _unbind_inventory_wheel(self, _event=None):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def _inventory_mousewheel(self, event):
        if not hasattr(self, "inventory_canvas"):
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.inventory_canvas.yview_scroll(delta * 3, "units")

    def _refresh_side(self):
        if not self.game:
            return
        g = self.game
        if hasattr(self, "points_label"):
            self.points_label.config(text=f"{g.points:,} Points")
            mode = " • Endless" if g.endless else ""
            self.total_label.config(text=f"{g.total_earned:,} total earned{mode}")
        if not hasattr(self, "glyph_frame") or not hasattr(self, "axiom_frame"):
            return

        state_sig = tuple(sorted((k, str(v)) for k, v in g.glyph_state.items()))
        signature = (tuple(g.glyphs), tuple(g.axioms), g.glyph_slots(), state_sig)
        if signature == self._side_inventory_signature:
            return
        self._side_inventory_signature = signature
        old_y = self.inventory_canvas.yview()[0] if hasattr(self, "inventory_canvas") else 0.0

        self.clear(self.glyph_frame)
        for i in range(g.glyph_slots()):
            occupied = i < len(g.glyphs)
            card_bg = PANEL2 if occupied else PANEL
            border = "#44444b" if occupied else "#303035"
            row = tk.Frame(self.glyph_frame, bg=card_bg, padx=8, pady=7,
                           highlightbackground=border, highlightthickness=1)
            row.pack(fill="x", pady=3)
            if occupied:
                gid = g.glyphs[i]
                gd = GLYPHS[gid]
                top = tk.Frame(row, bg=card_bg)
                top.pack(fill="x")
                tk.Label(top, text=f"{i+1}. {gd.name}", bg=card_bg, fg=TEXT,
                         font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
                tk.Label(top, text=f"{gd.category.upper()} • {gd.rarity.upper()}", bg=card_bg,
                         fg=ACCENT if gd.rarity != "Common" else MUTED,
                         font=("Segoe UI", 7, "bold")).pack(side="left", padx=(4, 3))
                tk.Button(top, text="×", command=lambda idx=i: self.trash_glyph(idx),
                          bg=card_bg, fg=BAD, activebackground=card_bg,
                          activeforeground=BAD, relief="flat", width=2).pack(side="right")
                tk.Label(row, text=g.glyph_description(gid), bg=card_bg, fg=MUTED,
                         justify="left", anchor="w", wraplength=298,
                         font=("Segoe UI", 8)).pack(fill="x", pady=(3, 0))
            else:
                tk.Label(row, text=f"{i+1}. — empty —", bg=card_bg, fg="#6f6f76",
                         anchor="w", font=("Segoe UI", 9)).pack(fill="x")

        self.clear(self.axiom_frame)
        if g.axioms:
            for aid in g.axioms:
                a = AXIOMS[aid]
                card = tk.Frame(self.axiom_frame, bg="#27272c", padx=8, pady=7,
                                highlightbackground="#4c463a", highlightthickness=1)
                card.pack(fill="x", pady=3)
                tk.Label(card, text=a.name, bg="#27272c", fg=ACCENT,
                         font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
                tk.Label(card, text=a.description, bg="#27272c", fg=MUTED,
                         justify="left", anchor="w", wraplength=298,
                         font=("Segoe UI", 8)).pack(fill="x", pady=(3, 0))
        else:
            tk.Label(self.axiom_frame, text="None yet", bg=PANEL, fg=MUTED,
                     anchor="w").pack(fill="x", pady=(0, 4))

        self.inventory_inner.update_idletasks()
        self._sync_inventory_scrollregion()
        self.inventory_canvas.yview_moveto(old_y)

    def refresh_play(self):
        if not self.game or self.game.status != "playing":
            return
        g, r = self.game, self.game.round
        self.word_label.config(text=g.visible_word())
        msg = r.last_message or "Choose a letter."
        self.feedback.config(text=msg, fg=GOOD if "appears" in msg else MUTED)
        remaining = max(0, r.max_mistakes - r.mistakes)
        if remaining == 1:
            self.mistake_label.config(text=f"⚠  {r.mistakes}/{r.max_mistakes} MISTAKES  •  1 LEFT", fg=BAD)
        else:
            self.mistake_label.config(text=f"Mistakes {r.mistakes}/{r.max_mistakes}  •  {remaining} left", fg=TEXT)
        self._refresh_danger_state()
        self.pos_label.config(text=g.round_info_text())

        for ch, button in self.letter_buttons.items():
            if ch in r.guessed_letters:
                if ch in r.word.word:
                    button.config(state="disabled", bg="#294536", disabledforeground="#8dc89c", text=ch.upper())
                else:
                    button.config(state="disabled", bg="#492b2d", disabledforeground="#d48e8e", text=ch.upper())
            elif ch in r.eliminated_letters:
                button.config(state="disabled", bg="#303035", disabledforeground="#77777e", text="·")
            elif ch in r.highlight_letters:
                button.config(state="normal", bg="#4a412c", fg="#f1cf83", text=ch.upper())
            else:
                button.config(state="normal", bg=PANEL2, fg=TEXT, text=ch.upper())
        self._draw_timer()
        self._draw_hangman()
        self._refresh_side()

    def _refresh_danger_state(self):
        """Make the one-mistake-left state impossible to overlook."""
        if not self.game or self.game.status != "playing" or not hasattr(self, "danger_frame"):
            return
        r = self.game.round
        remaining = max(0, r.max_mistakes - r.mistakes)
        danger = remaining == 1
        pulse = True if self.settings.get("reduced_motion", False) else int(time.perf_counter() * 4) % 2 == 0
        if danger:
            bg = "#54292e" if pulse else "#392326"
            fg = "#fff0f0" if pulse else "#f1b7ba"
            self.danger_frame.config(bg=bg, highlightbackground=BAD)
            self.danger_label.config(
                text="⚠  LAST CHANCE — ONE MORE MISTAKE ENDS THE RUN  ⚠",
                bg=bg, fg=fg, font=("Segoe UI", 11 if pulse else 10, "bold")
            )
            self.word_panel.config(highlightbackground=BAD if pulse else "#6b363a")
            # Play once on entry, not every 50 ms while the state persists.
            key = self.game.round_index
            if self.danger_sound_round != key:
                self.danger_sound_round = key
                self.sound.play("danger")
        else:
            self.danger_frame.config(bg=BG, highlightbackground=BG)
            self.danger_label.config(text="", bg=BG, fg=BG, font=("Segoe UI", 10, "bold"))
            # Preserve short guess-impact flashes, but otherwise return the panel border.
            self.word_panel.config(highlightbackground=BG)

    def _pop_word(self, color=GOOD):
        """Brief typographic punch on a successful reveal."""
        if self.settings.get("reduced_motion", False):
            if hasattr(self, "word_label") and self.word_label.winfo_exists(): self.word_label.config(fg=color)
            return
        if not hasattr(self, "word_label") or not self.word_label.winfo_exists():
            return
        frames = [(34, color), (33, color), (31, TEXT)]
        def frame(i=0):
            if not hasattr(self, "word_label") or not self.word_label.winfo_exists():
                return
            size, fg = frames[i]
            self.word_label.config(font=("Consolas", size, "bold"), fg=fg)
            if i + 1 < len(frames):
                self.root.after(55, lambda: frame(i + 1))
        frame()

    def _shake_word(self):
        """Small horizontal shake on a wrong guess; no sprite system required."""
        if self.settings.get("reduced_motion", False):
            return
        if not hasattr(self, "word_panel") or not self.word_panel.winfo_exists():
            return
        offsets = [10, -8, 6, -4, 2, 0]
        def frame(i=0):
            if not hasattr(self, "word_panel") or not self.word_panel.winfo_exists():
                return
            off = offsets[i]
            self.word_panel.pack_configure(padx=(max(0, off), max(0, -off)))
            if i + 1 < len(offsets):
                self.root.after(35, lambda: frame(i + 1))
            else:
                self.word_panel.pack_configure(padx=0)
        frame()

    def _draw_timer(self):
        r = self.game.round
        c = self.timer_canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        ratio = max(0, min(1, r.remaining_time / r.initial_time))
        danger = (r.max_mistakes - r.mistakes) == 1
        pulse = True if self.settings.get("reduced_motion", False) else int(time.perf_counter() * 4) % 2 == 0
        if r.remaining_time <= 5.0 and pulse:
            c.configure(bg="#3a2023", highlightbackground=BAD)
        elif danger and pulse:
            c.configure(bg="#2f2224", highlightbackground=BAD)
        else:
            c.configure(bg=PANEL2, highlightbackground="#3a3a40")
        color = GOOD if ratio > .45 else ACCENT if ratio > .2 else BAD
        c.create_rectangle(0, 0, w * ratio, 20, fill=color, outline="")
        if danger:
            # A thin red underlay remains visible even when plenty of time is left.
            c.create_line(0, 19, w, 19, fill=BAD, width=2)
        c.create_text(w / 2, 10, text=f"{r.remaining_time:0.1f}s", fill=TEXT,
                      font=("Segoe UI", 8, "bold"))

    def _draw_hangman(self):
        if not hasattr(self, "hangman") or not self.game or not self.game.round:
            return
        c = self.hangman
        c.delete("all")
        r = self.game.round
        remaining = max(0, r.max_mistakes - r.mistakes)
        danger = remaining == 1
        pulse = True if self.settings.get("reduced_motion", False) else int(time.perf_counter() * 4) % 2 == 0
        fg = BAD if danger and pulse else "#9b978d"
        c.configure(highlightbackground=BAD if danger and pulse else "#34343a",
                    bg="#2d2022" if danger and pulse else PANEL)
        # Traditional six-part Hangman figure. Extra capacity is represented
        # separately below so the base game still reads as six-mistake Hangman.
        c.create_line(40, 155, 190, 155, fill=fg, width=3)
        c.create_line(68, 155, 68, 20, fill=fg, width=3)
        c.create_line(66, 20, 148, 20, fill=fg, width=3)
        c.create_line(148, 20, 148, 38, fill=fg, width=2)
        m = r.mistakes
        if m >= 1: c.create_oval(133, 38, 163, 68, outline=TEXT, width=2)
        if m >= 2: c.create_line(148, 68, 148, 112, fill=TEXT, width=2)
        if m >= 3: c.create_line(148, 78, 128, 96, fill=TEXT, width=2)
        if m >= 4: c.create_line(148, 78, 168, 96, fill=TEXT, width=2)
        if m >= 5: c.create_line(148, 112, 131, 138, fill=TEXT, width=2)
        if m >= 6: c.create_line(148, 112, 165, 138, fill=TEXT, width=2)

        # Death eyes appear only when the *actual* current capacity is exhausted.
        # This prevents a +mistake build from visually looking dead at six.
        if m >= r.max_mistakes:
            c.create_line(140, 49, 145, 54, fill=BAD, width=2)
            c.create_line(145, 49, 140, 54, fill=BAD, width=2)
            c.create_line(151, 49, 156, 54, fill=BAD, width=2)
            c.create_line(156, 49, 151, 54, fill=BAD, width=2)

        # Capacity pips make buffs/debuffs immediately visible. The first six are
        # canonical Hangman capacity; bonus pips are gold and sit beyond them.
        c.create_text(12, 174, text="CAPACITY", fill=MUTED, anchor="w",
                      font=("Segoe UI", 7, "bold"))
        count = max(1, r.max_mistakes)
        x0 = 78
        gap = min(23, max(15, int(185 / max(1, count))))
        for i in range(count):
            x = x0 + i * gap
            bonus = i >= 6
            used = i < m
            is_final_live = danger and i == m
            outline = (BAD if is_final_live and pulse else ACCENT) if bonus else (BAD if is_final_live and pulse else "#77746d")
            fill = BAD if used else ("#5a2529" if is_final_live and pulse else ("#4a3d24" if bonus else PANEL2))
            width = 3 if is_final_live else (2 if bonus else 1)
            c.create_oval(x, 166, x + 13, 179, outline=outline, fill=fill, width=width)
            if is_final_live:
                c.create_text(x + 6.5, 172.5, text="!", fill=TEXT if pulse else BAD,
                              font=("Segoe UI", 7, "bold"))
            elif bonus and not used:
                c.create_text(x + 6.5, 172.5, text="+", fill=ACCENT,
                              font=("Segoe UI", 7, "bold"))
        if danger:
            c.create_text(12, 196, text="⚠ ONE MISTAKE LEFT — NEXT ONE ENDS THE RUN",
                          fill=BAD if pulse else "#e6b3b3", anchor="w",
                          font=("Segoe UI", 8, "bold"))
        elif r.max_mistakes > 6:
            c.create_text(12, 196, text=f"+{r.max_mistakes - 6} bonus mistake capacity",
                          fill=ACCENT, anchor="w", font=("Segoe UI", 7, "bold"))
        elif r.max_mistakes < 6:
            c.create_text(12, 196, text=f"Reduced to {r.max_mistakes} mistakes this word",
                          fill=BAD, anchor="w", font=("Segoe UI", 7, "bold"))
        else:
            c.create_text(12, 196, text="Standard six-mistake Hangman",
                          fill="#77777e", anchor="w", font=("Segoe UI", 7))

    def _fx_burst(self, color, text="", strong=False):
        if self.settings.get("reduced_motion", False):
            if hasattr(self, "effect_label") and self.effect_label.winfo_exists(): self.effect_label.config(text=text, fg=color)
            return
        if not hasattr(self, "fx_canvas") or not self.fx_canvas.winfo_exists():
            return
        c = self.fx_canvas
        c.delete("all")
        w = max(300, c.winfo_width())
        cx = w / 2
        cy = 14
        rays = 14 if strong else 8
        items = []
        for i in range(rays):
            spread = (i - (rays - 1) / 2) * (18 if strong else 22)
            x1 = cx + spread * 0.22
            x2 = cx + spread
            item = c.create_line(x1, cy, x2, cy + (4 if i % 2 else -4), fill=color,
                                 width=2 if strong else 1)
            items.append(item)
        text_item = None
        if text:
            text_item = c.create_text(cx, cy, text=text, fill=color,
                                      font=("Segoe UI", 9, "bold"))
            items.append(text_item)
        ring = c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline=color, width=2)
        items.append(ring)

        def fade(step=0):
            if not hasattr(self, "fx_canvas") or not self.fx_canvas.winfo_exists():
                return
            if step >= 4:
                c.delete("all")
                return
            # Tkinter has no alpha channel; shrinking line width gives a simple
            # impact/fade animation without external graphics libraries.
            for item in items:
                try:
                    typ = c.type(item)
                    if typ == "line":
                        c.itemconfigure(item, width=max(1, 2 - step // 2))
                    elif typ == "oval":
                        grow = 5 + step * 5
                        c.coords(item, cx - grow, cy - grow, cx + grow, cy + grow)
                    elif typ == "text":
                        c.move(item, 0, -2)
                except tk.TclError:
                    return
            self.root.after(55, lambda: fade(step + 1))
        self.root.after(55, fade)

    def _flash_hangman(self, color, duration=170):
        if not hasattr(self, "hangman") or not self.hangman.winfo_exists():
            return
        old = PANEL
        self.hangman.configure(bg=color)
        self.root.after(duration, lambda: self.hangman.winfo_exists() and self.hangman.configure(bg=old))

    def _flash_word(self, color, duration=180):
        if not hasattr(self, "word_panel"):
            return
        self.word_panel.config(highlightbackground=color)
        self.word_label.config(fg=color)
        def reset():
            if hasattr(self, "word_panel") and self.word_panel.winfo_exists():
                self.word_panel.config(highlightbackground=BG)
                self.word_label.config(fg=TEXT)
        self.root.after(duration, reset)

    def _animate_play_action(self, result, before_time, before_mistakes):
        if not self.game or self.game.status != "playing" or not result:
            return
        if not result.get("ok"):
            if hasattr(self, "effect_label"):
                self.effect_label.config(text=result.get("message", ""), fg=MUTED)
            return
        r = self.game.round
        if result.get("correct"):
            self.sound.play("correct")
            self._flash_word(GOOD)
            self._pop_word(GOOD)
            gained = r.remaining_time - before_time
            extra = f"  •  +{gained:.1f}s" if gained > 0.35 else ""
            self.effect_label.config(text=f"CORRECT{extra}", fg=GOOD)
            self._fx_burst(GOOD, "+ LETTER", strong=result.get("count", 1) > 1)
        else:
            self.sound.play("wrong")
            self._flash_word(BAD, 240)
            self._shake_word()
            self._flash_hangman("#3b2426", 190)
            delta = r.mistakes - before_mistakes
            text = f"WRONG  •  +{delta} mistake{'s' if delta != 1 else ''}" if delta else "WRONG  •  mistake absorbed"
            self.effect_label.config(text=text, fg=BAD)
            self._fx_burst(BAD, "MISTAKE" if delta else "ABSORBED", strong=delta > 0)

    def guess_letter(self, ch):
        if not self.game or self.game.status != "playing":
            return
        self.root.focus_set()
        r = self.game.round
        before_time, before_mistakes = r.remaining_time, r.mistakes
        result = self.game.guess_letter(ch)
        status = self.game.status
        self.after_action()
        if status == "playing":
            self._animate_play_action(result, before_time, before_mistakes)
        elif status == "glyph_choice":
            self.sound.play("solve")
        elif status == "lost":
            pass

    def guess_word(self):
        if not self.game or self.game.status != "playing":
            return
        text = self.word_entry.get()
        self.word_entry.delete(0, "end")
        r = self.game.round
        before_time, before_mistakes = r.remaining_time, r.mistakes
        result = self.game.guess_word(text)
        status = self.game.status
        self.after_action()
        if status == "playing":
            self._animate_play_action(result, before_time, before_mistakes)
            self.root.focus_set()
        elif status == "glyph_choice":
            self.sound.play("solve")
        elif status == "lost":
            pass

    def after_action(self):
        if self.game.status == "playing":
            self.refresh_play()
        elif self.game.status == "glyph_choice":
            self.show_glyph_choice()
        elif self.game.status == "lost":
            self.show_end(False)

    def show_glyph_choice(self):
        self.screen = "glyph_choice"
        self.presentation_paused = True
        self._run_chrome()
        self.clear(self.main)
        self.clear(self.side)
        g, r, res = self.game, self.game.round, self.game.last_result
        self.header_info.config(text=f"{self._chapter_label(g)}  •  Word cleared  •  {g.difficulty_def.name}")

        self._chapter_progress(self.main, solved_current=True)
        if r.boss_id:
            self._boss_banner(self.main, r.boss_id, "defeated")
        else:
            self._boss_banner(self.main, g.current_boss_id, "upcoming")
            self._boss_next_callout(self.main)

        cleared = tk.Frame(self.main, bg="#243328", padx=10, pady=6,
                           highlightbackground="#42634c", highlightthickness=1)
        cleared.pack(fill="x", pady=(1, 7))
        tk.Label(cleared, text="WORD CLEARED", bg="#243328", fg=GOOD,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        if not r.boss_id and g.round_in_chapter == 3:
            tk.Label(cleared, text="BOSS IS NEXT", bg="#243328", fg=BAD,
                     font=("Segoe UI", 9, "bold")).pack(side="right")

        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x", pady=(2, 2))
        tk.Label(top, text=res["word"], bg=BG, fg=TEXT,
                 font=("Georgia", 24, "bold")).pack(side="left")
        comp_text = f"Complexity {res['complexity']:.2f}"
        if abs(res.get("raw_complexity", res["complexity"]) - res["complexity"]) >= 0.01:
            comp_text += f"  (raw {res['raw_complexity']:.2f})"
        tk.Label(top, text=comp_text, bg=BG, fg=MUTED).pack(side="right")

        score = tk.Frame(self.main, bg=PANEL, padx=14, pady=9)
        score.pack(fill="x", pady=8)
        parts = [("Base", res["base"]), ("Mistakes", -res["mistake_penalty"]),
                 ("Speed", res["speed_bonus"]), ("Build bonus", res["glyph_bonus"])]
        for name, val in parts:
            text = f"{name}: {val:+,}" if name != "Base" else f"{name}: {val:,}"
            tk.Label(score, text=text, bg=PANEL, fg=TEXT).pack(side="left", expand=True)
        tk.Label(score, text=f"×{res['multiplier']:.2f}  →  +{res['total']:,}",
                 bg=PANEL, fg=ACCENT, font=("Segoe UI", 11, "bold")).pack(side="left", expand=True)

        tk.Label(self.main, text="Choose one Glyph", bg=BG, fg=TEXT,
                 font=("Georgia", 17, "bold")).pack(pady=(2, 3))
        tk.Label(self.main, text=f"{len(g.glyph_offers)} option{'s' if len(g.glyph_offers)!=1 else ''} offered on {g.difficulty_def.name}.",
                 bg=BG, fg="#77777e", font=("Segoe UI", 8)).pack()
        self.offer_frame = tk.Frame(self.main, bg=BG)
        self.offer_frame.pack(fill="x", pady=5)
        self._render_glyph_offers()

        controls = tk.Frame(self.main, bg=BG)
        controls.pack(pady=8)
        self.reroll_button = tk.Button(controls, command=self.reroll_glyphs, bg=PANEL2,
                                       fg=TEXT, relief="flat", padx=16, pady=6)
        self.reroll_button.pack(side="left", padx=5)
        tk.Button(controls, text="Skip", command=self.skip_glyph, bg=PANEL2, fg=MUTED,
                  relief="flat", padx=16, pady=6).pack(side="left", padx=5)
        self._safe_screen_button(controls)
        self.choice_message = tk.Label(self.main, text="", bg=BG, fg=BAD)
        self.choice_message.pack()
        self._build_side_panel()
        self._update_reroll_label()

    def _render_glyph_offers(self):
        self.clear(self.offer_frame)
        count = max(1, len(self.game.glyph_offers))
        wrap = {1: 430, 2: 280, 3: 200}.get(count, 155)
        for i, gid in enumerate(self.game.glyph_offers):
            gd = GLYPHS[gid]
            card = tk.Frame(self.offer_frame, bg=PANEL, padx=10, pady=10,
                            highlightbackground=RARITY_COLOR.get(gd.rarity, "#44444b"), highlightthickness=2 if gd.rarity == "Rare" else 1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=gd.name, bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card, text=f"{gd.category} • {gd.rarity}", bg=PANEL,
                     fg=RARITY_COLOR.get(gd.rarity, MUTED),
                     font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(1, 4))
            tk.Label(card, text=gd.description, bg=PANEL, fg=MUTED, justify="left",
                     wraplength=wrap, font=("Segoe UI", 8)).pack(anchor="w", fill="x", expand=True)
            tk.Button(card, text="TAKE", command=lambda idx=i: self.take_glyph(idx),
                      bg=ACCENT, fg=BG, relief="flat", pady=5).pack(fill="x", pady=(8, 0))

    def _update_reroll_label(self):
        if hasattr(self, "reroll_button"):
            cost = self.game.glyph_reroll_cost()
            self.reroll_button.config(text=f"Reroll — {cost} Points" if cost else "Reroll — FREE")

    def reroll_glyphs(self):
        ok, msg = self.game.reroll_glyphs()
        self.choice_message.config(text=msg, fg=GOOD if ok else BAD)
        if ok:
            self.sound.play("reroll")
            self._render_glyph_offers()
            self._refresh_side()
            self._update_reroll_label()

    def take_glyph(self, offer_idx):
        g = self.game
        if len(g.glyphs) < g.glyph_slots():
            ok, msg = g.take_glyph(offer_idx)
        else:
            dlg = tk.Toplevel(self.root)
            dlg.title("Replace Glyph")
            dlg.configure(bg=PANEL)
            dlg.transient(self.root)
            dlg.grab_set()
            dlg.geometry("560x560")
            incoming = GLYPHS[g.glyph_offers[offer_idx]]
            tk.Label(dlg, text=f"Replace a Glyph with {incoming.name}", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 11, "bold")).pack(pady=(12, 3))
            tk.Label(dlg, text=incoming.description, bg=PANEL, fg=MUTED, justify="left",
                     wraplength=500).pack(padx=20, pady=(0, 10))

            def choose(idx):
                g.take_glyph(offer_idx, idx)
                self.sound.play("select")
                dlg.destroy()
                self.continue_from_choice()

            for i, gid in enumerate(g.glyphs):
                gd = GLYPHS[gid]
                text = f"{gd.name}  [{gd.category} • {gd.rarity}]\n{g.glyph_description(gid)}"
                tk.Button(dlg, text=text, command=lambda idx=i: choose(idx), bg=PANEL2, fg=TEXT,
                          activebackground="#36363d", activeforeground=TEXT, relief="flat",
                          justify="left", anchor="w", padx=10, pady=7,
                          wraplength=490).pack(fill="x", padx=18, pady=3)
            tk.Button(dlg, text="Cancel", command=dlg.destroy, bg=PANEL, fg=MUTED,
                      relief="flat").pack(pady=8)
            return
        if ok:
            self.sound.play("select")
            self.continue_from_choice()
        else:
            self.choice_message.config(text=msg, fg=BAD)

    def skip_glyph(self):
        self.game.skip_glyph()
        self.sound.play("select")
        self.continue_from_choice()

    def continue_from_choice(self):
        if not self.game:
            self.show_main_menu()
            return
        if self.game.status == "playing":
            self.show_play()
        elif self.game.status == "boss_ready":
            self.show_boss_intro()
        elif self.game.status == "glyph_choice":
            self.show_glyph_choice()
        elif self.game.status == "axiom_choice":
            self.show_axiom_choice()
        elif self.game.status == "won":
            self.show_end(True)
        elif self.game.status == "lost":
            self.show_end(False)

    def show_axiom_choice(self):
        self.screen = "axiom_choice"
        self.presentation_paused = True
        self._run_chrome()
        self.clear(self.main)
        self.clear(self.side)
        g = self.game
        self.header_info.config(text=f"Boss defeated  •  {g.completed_chapters} Chapters complete  •  {g.difficulty_def.name}")
        cleared_chapter = max(1, g.completed_chapters)
        clearbox = tk.Frame(self.main, bg="#243328", padx=14, pady=10,
                            highlightbackground="#42634c", highlightthickness=1)
        clearbox.pack(fill="x", pady=(0, 9))
        tk.Label(clearbox, text=f"CHAPTER {cleared_chapter} CLEARED", bg="#243328", fg=GOOD,
                 font=("Georgia", 16, "bold")).pack(side="left")
        tk.Label(clearbox, text=f"{g.CHAPTERS - cleared_chapter} chapters remain" if not g.endless and cleared_chapter < g.CHAPTERS else "Main run complete" if cleared_chapter >= g.CHAPTERS and not g.endless else "Endless continues",
                 bg="#243328", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="right")
        if not (g.completed_chapters >= g.CHAPTERS and not g.endless):
            self._chapter_progress(self.main)
            self._boss_banner(self.main, g.current_boss_id, "upcoming")
        tk.Label(self.main, text="Choose an Axiom", bg=BG, fg=TEXT,
                 font=("Georgia", 23, "bold")).pack(pady=(16, 4))
        tk.Label(self.main,
                 text=f"Permanent run rules • {len(g.axiom_offers)} option{'s' if len(g.axiom_offers)!=1 else ''} offered on {g.difficulty_def.name}",
                 bg=BG, fg=MUTED).pack(pady=(0, 10))
        self.ax_offer_frame = tk.Frame(self.main, bg=BG)
        self.ax_offer_frame.pack(fill="x", pady=8)
        self._render_axiom_offers()
        controls = tk.Frame(self.main, bg=BG)
        controls.pack(pady=10)
        self.ax_message = tk.Label(self.main, text="", bg=BG, fg=BAD)
        self.ax_message.pack()
        if g.has_axiom("second_opinion") and g.axiom_offers:
            tk.Button(controls, text="Reroll Axioms — 500 Points", command=self.reroll_axioms,
                      bg=PANEL2, fg=TEXT, relief="flat", padx=16, pady=7).pack(side="left", padx=5)
        self._safe_screen_button(controls)
        self._build_side_panel()
        self.sound.play("chapter")

    def _render_axiom_offers(self):
        self.clear(self.ax_offer_frame)
        if not self.game.axiom_offers:
            tk.Label(self.ax_offer_frame, text="Every available Axiom has been collected.",
                     bg=BG, fg=MUTED).pack(pady=12)
            tk.Button(self.ax_offer_frame, text="CONTINUE", command=self.continue_no_axiom,
                      bg=ACCENT, fg=BG, relief="flat", padx=18, pady=7).pack()
            return
        count = len(self.game.axiom_offers)
        wrap = {1: 500, 2: 320, 3: 215}.get(count, 160)
        for i, aid in enumerate(self.game.axiom_offers):
            a = AXIOMS[aid]
            card = tk.Frame(self.ax_offer_frame, bg=PANEL, padx=12, pady=12,
                            highlightbackground="#6d5934", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=a.name, bg=PANEL, fg=ACCENT,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=a.description, bg=PANEL, fg=TEXT, justify="left",
                     wraplength=wrap, font=("Segoe UI", 8)).pack(anchor="w", fill="x", expand=True, pady=7)
            tk.Button(card, text="TAKE AXIOM", command=lambda idx=i: self.take_axiom(idx),
                      bg=ACCENT, fg=BG, relief="flat", pady=6).pack(fill="x", pady=(8, 0))

    def continue_no_axiom(self):
        if self.game.continue_without_axiom():
            self.continue_from_choice()

    def reroll_axioms(self):
        ok, msg = self.game.reroll_axioms()
        self.ax_message.config(text=msg, fg=GOOD if ok else BAD)
        if ok:
            self.sound.play("reroll")
            self._render_axiom_offers()
            self._refresh_side()

    def take_axiom(self, idx):
        ok, msg = self.game.take_axiom(idx)
        if ok:
            self.sound.play("select")
            self.continue_from_choice()
        else:
            self.ax_message.config(text=msg)

    def trash_glyph(self, idx):
        if not self.game:
            return
        gd = GLYPHS[self.game.glyphs[idx]]
        extra = "\nRecycling will refund Points." if self.game.has_axiom("recycling") else ""
        if messagebox.askyesno("Trash Glyph", f"Trash {gd.name}?{extra}"):
            self.game.trash_glyph(idx)
            self.sound.play("select")
            self._refresh_side()

    def _finish_and_menu(self):
        if self.game:
            self.storage.finalize_run(self.game)
            self.storage.delete_run_save()
        self.show_main_menu()

    def _build_archetype(self, game):
        counts = {}
        for gid in game.glyphs:
            cat = GLYPHS[gid].category
            counts[cat] = counts.get(cat, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if not ranked:
            return "UNFINISHED MANUSCRIPT"
        names = [name.upper() for name, _ in ranked[:2]]
        return " / ".join(names)

    def show_end(self, won):
        self.screen = "end"
        self.presentation_paused = True
        self._run_chrome()
        self.clear(self.main)
        self.clear(self.side)
        g = self.game
        self.storage.delete_run_save()
        if won:
            self.storage.record_main_win(g)
        else:
            self.storage.finalize_run(g)
        self.header_info.config(text=f"{g.difficulty_def.name}  •  Seed {g.seed}")
        self.sound.play("win" if won else "lose")
        if won:
            title = "RUN COMPLETE"
            sub = "You survived all eight Chapters."
            color = GOOD
        else:
            title = "RUN OVER"
            sub = f"The word was {g.round.word.word.upper()}."
            color = BAD
        tk.Label(self.main, text=title, bg=BG, fg=color,
                 font=("Georgia", 29, "bold")).pack(pady=(32, 6))
        tk.Label(self.main, text=sub, bg=BG, fg=TEXT, font=("Segoe UI", 13)).pack()
        tk.Label(self.main, text=f"BUILD — {self._build_archetype(g)}", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(pady=(7, 2))

        rs = g.run_stats
        fastest = rs.get("fastest_solve")
        metrics = [
            ("Words cleared", f"{rs.get('words_solved', g.round_index)}"),
            ("Highest Chapter", f"{g.chapter}"),
            ("Total Points", f"{g.total_earned:,}"),
            ("Bosses defeated", f"{rs.get('bosses_defeated', g.completed_chapters)}"),
            ("Perfect words", f"{rs.get('perfect_words',0)}"),
            ("Highest Complexity", f"{float(rs.get('highest_complexity_solved',0)):.2f}"),
            ("Auto reveals", f"{rs.get('auto_reveals',0)}"),
            ("Fastest solve", f"{fastest:.1f}s" if isinstance(fastest,(int,float)) else "—"),
        ]
        grid = tk.Frame(self.main, bg=BG); grid.pack(fill="x", padx=40, pady=14)
        for i,(label,value) in enumerate(metrics):
            card=tk.Frame(grid,bg=PANEL,padx=10,pady=8,highlightbackground="#3b3b42",highlightthickness=1)
            card.grid(row=i//4,column=i%4,sticky="nsew",padx=4,pady=4)
            grid.grid_columnconfigure(i%4,weight=1)
            tk.Label(card,text=value,bg=PANEL,fg=ACCENT,font=("Georgia",13,"bold")).pack()
            tk.Label(card,text=label,bg=PANEL,fg=MUTED,font=("Segoe UI",7,"bold")).pack()

        buttons = tk.Frame(self.main, bg=BG); buttons.pack(pady=8)
        if won and not g.endless:
            tk.Button(buttons, text="CONTINUE ENDLESS", command=self.start_endless,
                      bg=ACCENT, fg=BG, relief="flat", padx=20, pady=9,
                      font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(buttons, text="MAIN MENU", command=self._finish_and_menu, bg=PANEL2,
                  fg=TEXT, relief="flat", padx=20, pady=9,
                  font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

        tk.Label(self.side, text="RUN BUILD", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        for gid in g.glyphs:
            gd = GLYPHS[gid]
            tk.Label(self.side, text=f"• {gd.name}", bg=PANEL, fg=TEXT, anchor="w",
                     font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(3, 0))
            tk.Label(self.side, text=g.glyph_description(gid), bg=PANEL, fg=MUTED,
                     anchor="w", justify="left", wraplength=315,
                     font=("Segoe UI", 8)).pack(fill="x", padx=(10, 0))
        if g.axioms:
            tk.Label(self.side, text="AXIOMS", bg=PANEL, fg=ACCENT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(16, 4))
            for aid in g.axioms:
                a = AXIOMS[aid]
                tk.Label(self.side, text=f"• {a.name}", bg=PANEL, fg=TEXT, anchor="w",
                         font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(3, 0))
                tk.Label(self.side, text=a.description, bg=PANEL, fg=MUTED,
                         anchor="w", justify="left", wraplength=315,
                         font=("Segoe UI", 8)).pack(fill="x", padx=(10, 0))

    def start_endless(self):
        if self.game and self.game.continue_endless():
            self.storage.record_endless_entered(self.game)
            self.sound.play("chapter")
            self.continue_from_choice()

    def on_key(self, event):
        if self.screen == "title":
            self.show_main_menu()
            return "break"
        if not self.game or self.game.status != "playing":
            return
        focus = self.root.focus_get()
        if hasattr(self, "word_entry") and focus is self.word_entry:
            return
        if event.char == "/" and hasattr(self, "word_entry") and str(self.word_entry.cget("state")) != "disabled":
            self.word_entry.focus_set()
            return "break"
        ch = event.char.lower()
        if len(ch) == 1 and ch.isalpha():
            self.guess_letter(ch)
            return "break"

    def loop(self):
        now = time.perf_counter()
        dt = min(0.2, now - self.last_clock)
        self.last_clock = now
        if self.game and self.game.status == "playing" and not self.presentation_paused:
            result = self.game.tick(dt)
            if result and result.get("rescued") and hasattr(self, "effect_label"):
                self.effect_label.config(text=result.get("message", "SECOND DRAFT — rescued from timeout"), fg=ACCENT)
                self.sound.play("reveal")
            if self.game.status == "lost":
                self.show_end(False)
            else:
                self.refresh_play()
        self.root.after(50, self.loop)


def main():
    root = tk.Tk()
    DeadLetterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
