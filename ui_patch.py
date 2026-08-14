"""v1.1.2 presentation consistency patch.

Kept separate from the large prototype UI module so small public-release polish
can be maintained without rewriting the gameplay controller.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

M = None

BANK_EXAMPLES = {
    "standard": "Examples: ELEPHANT • QUARTZ • RHYTHM",
    "common_tongue": "Examples: HOUSE • MARKET • GARDEN",
    "bookish": "Examples: ARCHITECTURE • OBSERVATORY • MAGNITUDE",
    "quickfire": "Examples: JAZZ • GYM • SAFE",
    "labyrinth": "Examples: MYRRH • SYZYGY • QUEUE",
}

RARITY_ORDER = {"Common": 0, "Uncommon": 1, "Rare": 2}


def _styled_select_button(parent, text, command, selected=False, accent=None):
    accent = accent or M.ACCENT
    bg = accent if selected else M.PANEL2
    fg = M.BG if selected else M.TEXT
    active_bg = bg if selected else "#36363d"
    return tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=active_bg, activeforeground=fg,
        disabledforeground=fg, relief="flat", bd=0, highlightthickness=0,
        pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2", takefocus=0,
    )


def patched_init(self, root):
    original_init(self, root)
    if getattr(sys, "frozen", False):
        install_dir = Path(sys.executable).resolve().parent
        self.update_manager = M.UpdateManager(install_dir, M.GAME_VERSION)
        # v1.1.1 used the legacy batch launcher. Remove it after the first
        # successful executable launch so an in-place update looks clean too.
        try:
            (install_dir / "run_game.bat").unlink(missing_ok=True)
        except OSError:
            pass
        for icon in (
            install_dir / "DeadLetter.ico",
            Path(getattr(sys, "_MEIPASS", install_dir)) / "DeadLetter.ico",
        ):
            try:
                if icon.exists():
                    self.root.iconbitmap(str(icon))
                    break
            except tk.TclError:
                pass


def patched_show_title(self):
    self.screen = "title"
    self.presentation_paused = True
    self.clear(self.main); self.clear(self.side)
    self._menu_chrome(f"v{M.GAME_VERSION}")
    canvas = tk.Canvas(self.main, bg=M.BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    self.title_canvas = canvas

    def redraw(_event=None):
        if self.screen != "title" or not canvas.winfo_exists():
            return
        canvas.delete("static")
        w = max(900, canvas.winfo_width()); h = max(620, canvas.winfo_height())
        canvas.create_rectangle(42, 34, w - 42, h - 34, outline="#2f2f34", width=1, tags="static")
        canvas.create_line(72, 80, w - 72, 80, fill="#6a5432", width=1, tags="static")
        canvas.create_line(72, h - 78, w - 72, h - 78, fill="#6a5432", width=1, tags="static")
        gx = int(w * 0.73); gy = int(h * 0.30); fg = "#746f67"
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
        canvas.create_oval(gx + 118, gy + 176, gx + 172, gy + 230, fill="#6f2c31", outline="#a64a50", width=2, tags="static")
        canvas.create_text(gx + 145, gy + 203, text="DL", fill="#e8d8c7", font=("Georgia", 12, "bold"), tags="static")
        tx = int(w * 0.31)
        canvas.create_text(tx, int(h * 0.37), text="DEAD LETTER", fill=M.TEXT, font=("Georgia", 48, "bold"), tags="static")
        canvas.create_text(tx, int(h * 0.37) + 64, text="A  H A N G M A N  R O G U E L I K E", fill=M.ACCENT, font=("Segoe UI", 11, "bold"), tags="static")
        canvas.create_text(tx, h - 128, text="PRESS ANY KEY", fill=M.ACCENT, font=("Segoe UI", 11, "bold"), tags=("static", "prompt"))
        canvas.create_text(tx, h - 100, text="or click to continue", fill="#6e6b66", font=("Segoe UI", 8), tags="static")

    canvas.bind("<Configure>", redraw)
    canvas.bind("<Button-1>", lambda _e: self.show_main_menu())
    redraw()
    def pulse(on=True):
        if self.screen != "title" or not canvas.winfo_exists(): return
        canvas.itemconfigure("prompt", fill=M.ACCENT if on else "#7a6849")
        self.root.after(620, lambda: pulse(not on))
    pulse(); self.root.focus_set()


def patched_show_start(self):
    self.screen = "new_run"; self.presentation_paused = True
    self.clear(self.main); self.clear(self.side); self._menu_chrome("New Run")
    outer = tk.Frame(self.main, bg=M.BG, padx=48, pady=20); outer.pack(fill="both", expand=True)
    top = tk.Frame(outer, bg=M.BG); top.pack(fill="x")
    tk.Label(top, text="NEW RUN", bg=M.BG, fg=M.TEXT, font=("Georgia", 28, "bold")).pack(side="left")
    self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")

    tk.Label(outer, text="DIFFICULTY", bg=M.BG, fg=M.ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 7))
    cards = tk.Frame(outer, bg=M.BG); cards.pack(fill="x")
    colors = {"easy": M.GOOD, "medium": M.ACCENT, "hard": M.BAD}
    for did in ("easy", "medium", "hard"):
        d = M.DIFFICULTIES[did]; chosen = did == self.selected_difficulty
        f = tk.Frame(cards, bg=M.PANEL, padx=15, pady=12,
                     highlightbackground=colors[did] if chosen else "#3b3b42",
                     highlightthickness=2 if chosen else 1)
        f.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(f, text=d.name.upper(), bg=M.PANEL, fg=colors[did], font=("Georgia", 15, "bold")).pack(anchor="w")
        timing = "Standard time" if d.time_delta == 0 else f"{d.time_delta:+.0f}s starting time"
        option_word = "option" if d.glyph_choices == 1 else "options"
        tk.Label(f, text=f"{timing}\n{d.glyph_choices} Glyph / {d.axiom_choices} Axiom {option_word}",
                 bg=M.PANEL, fg=M.MUTED, justify="left", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 9))
        _styled_select_button(f, "SELECTED" if chosen else "SELECT", lambda x=did: self.select_difficulty(x),
                              selected=chosen, accent=colors[did]).pack(fill="x")

    tk.Label(outer, text="WORD BANK", bg=M.BG, fg=M.ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(18, 7))
    bank_area = tk.Frame(outer, bg=M.BG); bank_area.pack(fill="both", expand=True)
    bank_items = list(M.BANKS.items())
    for row_index, row_items in enumerate((bank_items[:3], bank_items[3:])):
        row = tk.Frame(bank_area, bg=M.BG); row.pack(fill="both", expand=True, pady=(0, 8 if row_index == 0 else 0))
        for bid, bdef in row_items:
            chosen = bid == self.selected_bank_id
            f = tk.Frame(row, bg=M.PANEL, padx=18, pady=14,
                         highlightbackground=M.ACCENT if chosen else "#3b3b42",
                         highlightthickness=2 if chosen else 1)
            f.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(f, text=bdef.name.upper(), bg=M.PANEL, fg=M.ACCENT if chosen else M.TEXT,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(f, text=bdef.description, bg=M.PANEL, fg="#c7c7cd", wraplength=520,
                     justify="left", anchor="nw", font=("Segoe UI", 10)).pack(anchor="w", fill="x", expand=True, pady=(6, 5))
            tk.Label(f, text=BANK_EXAMPLES.get(bid, ""), bg=M.PANEL, fg=M.ACCENT,
                     wraplength=520, justify="left", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 10))
            _styled_select_button(f, "SELECTED" if chosen else "SELECT", lambda x=bid: self.select_word_bank(x),
                                  selected=chosen, accent=M.ACCENT).pack(fill="x")

    setup = tk.Frame(outer, bg=M.PANEL, padx=14, pady=10, highlightbackground="#3b3b42", highlightthickness=1)
    setup.pack(fill="x", pady=(12, 10))
    tk.Label(setup, text="Seed (optional)", bg=M.PANEL, fg=M.TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")
    self.seed_entry = tk.Entry(setup, bg=M.PANEL2, fg=M.TEXT, insertbackground=M.TEXT, relief="flat", width=18)
    self.seed_entry.pack(side="left", padx=10, ipady=4)
    tk.Label(setup, text="Same seed + difficulty + word bank reproduces the same rolls.", bg=M.PANEL, fg=M.MUTED, font=("Segoe UI", 8)).pack(side="left")
    actions = tk.Frame(outer, bg=M.BG); actions.pack(fill="x")
    self._menu_button(actions, "START RUN", self.new_run, primary=True, width=18).pack(side="left")
    self._menu_button(actions, "TUTORIAL", lambda: self.show_tutorial(0), width=14).pack(side="left", padx=8)
    tk.Label(outer, text=f"8 Chapters • 16 unique Bosses before repeats • {len(M.GLYPHS)} Glyphs • {len(M.AXIOMS)} Axioms",
             bg=M.BG, fg="#77777e", font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))


def patched_build_side_panel(self):
    self.points_label = tk.Label(self.side, text="", bg=M.PANEL, fg=M.ACCENT, font=("Georgia", 19, "bold")); self.points_label.pack(anchor="w")
    self.total_label = tk.Label(self.side, text="", bg=M.PANEL, fg=M.MUTED); self.total_label.pack(anchor="w", pady=(0, 8))
    self.hangman = tk.Canvas(self.side, height=295, bg=M.PANEL, highlightthickness=2, highlightbackground="#34343a"); self.hangman.pack(fill="x", pady=(3, 8))
    inventory_wrap = tk.Frame(self.side, bg=M.PANEL); inventory_wrap.pack(fill="both", expand=True, pady=(2, 0))
    self.inventory_canvas = tk.Canvas(inventory_wrap, bg=M.PANEL, highlightthickness=0, bd=0)
    self.inventory_scroll = tk.Scrollbar(inventory_wrap, orient="vertical", command=self.inventory_canvas.yview)
    self.inventory_canvas.configure(yscrollcommand=self.inventory_scroll.set)
    self.inventory_scroll.pack(side="right", fill="y"); self.inventory_canvas.pack(side="left", fill="both", expand=True)
    self.inventory_inner = tk.Frame(self.inventory_canvas, bg=M.PANEL)
    self.inventory_window = self.inventory_canvas.create_window((0, 0), window=self.inventory_inner, anchor="nw")
    self.inventory_inner.bind("<Configure>", self._sync_inventory_scrollregion); self.inventory_canvas.bind("<Configure>", self._sync_inventory_width)
    self.inventory_canvas.bind("<Enter>", self._bind_inventory_wheel); self.inventory_canvas.bind("<Leave>", self._unbind_inventory_wheel)
    tk.Label(self.inventory_inner, text="GLYPHS", bg=M.PANEL, fg=M.ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(3, 5))
    self.glyph_frame = tk.Frame(self.inventory_inner, bg=M.PANEL); self.glyph_frame.pack(fill="x")
    tk.Label(self.inventory_inner, text="AXIOMS", bg=M.PANEL, fg=M.ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(13, 5))
    self.axiom_frame = tk.Frame(self.inventory_inner, bg=M.PANEL); self.axiom_frame.pack(fill="x")
    self._side_inventory_signature = None; self._refresh_side()


def patched_refresh_side(self):
    if not self.game: return
    g = self.game
    if hasattr(self, "points_label"):
        self.points_label.config(text=f"{g.points:,} Points"); mode = " • Endless" if g.endless else ""
        self.total_label.config(text=f"{g.total_earned:,} total earned{mode}")
    if not hasattr(self, "glyph_frame") or not hasattr(self, "axiom_frame"): return
    state_sig = tuple(sorted((k, str(v)) for k, v in g.glyph_state.items()))
    signature = (tuple(g.glyphs), tuple(g.axioms), g.glyph_slots(), state_sig)
    if signature == self._side_inventory_signature: return
    self._side_inventory_signature = signature
    old_y = self.inventory_canvas.yview()[0] if hasattr(self, "inventory_canvas") else 0.0
    self.clear(self.glyph_frame)
    for i in range(g.glyph_slots()):
        occupied = i < len(g.glyphs); card_bg = M.PANEL2 if occupied else M.PANEL; border = "#44444b" if occupied else "#303035"
        row = tk.Frame(self.glyph_frame, bg=card_bg, padx=8, pady=7, highlightbackground=border, highlightthickness=1); row.pack(fill="x", pady=3)
        if occupied:
            gid = g.glyphs[i]; gd = M.GLYPHS[gid]; top = tk.Frame(row, bg=card_bg); top.pack(fill="x")
            tk.Label(top, text=f"{i+1}. {gd.name}", bg=card_bg, fg=M.TEXT, font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(top, text=gd.rarity.upper(), bg=card_bg, fg=M.RARITY_COLOR.get(gd.rarity, M.MUTED), font=("Segoe UI", 7, "bold")).pack(side="left", padx=(4, 3))
            tk.Button(top, text="×", command=lambda idx=i: self.trash_glyph(idx), bg=card_bg, fg=M.BAD, activebackground=card_bg, activeforeground=M.BAD,
                      relief="flat", width=2, bd=0, highlightthickness=0).pack(side="right")
            tk.Label(row, text=g.glyph_description(gid), bg=card_bg, fg=M.MUTED, justify="left", anchor="w", wraplength=298, font=("Segoe UI", 8)).pack(fill="x", pady=(3, 0))
        else:
            tk.Label(row, text=f"{i+1}. — empty —", bg=card_bg, fg="#6f6f76", anchor="w", font=("Segoe UI", 9)).pack(fill="x")
    self.clear(self.axiom_frame)
    if g.axioms:
        for aid in g.axioms:
            a = M.AXIOMS[aid]; card = tk.Frame(self.axiom_frame, bg="#27272c", padx=8, pady=7, highlightbackground="#4c463a", highlightthickness=1); card.pack(fill="x", pady=3)
            tk.Label(card, text=a.name, bg="#27272c", fg=M.ACCENT, font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(card, text=a.description, bg="#27272c", fg=M.MUTED, justify="left", anchor="w", wraplength=298, font=("Segoe UI", 8)).pack(fill="x", pady=(3, 0))
    else:
        tk.Label(self.axiom_frame, text="None yet", bg=M.PANEL, fg=M.MUTED, anchor="w").pack(fill="x", pady=(0, 4))
    self.inventory_inner.update_idletasks(); self._sync_inventory_scrollregion(); self.inventory_canvas.yview_moveto(old_y)


def patched_draw_hangman(self):
    if not hasattr(self, "hangman") or not self.game or not self.game.round: return
    c = self.hangman; c.delete("all"); r = self.game.round
    remaining = max(0, r.max_mistakes - r.mistakes); danger = remaining == 1
    pulse = True if self.settings.get("reduced_motion", False) else int(M.time.perf_counter() * 4) % 2 == 0
    fg = M.BAD if danger and pulse else "#aaa69b"
    c.configure(highlightbackground=M.BAD if danger and pulse else "#34343a", bg="#2d2022" if danger and pulse else M.PANEL)
    bonus_capacity = max(0, r.max_mistakes - 6)
    figure_mistakes = max(0, r.mistakes - bonus_capacity) if r.max_mistakes >= 6 else r.mistakes
    c.create_line(25, 218, 255, 218, fill=fg, width=4); c.create_line(58, 218, 58, 24, fill=fg, width=4)
    c.create_line(56, 24, 205, 24, fill=fg, width=4); c.create_line(205, 24, 205, 49, fill=fg, width=3)
    if figure_mistakes >= 1: c.create_oval(181, 49, 229, 97, outline=M.TEXT, width=3)
    if figure_mistakes >= 2: c.create_line(205, 97, 205, 159, fill=M.TEXT, width=3)
    if figure_mistakes >= 3: c.create_line(205, 112, 171, 139, fill=M.TEXT, width=3)
    if figure_mistakes >= 4: c.create_line(205, 112, 239, 139, fill=M.TEXT, width=3)
    if figure_mistakes >= 5: c.create_line(205, 159, 178, 199, fill=M.TEXT, width=3)
    if figure_mistakes >= 6: c.create_line(205, 159, 232, 199, fill=M.TEXT, width=3)
    if r.mistakes >= r.max_mistakes and figure_mistakes >= 1:
        c.create_line(192, 67, 199, 74, fill=M.BAD, width=3); c.create_line(199, 67, 192, 74, fill=M.BAD, width=3)
        c.create_line(211, 67, 218, 74, fill=M.BAD, width=3); c.create_line(218, 67, 211, 74, fill=M.BAD, width=3)
    c.create_text(18, 235, text="MISTAKE CAPACITY", fill=M.MUTED, anchor="w", font=("Segoe UI", 8, "bold"))
    count = max(1, r.max_mistakes); types = (["bonus"] * bonus_capacity) + (["base"] * max(0, count - bonus_capacity))
    gap = min(24, max(15, int(275 / max(1, count)))); x0 = 18
    for i, kind in enumerate(types):
        x = x0 + i * gap; used = i < r.mistakes; is_final_live = danger and i == r.mistakes; bonus = kind == "bonus"
        outline = M.BAD if is_final_live and pulse else (M.ACCENT if bonus else "#77746d")
        fill = M.BAD if used else ("#5a2529" if is_final_live and pulse else ("#4a3d24" if bonus else M.PANEL2))
        c.create_oval(x, 247, x + 15, 262, outline=outline, fill=fill, width=3 if is_final_live else (2 if bonus else 1))
        if is_final_live: c.create_text(x + 7.5, 254.5, text="!", fill=M.TEXT if pulse else M.BAD, font=("Segoe UI", 8, "bold"))
        elif bonus and not used: c.create_text(x + 7.5, 254.5, text="+", fill=M.ACCENT, font=("Segoe UI", 8, "bold"))
    if danger:
        c.create_text(18, 282, text="⚠ ONE MISTAKE LEFT — NEXT ONE ENDS THE RUN", fill=M.BAD if pulse else "#e6b3b3", anchor="w", font=("Segoe UI", 8, "bold"))
    elif bonus_capacity:
        unused_bonus = max(0, bonus_capacity - min(r.mistakes, bonus_capacity))
        c.create_text(18, 282, text=f"{unused_bonus} bonus mistake{'s' if unused_bonus != 1 else ''} before the Hangman starts drawing",
                      fill=M.ACCENT, anchor="w", font=("Segoe UI", 8, "bold"))
    elif r.max_mistakes < 6:
        c.create_text(18, 282, text=f"Reduced to {r.max_mistakes} mistakes this word", fill=M.BAD, anchor="w", font=("Segoe UI", 8, "bold"))
    else:
        c.create_text(18, 282, text="Standard six-part Hangman", fill="#77777e", anchor="w", font=("Segoe UI", 8))


def patched_render_glyph_offers(self):
    self.clear(self.offer_frame); count = max(1, len(self.game.glyph_offers)); wrap = {1: 430, 2: 300, 3: 215}.get(count, 165)
    for i, gid in enumerate(self.game.glyph_offers):
        gd = M.GLYPHS[gid]; color = M.RARITY_COLOR.get(gd.rarity, M.MUTED)
        card = tk.Frame(self.offer_frame, bg=M.PANEL, padx=11, pady=11, highlightbackground=color, highlightthickness=2 if gd.rarity == "Rare" else 1)
        card.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(card, text=gd.name, bg=M.PANEL, fg=M.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(card, text=gd.rarity.upper(), bg=M.PANEL, fg=color, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(1, 5))
        tk.Label(card, text=gd.description, bg=M.PANEL, fg=M.MUTED, justify="left", wraplength=wrap, font=("Segoe UI", 8)).pack(anchor="w", fill="x", expand=True)
        tk.Button(card, text="TAKE", command=lambda idx=i: self.take_glyph(idx), bg=M.ACCENT, fg=M.BG, activebackground="#e7be72", activeforeground=M.BG,
                  relief="flat", bd=0, highlightthickness=0, pady=5, font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(8, 0))


def patched_take_glyph(self, offer_idx):
    g = self.game
    if len(g.glyphs) < g.glyph_slots(): ok, msg = g.take_glyph(offer_idx)
    else:
        dlg = tk.Toplevel(self.root); dlg.title("Replace Glyph"); dlg.configure(bg=M.PANEL); dlg.transient(self.root); dlg.grab_set(); dlg.geometry("600x590")
        incoming = M.GLYPHS[g.glyph_offers[offer_idx]]; color = M.RARITY_COLOR.get(incoming.rarity, M.MUTED)
        tk.Label(dlg, text=f"Replace a Glyph with {incoming.name}", bg=M.PANEL, fg=M.TEXT, font=("Segoe UI", 11, "bold")).pack(pady=(12, 2))
        tk.Label(dlg, text=incoming.rarity.upper(), bg=M.PANEL, fg=color, font=("Segoe UI", 8, "bold")).pack()
        tk.Label(dlg, text=incoming.description, bg=M.PANEL, fg=M.MUTED, justify="left", wraplength=540).pack(padx=20, pady=(4, 10))
        def choose(idx):
            g.take_glyph(offer_idx, idx); self.sound.play("select"); dlg.destroy(); self.continue_from_choice()
        for i, gid in enumerate(g.glyphs):
            gd = M.GLYPHS[gid]; row = tk.Frame(dlg, bg=M.PANEL2, padx=10, pady=8, highlightbackground=M.RARITY_COLOR.get(gd.rarity, M.MUTED), highlightthickness=1)
            row.pack(fill="x", padx=18, pady=3); head = tk.Frame(row, bg=M.PANEL2); head.pack(fill="x")
            tk.Label(head, text=gd.name, bg=M.PANEL2, fg=M.TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(head, text=gd.rarity.upper(), bg=M.PANEL2, fg=M.RARITY_COLOR.get(gd.rarity, M.MUTED), font=("Segoe UI", 7, "bold")).pack(side="right")
            tk.Label(row, text=g.glyph_description(gid), bg=M.PANEL2, fg=M.MUTED, justify="left", anchor="w", wraplength=500, font=("Segoe UI", 8)).pack(fill="x", pady=(3, 6))
            tk.Button(row, text="REPLACE THIS GLYPH", command=lambda idx=i: choose(idx), bg="#36363d", fg=M.TEXT, activebackground="#42424a", activeforeground=M.TEXT,
                      relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 8, "bold")).pack(fill="x")
        tk.Button(dlg, text="Cancel", command=dlg.destroy, bg=M.PANEL, fg=M.MUTED, activebackground=M.PANEL, activeforeground=M.TEXT, relief="flat", bd=0, highlightthickness=0).pack(pady=8)
        return
    if ok: self.sound.play("select"); self.continue_from_choice()
    else: self.choice_message.config(text=msg, fg=M.BAD)


def patched_show_compendium(self, tab="glyphs"):
    self.screen = "compendium"; self.clear(self.main); self.clear(self.side); self._menu_chrome("Compendium")
    outer = tk.Frame(self.main, bg=M.BG, padx=45, pady=24); outer.pack(fill="both", expand=True)
    top = tk.Frame(outer, bg=M.BG); top.pack(fill="x")
    tk.Label(top, text="COMPENDIUM", bg=M.BG, fg=M.TEXT, font=("Georgia", 26, "bold")).pack(side="left")
    self._menu_button(top, "BACK", self.show_main_menu, width=10).pack(side="right")
    tabs = tk.Frame(outer, bg=M.BG); tabs.pack(fill="x", pady=(14, 8))
    for key, label in (("glyphs", f"GLYPHS ({len(M.GLYPHS)})"), ("axioms", f"AXIOMS ({len(M.AXIOMS)})"), ("bosses", f"BOSSES ({len(M.BOSSES)})")):
        selected = key == tab
        tk.Button(tabs, text=label, command=lambda k=key: self.show_compendium(k), bg=M.ACCENT if selected else M.PANEL2,
                  fg=M.BG if selected else M.TEXT, activebackground=M.ACCENT if selected else "#36363d", activeforeground=M.BG if selected else M.TEXT,
                  relief="flat", bd=0, highlightthickness=0, padx=16, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
    filter_row = tk.Frame(outer, bg=M.BG); filter_row.pack(fill="x", pady=(0, 9))
    tk.Label(filter_row, text="Search", bg=M.BG, fg=M.MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
    search_var = tk.StringVar(); entry = tk.Entry(filter_row, textvariable=search_var, bg=M.PANEL2, fg=M.TEXT, insertbackground=M.TEXT, relief="flat")
    entry.pack(side="left", fill="x", expand=True, ipady=5)
    rarity_var = tk.StringVar(value="All rarities"); sort_var = tk.StringVar(value="Rarity: Common → Rare" if tab == "glyphs" else "Name: A → Z")
    if tab == "glyphs":
        tk.Label(filter_row, text="Rarity", bg=M.BG, fg=M.MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(14, 6))
        rm = tk.OptionMenu(filter_row, rarity_var, "All rarities", "Common", "Uncommon", "Rare")
        rm.config(bg=M.PANEL2, fg=M.TEXT, activebackground=M.PANEL2, activeforeground=M.TEXT, relief="flat", bd=0, highlightthickness=0, width=12); rm["menu"].config(bg=M.PANEL2, fg=M.TEXT); rm.pack(side="left")
    tk.Label(filter_row, text="Sort", bg=M.BG, fg=M.MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(14, 6))
    opts = ("Rarity: Common → Rare", "Rarity: Rare → Common", "Name: A → Z", "Name: Z → A") if tab == "glyphs" else ("Name: A → Z", "Name: Z → A")
    sm = tk.OptionMenu(filter_row, sort_var, *opts); sm.config(bg=M.PANEL2, fg=M.TEXT, activebackground=M.PANEL2, activeforeground=M.TEXT, relief="flat", bd=0, highlightthickness=0, width=20); sm["menu"].config(bg=M.PANEL2, fg=M.TEXT); sm.pack(side="left")
    wrap = tk.Frame(outer, bg=M.BG); wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(wrap, bg=M.BG, highlightthickness=0); scroll = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview); canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True); inner = tk.Frame(canvas, bg=M.BG); win = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))); canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width)); canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
    def render(*_):
        self.clear(inner); q = search_var.get().strip().lower()
        if tab == "glyphs":
            items = list(M.GLYPHS.values()); rf = rarity_var.get()
            if rf != "All rarities": items = [g for g in items if g.rarity == rf]
            mode = sort_var.get()
            if mode == "Rarity: Rare → Common": items.sort(key=lambda g: (-RARITY_ORDER.get(g.rarity, 99), g.name.lower()))
            elif mode == "Name: A → Z": items.sort(key=lambda g: g.name.lower())
            elif mode == "Name: Z → A": items.sort(key=lambda g: g.name.lower(), reverse=True)
            else: items.sort(key=lambda g: (RARITY_ORDER.get(g.rarity, 99), g.name.lower()))
            for g in items:
                if q and q not in f"{g.name} {g.rarity} {g.description}".lower(): continue
                color = M.RARITY_COLOR.get(g.rarity, M.MUTED); card = tk.Frame(inner, bg=M.PANEL, padx=14, pady=10, highlightbackground=color, highlightthickness=1); card.pack(fill="x", pady=4, padx=2)
                line = tk.Frame(card, bg=M.PANEL); line.pack(fill="x"); tk.Label(line, text=g.name, bg=M.PANEL, fg=M.TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
                tk.Label(line, text=g.rarity.upper(), bg=M.PANEL, fg=color, font=("Segoe UI", 8, "bold")).pack(side="right")
                tk.Label(card, text=g.description, bg=M.PANEL, fg=M.MUTED, justify="left", wraplength=900).pack(anchor="w", pady=(4, 0))
        elif tab == "axioms":
            for a in sorted(M.AXIOMS.values(), key=lambda x: x.name.lower(), reverse=sort_var.get() == "Name: Z → A"):
                if q and q not in f"{a.name} {a.description}".lower(): continue
                card = tk.Frame(inner, bg=M.PANEL, padx=14, pady=10, highlightbackground="#6d5934", highlightthickness=1); card.pack(fill="x", pady=4, padx=2)
                tk.Label(card, text=a.name, bg=M.PANEL, fg=M.ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w"); tk.Label(card, text=a.description, bg=M.PANEL, fg=M.MUTED, justify="left", wraplength=900).pack(anchor="w", pady=(4, 0))
        else:
            for b in sorted(M.BOSSES.values(), key=lambda x: x.name.lower(), reverse=sort_var.get() == "Name: Z → A"):
                if q and q not in f"{b.name} {b.description}".lower(): continue
                card = tk.Frame(inner, bg="#2a2022", padx=14, pady=10, highlightbackground="#704045", highlightthickness=1); card.pack(fill="x", pady=4, padx=2)
                tk.Label(card, text=b.name, bg="#2a2022", fg="#efc0c3", font=("Segoe UI", 10, "bold")).pack(anchor="w"); tk.Label(card, text=b.description, bg="#2a2022", fg="#c9aaac", justify="left", wraplength=900).pack(anchor="w", pady=(4, 0))
        canvas.yview_moveto(0)
    search_var.trace_add("write", render); sort_var.trace_add("write", render)
    if tab == "glyphs": rarity_var.trace_add("write", render)
    render(); entry.focus_set()


def patched_build_archetype(self, game):
    return f"{len(game.glyphs)} GLYPHS • {len(game.axioms)} AXIOMS"


def apply_patch(main_module):
    global M, original_init
    M = main_module; cls = main_module.DeadLetterApp; original_init = cls.__init__
    cls.__init__ = patched_init; cls.show_title = patched_show_title; cls.show_start = patched_show_start
    cls._build_side_panel = patched_build_side_panel; cls._refresh_side = patched_refresh_side; cls._draw_hangman = patched_draw_hangman
    cls._render_glyph_offers = patched_render_glyph_offers; cls.take_glyph = patched_take_glyph
    cls.show_compendium = patched_show_compendium; cls._build_archetype = patched_build_archetype
