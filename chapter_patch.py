"""Chapter-preview flow for Dead Letter v1.1.10.

Applied after the existing presentation patches.  The preview is a safe,
untimed gate at the start of every Chapter, including Chapter 1 and Endless.
"""
from __future__ import annotations

import tkinter as tk

from content import BOSSES, BOSS_COMPLEXITY_BUDGET
from game_logic import GameState

M = None


def _target_at(game: GameState, round_index: int, boss_id: str | None = None) -> float:
    """Mirror GameState.target_for_round without mutating run progression."""
    if round_index <= 31:
        progress = round_index / 31
        target = 1.80 + 6.40 * (progress ** 1.10)
    else:
        extra_chapters = (round_index - 31) / 4.0
        target = 8.20 + 0.12 * extra_chapters
    if game.has_axiom("high_standards"):
        target += 0.5
    if boss_id:
        target -= BOSS_COMPLEXITY_BUDGET.get(boss_id, 0.25)
    return max(1.0, min(9.70, target))


def _base_time_at(game: GameState, round_index: int) -> float:
    """Mirror the predictable portion of GameState.base_time_for_round."""
    if round_index <= 31:
        progress = round_index / 31
        base = 50.0 - 28.0 * progress
    else:
        extra_chapters = (round_index - 31) / 4.0
        base = max(14.0, 22.0 - 0.45 * extra_chapters)
    if game.has_axiom("long_game"):
        completed = round_index // game.WORDS_PER_CHAPTER
        base += min(8.0, 0.5 * completed)
    return base


def _predictable_glyph_time_delta(game: GameState, first_round: bool) -> float:
    """Starting-time Glyph effects that do not depend on the unseen word."""
    delta = 0.0
    if game.has_glyph("pencil_eraser"):
        delta -= 3.0
    if game.has_glyph("hourglass"):
        delta += 7.0
    if game.has_glyph("rush_job"):
        delta -= 7.0
    if game.has_glyph("nest_egg") and game.points >= 1500:
        delta += 3.0
    if game.has_glyph("inkblot"):
        delta -= 5.0
    if game.has_glyph("double_entry"):
        delta -= 4.0
    if game.has_glyph("deadline_writer"):
        delta += float(game.glyph_state.get("deadline_writer_time", 0.0))
    if game.has_glyph("rolling_press"):
        delta += float(game.glyph_state.get("rolling_press_time", 0.0))
    if first_round:
        delta += float(getattr(game, "next_word_time_bonus", 0.0))
    return delta


def _time_at(game: GameState, round_index: int, boss_id: str | None = None, *, first_round=False) -> float:
    """Estimate the starting timer before word-dependent/random Glyph effects."""
    initial = 18.0 if boss_id == "deadline" else _base_time_at(game, round_index)
    initial += game.difficulty_def.time_delta
    if game.has_axiom("countermeasure") and boss_id:
        initial += 4.0
    if game.has_axiom("grace_period"):
        initial += 4.0
    if game.has_axiom("overtime"):
        initial += 3.0
    if game.has_axiom("sharp_deadline"):
        initial -= 3.0
    if game.has_axiom("archive"):
        initial -= 3.0
    initial += _predictable_glyph_time_delta(game, first_round)
    if game.has_glyph("deadline_extension") and initial < 24.0:
        initial += 6.0
    return max(8.0, initial)


def _chapter_preview_values(game: GameState):
    start = game.round_index
    boss_id = game.current_boss_id
    complexities = []
    times = []
    for offset in range(game.WORDS_PER_CHAPTER):
        index = start + offset
        is_boss = offset == game.WORDS_PER_CHAPTER - 1
        rid = boss_id if is_boss else None
        complexities.append(_target_at(game, index, rid))
        times.append(_time_at(game, index, rid, first_round=(offset == 0)))
    return {
        "boss_id": boss_id,
        "avg_complexity": sum(complexities) / len(complexities),
        "min_complexity": min(complexities),
        "max_complexity": max(complexities),
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
    }


def patched_start_round(game: GameState):
    """Gate only the first round of each Chapter behind the preview screen."""
    at_chapter_start = game.round_index % game.WORDS_PER_CHAPTER == 0
    entering = bool(getattr(game, "_chapter_preview_entering", False))

    # Preserve the normal main-run victory guard if start_round is ever called
    # after Chapter 8 without Endless having been entered.
    main_run_finished = game.round_index >= game.CHAPTERS * game.WORDS_PER_CHAPTER and not game.endless
    if at_chapter_start and not entering and not main_run_finished:
        game.round = None
        game.status = "chapter_ready"
        return None
    return original_start_round(game)


def patched_can_save(game: GameState):
    return game.status == "chapter_ready" or original_can_save(game)


def show_chapter_intro(self):
    if not self.game or self.game.status != "chapter_ready":
        return

    g = self.game
    preview = _chapter_preview_values(g)
    boss = BOSSES[preview["boss_id"]]

    self.screen = "chapter_intro"
    self.presentation_paused = True
    self._run_chrome()
    self.clear(self.main)
    self.clear(self.side)

    bank_name = M.BANKS.get(g.bank_id, M.BANKS["standard"]).name
    self.header_info.config(text=f"{g.difficulty_def.name}  •  {bank_name}  •  Seed {g.seed}")

    outer = tk.Frame(self.main, bg=M.BG, padx=42, pady=24)
    outer.pack(fill="both", expand=True)

    top_rule = tk.Frame(outer, bg=M.ACCENT, height=2)
    top_rule.pack(fill="x", pady=(4, 22))

    endless = g.endless or g.chapter > g.CHAPTERS
    chapter_label = f"CHAPTER {g.chapter}" + ("  •  ENDLESS" if endless else f" / {g.CHAPTERS}")
    tk.Label(
        outer,
        text=chapter_label,
        bg=M.BG,
        fg=M.ACCENT,
        font=("Segoe UI", 11, "bold"),
    ).pack()
    tk.Label(
        outer,
        text=f"CHAPTER {g.chapter}",
        bg=M.BG,
        fg=M.TEXT,
        font=("Georgia", 34, "bold"),
    ).pack(pady=(5, 4))
    tk.Label(
        outer,
        text="CHAPTER PREVIEW",
        bg=M.BG,
        fg=M.MUTED,
        font=("Segoe UI", 9, "bold"),
    ).pack(pady=(0, 20))

    stats = tk.Frame(outer, bg=M.BG)
    stats.pack(fill="x", padx=30)
    for col in range(2):
        stats.grid_columnconfigure(col, weight=1, uniform="preview_stats")

    comp = tk.Frame(
        stats,
        bg=M.PANEL,
        padx=22,
        pady=17,
        highlightbackground="#4b4334",
        highlightthickness=1,
    )
    comp.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    tk.Label(comp, text="AVG TARGET COMPLEXITY", bg=M.PANEL, fg=M.MUTED,
             font=("Segoe UI", 9, "bold")).pack()
    tk.Label(comp, text=f"{preview['avg_complexity']:.2f} / 10", bg=M.PANEL, fg=M.ACCENT,
             font=("Georgia", 25, "bold")).pack(pady=(6, 3))
    tk.Label(comp,
             text=f"Expected targets {preview['min_complexity']:.2f}–{preview['max_complexity']:.2f}",
             bg=M.PANEL, fg="#85827c", font=("Segoe UI", 8)).pack()

    timer = tk.Frame(
        stats,
        bg=M.PANEL,
        padx=22,
        pady=17,
        highlightbackground="#3a444b",
        highlightthickness=1,
    )
    timer.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    tk.Label(timer, text="AVG STARTING TIME", bg=M.PANEL, fg=M.MUTED,
             font=("Segoe UI", 9, "bold")).pack()
    tk.Label(timer, text=f"{preview['avg_time']:.1f}s", bg=M.PANEL, fg=M.BLUE,
             font=("Georgia", 25, "bold")).pack(pady=(6, 3))
    tk.Label(timer,
             text=f"Expected range {preview['min_time']:.0f}–{preview['max_time']:.0f}s",
             bg=M.PANEL, fg="#85827c", font=("Segoe UI", 8)).pack()

    boss_box = tk.Frame(
        outer,
        bg="#2c2022",
        padx=20,
        pady=16,
        highlightbackground="#6a3a3f",
        highlightthickness=1,
    )
    boss_box.pack(fill="x", padx=30, pady=(16, 4))
    tk.Label(boss_box, text="UPCOMING BOSS", bg="#2c2022", fg=M.BAD,
             font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(boss_box, text=boss.name, bg="#2c2022", fg="#f2d4d5",
             font=("Georgia", 20, "bold")).pack(anchor="w", pady=(4, 3))
    tk.Label(boss_box, text=boss.description, bg="#2c2022", fg="#cfaeb0",
             justify="left", wraplength=850, font=("Segoe UI", 10)).pack(anchor="w")

    tk.Label(
        outer,
        text="Starting-time preview excludes word-dependent and random Glyph effects.",
        bg=M.BG,
        fg="#6f6d68",
        font=("Segoe UI", 8),
    ).pack(pady=(7, 3))

    actions = tk.Frame(outer, bg=M.BG)
    actions.pack(pady=(18, 8))
    tk.Button(
        actions,
        text="ENTER CHAPTER",
        command=self.enter_chapter,
        bg=M.ACCENT,
        fg=M.BG,
        activebackground="#e7be72",
        activeforeground=M.BG,
        relief="flat",
        bd=0,
        highlightthickness=0,
        padx=38,
        pady=12,
        font=("Segoe UI", 11, "bold"),
        cursor="hand2",
    ).pack(side="left", padx=5)
    self._safe_screen_button(actions)

    self._build_side_panel()
    self.sound.play("chapter")
    self.root.focus_set()


def enter_chapter(self):
    if not self.game or self.game.status != "chapter_ready":
        return
    g = self.game
    g._chapter_preview_entering = True
    try:
        g.start_round()
    finally:
        try:
            delattr(g, "_chapter_preview_entering")
        except AttributeError:
            pass
    self.storage.delete_run_save()
    self.presentation_paused = False
    self.sound.play("select")
    self.continue_from_choice()


def patched_continue_from_choice(self):
    if self.game and self.game.status == "chapter_ready":
        self.show_chapter_intro()
        return
    return original_continue_from_choice(self)


def apply_patch(main_module):
    global M
    global original_start_round, original_can_save, original_continue_from_choice

    M = main_module
    original_start_round = GameState.start_round
    original_can_save = GameState.can_save
    original_continue_from_choice = main_module.DeadLetterApp.continue_from_choice

    GameState.start_round = patched_start_round
    GameState.can_save = patched_can_save

    cls = main_module.DeadLetterApp
    cls.show_chapter_intro = show_chapter_intro
    cls.enter_chapter = enter_chapter
    cls.continue_from_choice = patched_continue_from_choice
