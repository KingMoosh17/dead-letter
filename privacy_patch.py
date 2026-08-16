"""Consent UI and non-blocking online telemetry hooks for Dead Letter."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import online_telemetry
import telemetry

M = None


def _save_remote_setting(app, enabled: bool) -> None:
    app.settings["remote_telemetry_enabled"] = bool(enabled)
    app.settings["telemetry_consent_version"] = online_telemetry.CONSENT_VERSION
    app.storage.save_settings()
    if enabled:
        online_telemetry.start_flush(app.storage.root)
    else:
        online_telemetry.discard_queue(app.storage.root)


def _ask_consent(app) -> None:
    if int(app.settings.get("telemetry_consent_version", 0)) == online_telemetry.CONSENT_VERSION:
        return
    enabled = messagebox.askyesno(
        "Help improve Dead Letter?",
        "Share anonymous gameplay data to help improve word difficulty and game balance?\n\n"
        "If enabled, Dead Letter may send run results, word performance, Boss outcomes, "
        "Glyph/Axiom offers and choices, rerolls, score, difficulty, and word-bank information.\n\n"
        "It does not send your name, email, account information, files, or a persistent player/device ID. "
        "Events are linked only within an individual run.\n\n"
        "You can change this later in Settings.",
    )
    _save_remote_setting(app, enabled)


def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    if bool(self.settings.get("remote_telemetry_enabled", False)):
        online_telemetry.start_flush(self.storage.root)


def patched_show_main_menu(self):
    result = original_show_main_menu(self)
    if int(self.settings.get("telemetry_consent_version", 0)) != online_telemetry.CONSENT_VERSION:
        self.root.after(100, lambda: _ask_consent(self))
    return result


def patched_show_settings(self):
    result = original_show_settings(self)
    try:
        outer = self.main.winfo_children()[-1]
        share = tk.BooleanVar(value=bool(self.settings.get("remote_telemetry_enabled", False)))
        card = tk.Frame(
            outer,
            bg=M.PANEL,
            padx=18,
            pady=14,
            highlightbackground="#3b3b42",
            highlightthickness=1,
        )
        card.pack(fill="x", pady=(16, 0))
        tk.Label(
            card,
            text="ANONYMOUS PLAYTEST SHARING",
            bg=M.PANEL,
            fg=M.TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        def changed():
            _save_remote_setting(self, bool(share.get()))

        tk.Checkbutton(
            card,
            text="Share anonymous gameplay balance data with the developer",
            variable=share,
            command=changed,
            bg=M.PANEL,
            fg=M.MUTED,
            selectcolor=M.PANEL2,
            activebackground=M.PANEL,
            activeforeground=M.TEXT,
        ).pack(anchor="w", pady=(7, 2))
        tk.Label(
            card,
            text=(
                "Sends run-scoped gameplay telemetry only. No name, email, account, or persistent device/player ID. "
                "Requires Local play telemetry above to be enabled. Turning sharing off also deletes any unsent upload queue."
            ),
            bg=M.PANEL,
            fg="#77777e",
            font=("Segoe UI", 8),
            wraplength=760,
            justify="left",
        ).pack(anchor="w")
    except (tk.TclError, IndexError):
        pass
    return result


def _wrap_record(original, event_type: str):
    def wrapped(game, *args, **kwargs):
        path = original(game, *args, **kwargs)
        if path is not None:
            online_telemetry.enqueue_csv_event(
                getattr(game, "data_dir", None), event_type, path
            )
        return path
    return wrapped


def apply_patch(main_module):
    global M
    global original_init, original_show_main_menu, original_show_settings
    M = main_module

    original_init = main_module.DeadLetterApp.__init__
    original_show_main_menu = main_module.DeadLetterApp.show_main_menu
    original_show_settings = main_module.DeadLetterApp.show_settings

    main_module.DeadLetterApp.__init__ = patched_init
    main_module.DeadLetterApp.show_main_menu = patched_show_main_menu
    main_module.DeadLetterApp.show_settings = patched_show_settings

    telemetry.record_round = _wrap_record(telemetry.record_round, "round")
    telemetry.record_decision = _wrap_record(telemetry.record_decision, "decision")
    telemetry.record_run_event = _wrap_record(telemetry.record_run_event, "run_event")
