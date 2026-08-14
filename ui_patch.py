"""Dead Letter v1.1.3 presentation/QoL patch.

The large gameplay controller remains in main.py.  Release-facing UI polish lives
here so small interface revisions do not require replacing that entire module.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from content import RARITY_TRASH_VALUE

M = None
RARITY_ORDER = {"Common": 0, "Uncommon": 1, "Rare": 2}
BANK_EXAMPLES = {
    "standard": "ELEPHANT • QUARTZ • RHYTHM",
    "common_tongue": "HOUSE • MARKET • GARDEN",
    "bookish": "ARCHITECTURE • OBSERVATORY • MAGNITUDE",
    "quickfire": "JAZZ • GYM • SAFE",
    "labyrinth": "MYRRH • SYZYGY • QUEUE",
}


def _flat_menu_button(self, parent, text, command, primary=False, state="normal", width=26):
    bg = M.ACCENT if primary else M.PANEL2
    fg = M.BG if primary else M.TEXT
    active = "#e7be72" if primary else "#34343b"
    btn = tk.Button(
        parent, text=text, command=command, state=state,
        bg=bg, fg=fg, activebackground=active, activeforeground=fg,
        disabledforeground="#64646c", relief="flat", bd=0,
        highlightthickness=0, takefocus=0, overrelief="flat",
        padx=18, pady=9, width=width,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2" if state == "normal" else "",
    )
    if state == "normal" and not primary:
        btn.bind("<Enter>", lambda _e, b=btn: b.config(bg="#34343b"))
        btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=M.PANEL2))
    return btn


def _click_label(parent, text, command, selected=False, accent=None, font=("Segoe UI", 9, "bold")):
    """Native Button redraws can flash on Windows; labels give a stable flat selector."""
    accent = accent or M.ACCENT
    bg = accent if selected else M.PANEL2
    fg = M.BG if selected else M.TEXT
    label = tk.Label(parent, text=text, bg=bg, fg=fg, pady=6, font=font, cursor="hand2")
    label.bind("<Button-1>", lambda _e: command())
    return label


def _draw_gallows(canvas, w, h, compact=False):
    canvas.delete("art")
    cx = w * (0.53 if compact else 0.5)
    cy = h * 0.48
    scale = min(w / 430.0, h / 430.0) * (0.82 if compact else 1.0)
    def p(x, y): return cx + x * scale, cy + y * scale
    line = "#777269"; body = "#c1bbb0"
    canvas.create_line(*p(-120, 150), *p(110, 150), fill=line, width=max(3, int(5*scale)), tags="art")
    canvas.create_line(*p(-80, 150), *p(-80, -125), fill=line, width=max(3, int(5*scale)), tags="art")
    canvas.create_line(*p(-82, -125), *p(55, -125), fill=line, width=max(3, int(5*scale)), tags="art")
    canvas.create_line(*p(55, -125), *p(55, -77), fill=line, width=max(2, int(3*scale)), tags="art")
    x1,y1=p(28,-77); x2,y2=p(82,-23)
    canvas.create_oval(x1,y1,x2,y2,outline=body,width=max(2,int(3*scale)),tags="art")
    canvas.create_line(*p(55,-23),*p(55,68),fill=body,width=max(2,int(3*scale)),tags="art")
    canvas.create_line(*p(55,5),*p(15,42),fill=body,width=max(2,int(3*scale)),tags="art")
    canvas.create_line(*p(55,5),*p(95,42),fill=body,width=max(2,int(3*scale)),tags="art")
    canvas.create_line(*p(55,68),*p(22,126),fill=body,width=max(2,int(3*scale)),tags="art")
    canvas.create_line(*p(55,68),*p(88,126),fill=body,width=max(2,int(3*scale)),tags="art")
    x1,y1=p(108,92); x2,y2=p(170,154)
    canvas.create_oval(x1,y1,x2,y2,fill="#6f2c31",outline="#a64a50",width=2,tags="art")
    canvas.create_text(*p(139,123),text="DL",fill="#ead8c1",font=("Georgia",max(9,int(13*scale)),"bold"),tags="art")


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def _remove_text_widgets(root, predicate):
    for widget in list(_walk(root)):
        try:
            text = str(widget.cget("text"))
        except (tk.TclError, AttributeError):
            continue
        if predicate(text):
            widget.destroy()


def patched_init(self, root):
    original_init(self, root)
    # Reduce native focus/default-button redraw artifacts globally.
    self.root.option_add("*Button.highlightThickness", 0)
    self.root.option_add("*Button.borderWidth", 0)
    if getattr(sys, "frozen", False):
        install_dir = Path(sys.executable).resolve().parent
        self.update_manager = M.UpdateManager(install_dir, M.GAME_VERSION)
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
                    self.root.iconbitmap(str(icon)); break
            except tk.TclError:
                pass


def patched_show_title(self):
    self.screen = "title"; self.presentation_paused = True
    self.clear(self.main); self.clear(self.side); self._menu_chrome(f"v{M.GAME_VERSION}")
    canvas = tk.Canvas(self.main, bg=M.BG, highlightthickness=0); canvas.pack(fill="both", expand=True)
    self.title_canvas = canvas
    def redraw(_event=None):
        if self.screen != "title" or not canvas.winfo_exists(): return
        canvas.delete("static"); w=max(900,canvas.winfo_width()); h=max(620,canvas.winfo_height())
        canvas.create_rectangle(42,34,w-42,h-34,outline="#2f2f34",width=1,tags="static")
        canvas.create_line(72,80,w-72,80,fill="#6a5432",width=1,tags="static")
        canvas.create_line(72,h-78,w-72,h-78,fill="#6a5432",width=1,tags="static")
        # Title-screen art is deliberately offset right of the wordmark.
        art = tk.Canvas(canvas, bg=M.BG, highlightthickness=0)
        # Draw directly on the main canvas instead of nesting a window.
        gx=int(w*0.73); gy=int(h*0.30); fg="#746f67"
        canvas.create_line(gx-120,gy+245,gx+95,gy+245,fill=fg,width=5,tags="static")
        canvas.create_line(gx-80,gy+245,gx-80,gy-65,fill=fg,width=5,tags="static")
        canvas.create_line(gx-82,gy-65,gx+55,gy-65,fill=fg,width=5,tags="static")
        canvas.create_line(gx+55,gy-65,gx+55,gy-10,fill=fg,width=3,tags="static")
        canvas.create_oval(gx+25,gy-10,gx+85,gy+50,outline="#b0aaa0",width=3,tags="static")
        canvas.create_line(gx+55,gy+50,gx+55,gy+145,fill="#b0aaa0",width=3,tags="static")
        canvas.create_line(gx+55,gy+80,gx+12,gy+118,fill="#b0aaa0",width=3,tags="static")
        canvas.create_line(gx+55,gy+80,gx+98,gy+118,fill="#b0aaa0",width=3,tags="static")
        canvas.create_line(gx+55,gy+145,gx+20,gy+205,fill="#b0aaa0",width=3,tags="static")
        canvas.create_line(gx+55,gy+145,gx+90,gy+205,fill="#b0aaa0",width=3,tags="static")
        canvas.create_oval(gx+118,gy+176,gx+172,gy+230,fill="#6f2c31",outline="#a64a50",width=2,tags="static")
        canvas.create_text(gx+145,gy+203,text="DL",fill="#e8d8c7",font=("Georgia",12,"bold"),tags="static")
        tx=int(w*0.31)
        canvas.create_text(tx,int(h*0.37),text="DEAD LETTER",fill=M.TEXT,font=("Georgia",48,"bold"),tags="static")
        canvas.create_text(tx,int(h*0.37)+64,text="A  H A N G M A N  R O G U E L I K E",fill=M.ACCENT,font=("Segoe UI",11,"bold"),tags="static")
        canvas.create_text(tx,h-128,text="PRESS ANY KEY",fill=M.ACCENT,font=("Segoe UI",11,"bold"),tags=("static","prompt"))
        canvas.create_text(tx,h-100,text="or click to continue",fill="#6e6b66",font=("Segoe UI",8),tags="static")
    canvas.bind("<Configure>", redraw); canvas.bind("<Button-1>", lambda _e:self.show_main_menu()); redraw()
    def pulse(on=True):
        if self.screen!="title" or not canvas.winfo_exists(): return
        canvas.itemconfigure("prompt",fill=M.ACCENT if on else "#7a6849"); self.root.after(620,lambda:pulse(not on))
    pulse(); self.root.focus_set()


def patched_show_main_menu(self):
    self.screen="menu"; self.presentation_paused=True; self.game=None
    self.clear(self.main); self.clear(self.side); self._menu_chrome(f"v{M.GAME_VERSION}")
    outer=tk.Frame(self.main,bg=M.BG,padx=55,pady=30); outer.pack(fill="both",expand=True)
    left=tk.Frame(outer,bg=M.BG); left.pack(side="left",fill="both",expand=True,padx=(20,45))
    right=tk.Frame(outer,bg=M.BG,width=430); right.pack(side="right",fill="both",expand=False,padx=(0,20)); right.pack_propagate(False)
    tk.Label(left,text="DEAD LETTER",bg=M.BG,fg=M.TEXT,font=("Georgia",38,"bold")).pack(anchor="w",pady=(32,2))
    tk.Label(left,text="A HANGMAN ROGUELIKE",bg=M.BG,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(0,28))
    buttons=tk.Frame(left,bg=M.BG); buttons.pack(anchor="w")
    has_save=self.storage.has_run_save()
    self._menu_button(buttons,"CONTINUE RUN",self.continue_saved_run,primary=has_save,state="normal" if has_save else "disabled").pack(pady=4,anchor="w")
    self._menu_button(buttons,"NEW RUN",self.show_start,primary=not has_save).pack(pady=4,anchor="w")
    self._menu_button(buttons,"HOW TO PLAY",lambda:self.show_tutorial(0)).pack(pady=4,anchor="w")
    self._menu_button(buttons,"STATS",self.show_stats).pack(pady=4,anchor="w")
    self._menu_button(buttons,"COMPENDIUM",lambda:self.show_compendium("glyphs")).pack(pady=4,anchor="w")
    self._menu_button(buttons,"SETTINGS",self.show_settings).pack(pady=4,anchor="w")
    self.update_button_holder=tk.Frame(buttons,bg=M.BG); self.update_button_holder.pack(anchor="w")
    if self.available_update: self._show_update_button()
    self._menu_button(buttons,"QUIT",self.request_quit).pack(pady=(18,4),anchor="w")
    if self.settings.get("check_updates",True) and not self.available_update: self._check_updates_async()
    art=tk.Canvas(right,bg=M.BG,highlightthickness=0)
    art.pack(fill="both",expand=True)
    art.bind("<Configure>",lambda e:_draw_gallows(art,e.width,e.height,compact=True))
    self.sound.play("menu")


def patched_show_start(self):
    self.screen="new_run"; self.presentation_paused=True
    self.clear(self.main); self.clear(self.side); self._menu_chrome("New Run")
    outer=tk.Frame(self.main,bg=M.BG,padx=50,pady=18); outer.pack(fill="both",expand=True)
    top=tk.Frame(outer,bg=M.BG); top.pack(fill="x")
    tk.Label(top,text="NEW RUN",bg=M.BG,fg=M.TEXT,font=("Georgia",28,"bold")).pack(side="left")
    self._menu_button(top,"BACK",self.show_main_menu,width=10).pack(side="right")

    self._start_diff_widgets={}; self._start_bank_widgets={}
    tk.Label(outer,text="DIFFICULTY",bg=M.BG,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(13,6))
    cards=tk.Frame(outer,bg=M.BG); cards.pack(fill="x")
    colors={"easy":M.GOOD,"medium":M.ACCENT,"hard":M.BAD}
    for did in ("easy","medium","hard"):
        d=M.DIFFICULTIES[did]; chosen=did==self.selected_difficulty; color=colors[did]
        f=tk.Frame(cards,bg=M.PANEL,padx=14,pady=9,highlightbackground=color if chosen else "#3b3b42",highlightthickness=2 if chosen else 1)
        f.pack(side="left",fill="x",expand=True,padx=4)
        title=tk.Label(f,text=d.name.upper(),bg=M.PANEL,fg=color,font=("Georgia",14,"bold")); title.pack(anchor="w")
        timing="Standard time" if d.time_delta==0 else f"{d.time_delta:+.0f}s starting time"
        opts=f"{d.glyph_choices} Glyph / {d.axiom_choices} Axiom option{'s' if d.glyph_choices!=1 else ''}"
        tk.Label(f,text=f"{timing}  •  {opts}",bg=M.PANEL,fg=M.MUTED,font=("Segoe UI",9)).pack(anchor="w",pady=(3,7))
        selector=_click_label(f,"SELECTED" if chosen else "SELECT",lambda x=did:self.select_difficulty(x),chosen,color)
        selector.pack(fill="x")
        self._start_diff_widgets[did]=(f,selector,color)

    tk.Label(outer,text="WORD BANK",bg=M.BG,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(16,6))
    bank_area=tk.Frame(outer,bg=M.BG); bank_area.pack(fill="x")
    bank_items=list(M.BANKS.items())
    for row_index,row_items in enumerate((bank_items[:3],bank_items[3:])):
        row=tk.Frame(bank_area,bg=M.BG); row.pack(fill="x",pady=(0,7 if row_index==0 else 0))
        for bid,bdef in row_items:
            chosen=bid==self.selected_bank_id
            f=tk.Frame(row,bg=M.PANEL,padx=14,pady=9,height=126,highlightbackground=M.ACCENT if chosen else "#3b3b42",highlightthickness=2 if chosen else 1)
            f.pack(side="left",fill="x",expand=True,padx=4); f.pack_propagate(False)
            title=tk.Label(f,text=bdef.name.upper(),bg=M.PANEL,fg=M.ACCENT if chosen else M.TEXT,font=("Segoe UI",11,"bold")); title.pack(anchor="w")
            tk.Label(f,text=bdef.description,bg=M.PANEL,fg="#c7c7cd",wraplength=520,justify="left",anchor="nw",font=("Segoe UI",10)).pack(anchor="w",fill="x",pady=(3,1))
            tk.Label(f,text=f"Examples: {BANK_EXAMPLES.get(bid,'')}",bg=M.PANEL,fg=M.ACCENT,wraplength=520,justify="left",font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(0,4))
            selector=_click_label(f,"SELECTED" if chosen else "SELECT",lambda x=bid:self.select_word_bank(x),chosen,M.ACCENT,font=("Segoe UI",8,"bold"))
            selector.pack(side="bottom",fill="x")
            self._start_bank_widgets[bid]=(f,title,selector)

    setup=tk.Frame(outer,bg=M.PANEL,padx=18,pady=12,highlightbackground="#3b3b42",highlightthickness=1)
    setup.pack(fill="x",pady=(15,12))
    inner=tk.Frame(setup,bg=M.PANEL); inner.pack(anchor="center")
    tk.Label(inner,text="Seed (optional)",bg=M.PANEL,fg=M.TEXT,font=("Segoe UI",10,"bold")).pack(side="left",padx=(0,10))
    self.seed_entry=tk.Entry(inner,bg=M.PANEL2,fg=M.TEXT,insertbackground=M.TEXT,relief="flat",width=30,font=("Consolas",10))
    self.seed_entry.pack(side="left",ipady=6,padx=(0,12))
    tk.Label(inner,text="Same setup + seed reproduces the same rolls.",bg=M.PANEL,fg=M.MUTED,font=("Segoe UI",9)).pack(side="left")
    actions=tk.Frame(outer,bg=M.BG); actions.pack(fill="x")
    start=tk.Button(actions,text="START RUN",command=self.new_run,bg=M.ACCENT,fg=M.BG,activebackground="#e7be72",activeforeground=M.BG,
                    relief="flat",bd=0,highlightthickness=0,takefocus=0,padx=32,pady=12,width=26,font=("Segoe UI",13,"bold"),cursor="hand2")
    start.pack(anchor="center")
    self._refresh_start_selection()


def patched_refresh_start_selection(self):
    if getattr(self,"screen","")!="new_run": return
    for did,(frame,label,color) in getattr(self,"_start_diff_widgets",{}).items():
        chosen=did==self.selected_difficulty
        frame.config(highlightbackground=color if chosen else "#3b3b42",highlightthickness=2 if chosen else 1)
        label.config(text="SELECTED" if chosen else "SELECT",bg=color if chosen else M.PANEL2,fg=M.BG if chosen else M.TEXT)
    for bid,(frame,title,label) in getattr(self,"_start_bank_widgets",{}).items():
        chosen=bid==self.selected_bank_id
        frame.config(highlightbackground=M.ACCENT if chosen else "#3b3b42",highlightthickness=2 if chosen else 1)
        title.config(fg=M.ACCENT if chosen else M.TEXT)
        label.config(text="SELECTED" if chosen else "SELECT",bg=M.ACCENT if chosen else M.PANEL2,fg=M.BG if chosen else M.TEXT)


def patched_select_difficulty(self,did):
    if did not in M.DIFFICULTIES: return
    self.selected_difficulty=did; self.sound.play("select")
    if getattr(self,"screen","")=="new_run" and hasattr(self,"_refresh_start_selection"): self._refresh_start_selection()
    else: self.show_start()


def patched_select_word_bank(self,bid):
    if bid not in M.BANKS: return
    self.selected_bank_id=bid; self.sound.play("select")
    if getattr(self,"screen","")=="new_run" and hasattr(self,"_refresh_start_selection"): self._refresh_start_selection()
    else: self.show_start()


def patched_chapter_progress(self,parent,solved_current=False):
    if not self.game: return None
    g=self.game; current=g.round_in_chapter; boss=M.BOSSES[g.current_boss_id]
    wrap=tk.Frame(parent,bg=M.BG); wrap.pack(fill="x",pady=(0,9))
    chapter_text=f"CHAPTER {g.chapter}"+(" • ENDLESS" if g.endless or g.chapter>8 else f" / {g.CHAPTERS}")
    tk.Label(wrap,text=chapter_text,bg=M.BG,fg=M.TEXT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(0,5))
    row=tk.Frame(wrap,bg=M.BG); row.pack(fill="x")
    for idx in range(1,5):
        label=f"WORD {idx}" if idx<4 else f"BOSS\n{boss.name.upper()}"
        completed=idx<current or (solved_current and idx==current)
        active=idx==current and not solved_current
        if completed: bg,fg,border,prefix="#25372a",M.GOOD,"#3e7050","✓  "
        elif active and idx==4: bg,fg,border,prefix="#412426","#f1caca",M.BAD,"▶  "
        elif active: bg,fg,border,prefix="#393224",M.ACCENT,"#6d5934","▶  "
        else: bg,fg,border,prefix=M.PANEL,M.MUTED,"#34343a",""
        cell=tk.Frame(row,bg=bg,padx=8,pady=6,highlightbackground=border,highlightthickness=1)
        cell.pack(side="left",fill="x",expand=True,padx=(0 if idx==1 else 3,0))
        tk.Label(cell,text=prefix+label,bg=bg,fg=fg,justify="center",font=("Segoe UI",8,"bold")).pack(expand=True)
    return wrap


def patched_boss_banner(self,parent,boss_id,mode="upcoming"):
    # Reward screens no longer repeat a Boss preview immediately before the
    # dedicated Boss-approach screen. During actual words, preview stays useful.
    if getattr(self,"screen","")=="glyph_choice" and mode=="upcoming": return None
    return original_boss_banner(self,parent,boss_id,mode)


def patched_boss_next_callout(self,parent):
    return None


def patched_show_glyph_choice(self):
    original_show_glyph_choice(self)
    _remove_text_widgets(self.main,lambda t:t=="BOSS IS NEXT" or ("option" in t.lower() and "offered on" in t.lower()))


def patched_show_axiom_choice(self):
    original_show_axiom_choice(self)
    for widget in _walk(self.main):
        try: text=str(widget.cget("text"))
        except (tk.TclError,AttributeError): continue
        if text.startswith("Permanent run rules"):
            widget.config(text="Permanent run rules")


def patched_show_boss_intro(self):
    original_show_boss_intro(self)
    _remove_text_widgets(self.main,lambda t:"timer is paused until you enter" in t.lower())


def patched_game_glyph_description(game,gid):
    text=original_game_glyph_description(game,gid)
    if game.has_axiom("recycling"):
        value=RARITY_TRASH_VALUE.get(M.GLYPHS[gid].rarity,0)
        if value and "Sell value:" not in text:
            text=f"{text}  Sell value: {value} Points."
    return text


def patched_build_side_panel(self):
    self.points_label=tk.Label(self.side,text="",bg=M.PANEL,fg=M.ACCENT,font=("Georgia",19,"bold")); self.points_label.pack(anchor="w")
    self.total_label=tk.Label(self.side,text="",bg=M.PANEL,fg=M.MUTED); self.total_label.pack(anchor="w",pady=(0,8))
    self.hangman=tk.Canvas(self.side,height=295,bg=M.PANEL,highlightthickness=2,highlightbackground="#34343a"); self.hangman.pack(fill="x",pady=(3,8))
    inventory_wrap=tk.Frame(self.side,bg=M.PANEL); inventory_wrap.pack(fill="both",expand=True,pady=(2,0))
    self.inventory_canvas=tk.Canvas(inventory_wrap,bg=M.PANEL,highlightthickness=0,bd=0)
    self.inventory_scroll=tk.Scrollbar(inventory_wrap,orient="vertical",command=self.inventory_canvas.yview)
    self.inventory_canvas.configure(yscrollcommand=self.inventory_scroll.set); self.inventory_scroll.pack(side="right",fill="y"); self.inventory_canvas.pack(side="left",fill="both",expand=True)
    self.inventory_inner=tk.Frame(self.inventory_canvas,bg=M.PANEL); self.inventory_window=self.inventory_canvas.create_window((0,0),window=self.inventory_inner,anchor="nw")
    self.inventory_inner.bind("<Configure>",self._sync_inventory_scrollregion); self.inventory_canvas.bind("<Configure>",self._sync_inventory_width)
    self.inventory_canvas.bind("<Enter>",self._bind_inventory_wheel); self.inventory_canvas.bind("<Leave>",self._unbind_inventory_wheel)
    tk.Label(self.inventory_inner,text="GLYPHS",bg=M.PANEL,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(3,5))
    self.glyph_frame=tk.Frame(self.inventory_inner,bg=M.PANEL); self.glyph_frame.pack(fill="x")
    tk.Label(self.inventory_inner,text="AXIOMS",bg=M.PANEL,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(13,5))
    self.axiom_frame=tk.Frame(self.inventory_inner,bg=M.PANEL); self.axiom_frame.pack(fill="x")
    self._side_inventory_signature=None; self._refresh_side()


def patched_refresh_side(self):
    if not self.game: return
    g=self.game
    if hasattr(self,"points_label"):
        self.points_label.config(text=f"{g.points:,} Points"); mode=" • Endless" if g.endless else ""; self.total_label.config(text=f"{g.total_earned:,} total earned{mode}")
    if not hasattr(self,"glyph_frame") or not hasattr(self,"axiom_frame"): return
    state_sig=tuple(sorted((k,str(v)) for k,v in g.glyph_state.items())); signature=(tuple(g.glyphs),tuple(g.axioms),g.glyph_slots(),state_sig,g.has_axiom("recycling"))
    if signature==self._side_inventory_signature: return
    self._side_inventory_signature=signature; old_y=self.inventory_canvas.yview()[0] if hasattr(self,"inventory_canvas") else 0.0
    self.clear(self.glyph_frame)
    for i in range(g.glyph_slots()):
        occupied=i<len(g.glyphs); card_bg=M.PANEL2 if occupied else M.PANEL; border="#44444b" if occupied else "#303035"
        row=tk.Frame(self.glyph_frame,bg=card_bg,padx=8,pady=7,highlightbackground=border,highlightthickness=1); row.pack(fill="x",pady=3)
        if occupied:
            gid=g.glyphs[i]; gd=M.GLYPHS[gid]; top=tk.Frame(row,bg=card_bg); top.pack(fill="x")
            tk.Label(top,text=f"{i+1}. {gd.name}",bg=card_bg,fg=M.TEXT,font=("Segoe UI",9,"bold"),anchor="w").pack(side="left",fill="x",expand=True)
            tk.Label(top,text=gd.rarity.upper(),bg=card_bg,fg=M.RARITY_COLOR.get(gd.rarity,M.MUTED),font=("Segoe UI",7,"bold")).pack(side="left",padx=(4,3))
            tk.Button(top,text="×",command=lambda idx=i:self.trash_glyph(idx),bg=card_bg,fg=M.BAD,activebackground=card_bg,activeforeground=M.BAD,relief="flat",width=2,bd=0,highlightthickness=0,takefocus=0).pack(side="right")
            tk.Label(row,text=g.glyph_description(gid),bg=card_bg,fg=M.MUTED,justify="left",anchor="w",wraplength=298,font=("Segoe UI",8)).pack(fill="x",pady=(3,0))
        else:
            tk.Label(row,text=f"{i+1}. — empty —",bg=card_bg,fg="#6f6f76",anchor="w",font=("Segoe UI",9)).pack(fill="x")
    self.clear(self.axiom_frame)
    if g.axioms:
        for aid in g.axioms:
            a=M.AXIOMS[aid]; card=tk.Frame(self.axiom_frame,bg="#27272c",padx=8,pady=7,highlightbackground="#4c463a",highlightthickness=1); card.pack(fill="x",pady=3)
            tk.Label(card,text=a.name,bg="#27272c",fg=M.ACCENT,font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x")
            tk.Label(card,text=a.description,bg="#27272c",fg=M.MUTED,justify="left",anchor="w",wraplength=298,font=("Segoe UI",8)).pack(fill="x",pady=(3,0))
    else: tk.Label(self.axiom_frame,text="None yet",bg=M.PANEL,fg=M.MUTED,anchor="w").pack(fill="x",pady=(0,4))
    self.inventory_inner.update_idletasks(); self._sync_inventory_scrollregion(); self.inventory_canvas.yview_moveto(old_y)


def patched_draw_hangman(self):
    if not hasattr(self,"hangman") or not self.game or not self.game.round: return
    c=self.hangman; c.delete("all"); r=self.game.round; remaining=max(0,r.max_mistakes-r.mistakes); danger=remaining==1
    pulse=True if self.settings.get("reduced_motion",False) else int(M.time.perf_counter()*4)%2==0; fg=M.BAD if danger and pulse else "#aaa69b"
    c.configure(highlightbackground=M.BAD if danger and pulse else "#34343a",bg="#2d2022" if danger and pulse else M.PANEL)
    bonus=max(0,r.max_mistakes-6); figure_mistakes=max(0,r.mistakes-bonus) if r.max_mistakes>=6 else r.mistakes
    c.create_line(25,218,255,218,fill=fg,width=4); c.create_line(58,218,58,24,fill=fg,width=4); c.create_line(56,24,205,24,fill=fg,width=4); c.create_line(205,24,205,49,fill=fg,width=3)
    if figure_mistakes>=1:c.create_oval(181,49,229,97,outline=M.TEXT,width=3)
    if figure_mistakes>=2:c.create_line(205,97,205,159,fill=M.TEXT,width=3)
    if figure_mistakes>=3:c.create_line(205,112,171,139,fill=M.TEXT,width=3)
    if figure_mistakes>=4:c.create_line(205,112,239,139,fill=M.TEXT,width=3)
    if figure_mistakes>=5:c.create_line(205,159,178,199,fill=M.TEXT,width=3)
    if figure_mistakes>=6:c.create_line(205,159,232,199,fill=M.TEXT,width=3)
    if r.mistakes>=r.max_mistakes and figure_mistakes>=1:
        c.create_line(192,67,199,74,fill=M.BAD,width=3); c.create_line(199,67,192,74,fill=M.BAD,width=3); c.create_line(211,67,218,74,fill=M.BAD,width=3); c.create_line(218,67,211,74,fill=M.BAD,width=3)
    c.create_text(18,235,text="MISTAKE CAPACITY",fill=M.MUTED,anchor="w",font=("Segoe UI",8,"bold"))
    count=max(1,r.max_mistakes); types=(["bonus"]*bonus)+(["base"]*max(0,count-bonus)); gap=min(24,max(15,int(275/max(1,count)))); x0=18
    for i,kind in enumerate(types):
        x=x0+i*gap; used=i<r.mistakes; final=danger and i==r.mistakes; is_bonus=kind=="bonus"
        outline=M.BAD if final and pulse else (M.ACCENT if is_bonus else "#77746d"); fill=M.BAD if used else ("#5a2529" if final and pulse else ("#4a3d24" if is_bonus else M.PANEL2))
        c.create_oval(x,247,x+15,262,outline=outline,fill=fill,width=3 if final else (2 if is_bonus else 1))
        if final:c.create_text(x+7.5,254.5,text="!",fill=M.TEXT if pulse else M.BAD,font=("Segoe UI",8,"bold"))
        elif is_bonus and not used:c.create_text(x+7.5,254.5,text="+",fill=M.ACCENT,font=("Segoe UI",8,"bold"))
    if danger:c.create_text(18,282,text="⚠ ONE MISTAKE LEFT — NEXT ONE ENDS THE RUN",fill=M.BAD if pulse else "#e6b3b3",anchor="w",font=("Segoe UI",8,"bold"))
    elif bonus:
        unused=max(0,bonus-min(r.mistakes,bonus)); c.create_text(18,282,text=f"{unused} bonus mistake{'s' if unused!=1 else ''} before the Hangman starts drawing",fill=M.ACCENT,anchor="w",font=("Segoe UI",8,"bold"))
    elif r.max_mistakes<6:c.create_text(18,282,text=f"Reduced to {r.max_mistakes} mistakes this word",fill=M.BAD,anchor="w",font=("Segoe UI",8,"bold"))
    else:c.create_text(18,282,text="Standard six-part Hangman",fill="#77777e",anchor="w",font=("Segoe UI",8))


def patched_render_glyph_offers(self):
    self.clear(self.offer_frame); count=max(1,len(self.game.glyph_offers)); wrap={1:430,2:300,3:215}.get(count,165)
    for i,gid in enumerate(self.game.glyph_offers):
        gd=M.GLYPHS[gid]; color=M.RARITY_COLOR.get(gd.rarity,M.MUTED); card=tk.Frame(self.offer_frame,bg=M.PANEL,padx=11,pady=11,highlightbackground=color,highlightthickness=2 if gd.rarity=="Rare" else 1)
        card.pack(side="left",fill="both",expand=True,padx=4)
        tk.Label(card,text=gd.name,bg=M.PANEL,fg=M.TEXT,font=("Segoe UI",10,"bold")).pack(anchor="w")
        tk.Label(card,text=gd.rarity.upper(),bg=M.PANEL,fg=color,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(1,5))
        tk.Label(card,text=self.game.glyph_description(gid),bg=M.PANEL,fg=M.MUTED,justify="left",wraplength=wrap,font=("Segoe UI",8)).pack(anchor="w",fill="x",expand=True)
        tk.Button(card,text="TAKE",command=lambda idx=i:self.take_glyph(idx),bg=M.ACCENT,fg=M.BG,activebackground="#e7be72",activeforeground=M.BG,relief="flat",bd=0,highlightthickness=0,takefocus=0,pady=5,font=("Segoe UI",9,"bold")).pack(fill="x",pady=(8,0))


def patched_take_glyph(self,offer_idx):
    g=self.game
    if len(g.glyphs)<g.glyph_slots(): ok,msg=g.take_glyph(offer_idx)
    else:
        dlg=tk.Toplevel(self.root); dlg.title("Replace Glyph"); dlg.configure(bg=M.PANEL); dlg.transient(self.root); dlg.grab_set(); dlg.geometry("600x590")
        incoming_id=g.glyph_offers[offer_idx]; incoming=M.GLYPHS[incoming_id]; color=M.RARITY_COLOR.get(incoming.rarity,M.MUTED)
        tk.Label(dlg,text=f"Replace a Glyph with {incoming.name}",bg=M.PANEL,fg=M.TEXT,font=("Segoe UI",11,"bold")).pack(pady=(12,2)); tk.Label(dlg,text=incoming.rarity.upper(),bg=M.PANEL,fg=color,font=("Segoe UI",8,"bold")).pack()
        tk.Label(dlg,text=g.glyph_description(incoming_id),bg=M.PANEL,fg=M.MUTED,justify="left",wraplength=540).pack(padx=20,pady=(4,10))
        def choose(idx): g.take_glyph(offer_idx,idx); self.sound.play("select"); dlg.destroy(); self.continue_from_choice()
        for i,gid in enumerate(g.glyphs):
            gd=M.GLYPHS[gid]; row=tk.Frame(dlg,bg=M.PANEL2,padx=10,pady=8,highlightbackground=M.RARITY_COLOR.get(gd.rarity,M.MUTED),highlightthickness=1); row.pack(fill="x",padx=18,pady=3)
            head=tk.Frame(row,bg=M.PANEL2); head.pack(fill="x"); tk.Label(head,text=gd.name,bg=M.PANEL2,fg=M.TEXT,font=("Segoe UI",9,"bold")).pack(side="left"); tk.Label(head,text=gd.rarity.upper(),bg=M.PANEL2,fg=M.RARITY_COLOR.get(gd.rarity,M.MUTED),font=("Segoe UI",7,"bold")).pack(side="right")
            tk.Label(row,text=g.glyph_description(gid),bg=M.PANEL2,fg=M.MUTED,justify="left",anchor="w",wraplength=500,font=("Segoe UI",8)).pack(fill="x",pady=(3,6))
            tk.Button(row,text="REPLACE THIS GLYPH",command=lambda idx=i:choose(idx),bg="#36363d",fg=M.TEXT,activebackground="#42424a",activeforeground=M.TEXT,relief="flat",bd=0,highlightthickness=0,takefocus=0,font=("Segoe UI",8,"bold")).pack(fill="x")
        tk.Button(dlg,text="Cancel",command=dlg.destroy,bg=M.PANEL,fg=M.MUTED,activebackground=M.PANEL,activeforeground=M.TEXT,relief="flat",bd=0,highlightthickness=0,takefocus=0).pack(pady=8); return
    if ok:self.sound.play("select"); self.continue_from_choice()
    else:self.choice_message.config(text=msg,fg=M.BAD)


def patched_show_compendium(self,tab="glyphs"):
    self.screen="compendium"; self.clear(self.main); self.clear(self.side); self._menu_chrome("Compendium")
    outer=tk.Frame(self.main,bg=M.BG,padx=45,pady=24); outer.pack(fill="both",expand=True)
    top=tk.Frame(outer,bg=M.BG); top.pack(fill="x"); tk.Label(top,text="COMPENDIUM",bg=M.BG,fg=M.TEXT,font=("Georgia",26,"bold")).pack(side="left"); self._menu_button(top,"BACK",self.show_main_menu,width=10).pack(side="right")
    tabs=tk.Frame(outer,bg=M.BG); tabs.pack(fill="x",pady=(14,8))
    for key,label in (("glyphs",f"GLYPHS ({len(M.GLYPHS)})"),("axioms",f"AXIOMS ({len(M.AXIOMS)})"),("bosses",f"BOSSES ({len(M.BOSSES)})")):
        selected=key==tab; control=_click_label(tabs,label,lambda k=key:self.show_compendium(k),selected,M.ACCENT); control.config(padx=16); control.pack(side="left",padx=(0,6))
    counts={r:sum(1 for g in M.GLYPHS.values() if g.rarity==r) for r in ("Common","Uncommon","Rare")}
    if tab=="glyphs":
        tk.Label(outer,text=f"COMMON {counts['Common']}   •   UNCOMMON {counts['Uncommon']}   •   RARE {counts['Rare']}",bg=M.BG,fg=M.MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(0,7))
    filter_row=tk.Frame(outer,bg=M.BG); filter_row.pack(fill="x",pady=(0,7)); tk.Label(filter_row,text="Search",bg=M.BG,fg=M.MUTED,font=("Segoe UI",9,"bold")).pack(side="left",padx=(0,6))
    search_var=tk.StringVar(); entry=tk.Entry(filter_row,textvariable=search_var,bg=M.PANEL2,fg=M.TEXT,insertbackground=M.TEXT,relief="flat"); entry.pack(side="left",fill="x",expand=True,ipady=5)
    rarity_var=tk.StringVar(value="All rarities"); sort_var=tk.StringVar(value="Rarity: Common → Rare" if tab=="glyphs" else "Name: A → Z")
    if tab=="glyphs":
        tk.Label(filter_row,text="Rarity",bg=M.BG,fg=M.MUTED,font=("Segoe UI",9,"bold")).pack(side="left",padx=(14,6)); rm=tk.OptionMenu(filter_row,rarity_var,"All rarities","Common","Uncommon","Rare"); rm.config(bg=M.PANEL2,fg=M.TEXT,activebackground=M.PANEL2,activeforeground=M.TEXT,relief="flat",bd=0,highlightthickness=0,width=12); rm["menu"].config(bg=M.PANEL2,fg=M.TEXT); rm.pack(side="left")
    tk.Label(filter_row,text="Sort",bg=M.BG,fg=M.MUTED,font=("Segoe UI",9,"bold")).pack(side="left",padx=(14,6)); opts=("Rarity: Common → Rare","Rarity: Rare → Common","Name: A → Z","Name: Z → A") if tab=="glyphs" else ("Name: A → Z","Name: Z → A"); sm=tk.OptionMenu(filter_row,sort_var,*opts); sm.config(bg=M.PANEL2,fg=M.TEXT,activebackground=M.PANEL2,activeforeground=M.TEXT,relief="flat",bd=0,highlightthickness=0,width=20); sm["menu"].config(bg=M.PANEL2,fg=M.TEXT); sm.pack(side="left")
    result_label=tk.Label(outer,text="",bg=M.BG,fg=M.ACCENT,font=("Segoe UI",8,"bold")); result_label.pack(anchor="w",pady=(0,5))
    wrap=tk.Frame(outer,bg=M.BG); wrap.pack(fill="both",expand=True); canvas=tk.Canvas(wrap,bg=M.BG,highlightthickness=0); scroll=tk.Scrollbar(wrap,orient="vertical",command=canvas.yview); canvas.configure(yscrollcommand=scroll.set); scroll.pack(side="right",fill="y"); canvas.pack(side="left",fill="both",expand=True); inner=tk.Frame(canvas,bg=M.BG); win=canvas.create_window((0,0),window=inner,anchor="nw")
    inner.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all"))); canvas.bind("<Configure>",lambda e:canvas.itemconfigure(win,width=e.width)); canvas.bind("<MouseWheel>",lambda e:canvas.yview_scroll(int(-e.delta/120),"units"))
    def render(*_):
        self.clear(inner); q=search_var.get().strip().lower(); shown=0
        if tab=="glyphs":
            items=list(M.GLYPHS.values()); rf=rarity_var.get()
            if rf!="All rarities": items=[g for g in items if g.rarity==rf]
            mode=sort_var.get()
            if mode=="Rarity: Rare → Common":items.sort(key=lambda g:(-RARITY_ORDER.get(g.rarity,99),g.name.lower()))
            elif mode=="Name: A → Z":items.sort(key=lambda g:g.name.lower())
            elif mode=="Name: Z → A":items.sort(key=lambda g:g.name.lower(),reverse=True)
            else:items.sort(key=lambda g:(RARITY_ORDER.get(g.rarity,99),g.name.lower()))
            for g in items:
                if q and q not in f"{g.name} {g.rarity} {g.description}".lower():continue
                shown+=1; color=M.RARITY_COLOR.get(g.rarity,M.MUTED); card=tk.Frame(inner,bg=M.PANEL,padx=14,pady=10,highlightbackground=color,highlightthickness=1); card.pack(fill="x",pady=4,padx=2); line=tk.Frame(card,bg=M.PANEL); line.pack(fill="x"); tk.Label(line,text=g.name,bg=M.PANEL,fg=M.TEXT,font=("Segoe UI",10,"bold")).pack(side="left"); tk.Label(line,text=g.rarity.upper(),bg=M.PANEL,fg=color,font=("Segoe UI",8,"bold")).pack(side="right"); tk.Label(card,text=g.description,bg=M.PANEL,fg=M.MUTED,justify="left",wraplength=900).pack(anchor="w",pady=(4,0))
            scope=rf if rf!="All rarities" else "Glyphs"; result_label.config(text=f"Showing {shown} {scope}" if scope=="Glyphs" else f"Showing {shown} {scope} Glyph{'s' if shown!=1 else ''}")
        elif tab=="axioms":
            for a in sorted(M.AXIOMS.values(),key=lambda x:x.name.lower(),reverse=sort_var.get()=="Name: Z → A"):
                if q and q not in f"{a.name} {a.description}".lower():continue
                shown+=1; card=tk.Frame(inner,bg=M.PANEL,padx=14,pady=10,highlightbackground="#6d5934",highlightthickness=1); card.pack(fill="x",pady=4,padx=2); tk.Label(card,text=a.name,bg=M.PANEL,fg=M.ACCENT,font=("Segoe UI",10,"bold")).pack(anchor="w"); tk.Label(card,text=a.description,bg=M.PANEL,fg=M.MUTED,justify="left",wraplength=900).pack(anchor="w",pady=(4,0))
            result_label.config(text=f"Showing {shown} Axiom{'s' if shown!=1 else ''}")
        else:
            for b in sorted(M.BOSSES.values(),key=lambda x:x.name.lower(),reverse=sort_var.get()=="Name: Z → A"):
                if q and q not in f"{b.name} {b.description}".lower():continue
                shown+=1; card=tk.Frame(inner,bg="#2a2022",padx=14,pady=10,highlightbackground="#704045",highlightthickness=1); card.pack(fill="x",pady=4,padx=2); tk.Label(card,text=b.name,bg="#2a2022",fg="#efc0c3",font=("Segoe UI",10,"bold")).pack(anchor="w"); tk.Label(card,text=b.description,bg="#2a2022",fg="#c9aaac",justify="left",wraplength=900).pack(anchor="w",pady=(4,0))
            result_label.config(text=f"Showing {shown} Boss{'es' if shown!=1 else ''}")
        canvas.yview_moveto(0)
    search_var.trace_add("write",render); sort_var.trace_add("write",render)
    if tab=="glyphs":rarity_var.trace_add("write",render)
    render(); entry.focus_set()


def patched_build_archetype(self,game):
    return f"{len(game.glyphs)} GLYPHS • {len(game.axioms)} AXIOMS"


def apply_patch(main_module):
    global M,original_init,original_boss_banner,original_show_glyph_choice,original_show_axiom_choice,original_show_boss_intro,original_game_glyph_description
    M=main_module; cls=main_module.DeadLetterApp
    original_init=cls.__init__; original_boss_banner=cls._boss_banner; original_show_glyph_choice=cls.show_glyph_choice; original_show_axiom_choice=cls.show_axiom_choice; original_show_boss_intro=cls.show_boss_intro
    original_game_glyph_description=main_module.GameState.glyph_description
    cls.__init__=patched_init; cls._menu_button=_flat_menu_button
    cls.show_title=patched_show_title; cls.show_main_menu=patched_show_main_menu; cls.show_start=patched_show_start
    cls._refresh_start_selection=patched_refresh_start_selection; cls.select_difficulty=patched_select_difficulty; cls.select_word_bank=patched_select_word_bank
    cls._chapter_progress=patched_chapter_progress; cls._boss_banner=patched_boss_banner; cls._boss_next_callout=patched_boss_next_callout
    cls.show_glyph_choice=patched_show_glyph_choice; cls.show_axiom_choice=patched_show_axiom_choice; cls.show_boss_intro=patched_show_boss_intro
    cls._build_side_panel=patched_build_side_panel; cls._refresh_side=patched_refresh_side; cls._draw_hangman=patched_draw_hangman
    cls._render_glyph_offers=patched_render_glyph_offers; cls.take_glyph=patched_take_glyph; cls.show_compendium=patched_show_compendium; cls._build_archetype=patched_build_archetype
    main_module.GameState.glyph_description=patched_game_glyph_description
