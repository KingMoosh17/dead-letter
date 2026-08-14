"""Automatic local playtest telemetry for Dead Letter.

No network calls are made. Completed/failed words, upgrade decisions, and major
run events are written to the per-user Dead Letter data folder so playtesting can improve both
word Complexity and roguelike balance without asking the player to manually
rate anything.

v1.1 adds selectable word-bank context while retaining the v0.8 word-model telemetry fields.

v0.8 added:
- the frequency-order ("human-ish") Hangman solver features used by the new
  Complexity model;
- exact manual letter-guess order and wrong-letter order;
- decision telemetry for Glyph/Axiom offers, rerolls, picks, replacements,
  skips, and trashing;
- run-event telemetry for main-run wins and Endless entry/loss.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime

GAME_VERSION = "1.1"
COMPLEXITY_MODEL_VERSION = "structural_frequency_v08"

FIELDS = [
    "timestamp", "game_version", "complexity_model_version",
    "run_id", "seed", "difficulty", "word_bank", "round_index", "chapter", "round_in_chapter",
    "endless", "boss_id", "outcome", "fail_reason", "word", "complexity",
    "raw_complexity", "model_complexity", "v05_complexity",
    "frequency_solver_misses", "frequency_solver_guesses", "frequency_complexity",
    "target", "variance",
    "familiarity_score", "length", "unique_letters", "pos_tags",
    "solver_misses", "solver_guesses", "solver_miss_difficulty",
    "solver_guess_difficulty", "ambiguity_difficulty", "familiarity_difficulty",
    "letter_rarity", "ngram_rarity", "vowel_oddity", "length_difficulty",
    "morphology_difficulty", "repetition_difficulty",
    "initial_time", "remaining_time", "elapsed_time", "time_used_ratio",
    "max_mistakes", "charged_mistakes", "attempted_mistakes",
    "wrong_letter_guesses", "wrong_full_word_guesses", "full_word_attempts",
    "correct_letter_guesses", "total_letter_guesses",
    "letter_guess_sequence", "wrong_letter_sequence",
    "eliminated_letters", "auto_revealed_letters", "solve_method",
    "score_total", "points_at_start", "points_after", "glyph_count",
    "axiom_count", "glyphs", "axioms",
]

DECISION_FIELDS = [
    "timestamp", "game_version", "run_id", "seed", "difficulty", "round_index", "chapter",
    "round_in_chapter", "decision_type", "action",
    "offers_before", "offers_after", "selected_id", "replaced_id",
    "cost", "refund", "points_before", "points_after",
    "glyphs_before", "glyphs_after", "axioms_before", "axioms_after",
]

RUN_EVENT_FIELDS = [
    "timestamp", "game_version", "run_id", "seed", "difficulty", "event",
    "round_index", "chapter", "round_in_chapter", "endless",
    "points", "total_earned", "boss_id", "word", "glyphs", "axioms",
]


def _telemetry_dir(game):
    root = getattr(game, "data_dir", None)
    if root is not None:
        return root / "telemetry"
    return game.bank.path.parent.parent / "telemetry"


def _enabled(game):
    return bool(getattr(game, "telemetry_enabled", True))


def _migrate_if_needed(path):
    """Upgrade older round-telemetry headers in place without discarding playtests."""
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            old_fields = reader.fieldnames or []
            if old_fields == FIELDS:
                return
            rows = list(reader)
        tmp = path.with_suffix(".migrating.csv")
        with tmp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            for old in rows:
                row = {k: old.get(k, "") for k in FIELDS}
                row["game_version"] = old.get("game_version") or "0.4"
                row["complexity_model_version"] = (
                    old.get("complexity_model_version") or "legacy_v0.4"
                )
                writer.writerow(row)
        os.replace(tmp, path)
    except OSError:
        # Telemetry must never break a run.
        return


def _append(path, fields, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def record_round(game, outcome: str, fail_reason: str = ""):
    if not _enabled(game):
        return None
    r = game.round
    if not r or getattr(r, "telemetry_recorded", False):
        return None
    try:
        out_dir = _telemetry_dir(game)
        path = out_dir / "run_telemetry.csv"
        _migrate_if_needed(path)
        initial = max(0.001, float(r.initial_time))
        score_total = int(game.last_result.get("total", 0)) if outcome == "solved" else 0
        w = r.word
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_version": GAME_VERSION,
            "complexity_model_version": COMPLEXITY_MODEL_VERSION,
            "run_id": game.run_id,
            "seed": game.seed,
            "difficulty": getattr(game, "difficulty", "medium"),
            "word_bank": getattr(game, "bank_id", "standard"),
            "round_index": game.round_index,
            "chapter": game.chapter,
            "round_in_chapter": game.round_in_chapter,
            "endless": int(game.endless),
            "boss_id": r.boss_id or "",
            "outcome": outcome,
            "fail_reason": fail_reason,
            "word": w.word,
            "complexity": round(w.complexity, 4),
            "raw_complexity": round(w.raw_complexity, 4),
            "model_complexity": round(getattr(w, "model_complexity", w.complexity), 4),
            "v05_complexity": round(getattr(w, "v05_complexity", w.complexity), 4),
            "frequency_solver_misses": getattr(w, "frequency_solver_misses", ""),
            "frequency_solver_guesses": getattr(w, "frequency_solver_guesses", ""),
            "frequency_complexity": round(getattr(w, "frequency_complexity", w.complexity), 4),
            "target": round(r.target_complexity, 4),
            "variance": round(r.variance, 4),
            "familiarity_score": round(w.familiarity_score, 6),
            "length": w.length,
            "unique_letters": len(set(w.word)),
            "pos_tags": w.pos_tags,
            "solver_misses": getattr(w, "solver_misses", ""),
            "solver_guesses": getattr(w, "solver_guesses", ""),
            "solver_miss_difficulty": round(getattr(w, "solver_miss_difficulty", 0.0), 6),
            "solver_guess_difficulty": round(getattr(w, "solver_guess_difficulty", 0.0), 6),
            "ambiguity_difficulty": round(getattr(w, "ambiguity_difficulty", 0.0), 6),
            "familiarity_difficulty": round(getattr(w, "familiarity_difficulty", 0.0), 6),
            "letter_rarity": round(getattr(w, "letter_rarity", 0.0), 6),
            "ngram_rarity": round(getattr(w, "ngram_rarity", 0.0), 6),
            "vowel_oddity": round(getattr(w, "vowel_oddity", 0.0), 6),
            "length_difficulty": round(getattr(w, "length_difficulty", 0.0), 6),
            "morphology_difficulty": round(getattr(w, "morphology_difficulty", 0.0), 6),
            "repetition_difficulty": round(getattr(w, "repetition_difficulty", 0.0), 6),
            "initial_time": round(r.initial_time, 3),
            "remaining_time": round(r.remaining_time, 3),
            "elapsed_time": round(r.elapsed, 3),
            "time_used_ratio": round(min(1.5, max(0.0, r.elapsed / initial)), 5),
            "max_mistakes": r.max_mistakes,
            "charged_mistakes": r.mistakes,
            "attempted_mistakes": getattr(r, "attempted_mistakes", r.mistakes),
            "wrong_letter_guesses": getattr(r, "wrong_letter_guesses", 0),
            "wrong_full_word_guesses": getattr(r, "wrong_full_word_guesses", 0),
            "full_word_attempts": getattr(r, "full_word_attempts", 0),
            "correct_letter_guesses": r.correct_letter_guesses,
            "total_letter_guesses": r.total_letter_guesses,
            "letter_guess_sequence": "".join(getattr(r, "letter_guess_sequence", [])),
            "wrong_letter_sequence": "".join(getattr(r, "wrong_letter_sequence", [])),
            "eliminated_letters": len(r.eliminated_letters),
            "auto_revealed_letters": getattr(r, "auto_revealed_letters", 0),
            "solve_method": r.solve_method,
            "score_total": score_total,
            "points_at_start": getattr(r, "points_at_start", 0),
            "points_after": game.points,
            "glyph_count": len(game.glyphs),
            "axiom_count": len(game.axioms),
            "glyphs": "|".join(game.glyphs),
            "axioms": "|".join(game.axioms),
        }
        _append(path, FIELDS, row)
        r.telemetry_recorded = True
        return path
    except OSError:
        return None


def record_decision(
    game,
    decision_type: str,
    action: str,
    *,
    offers_before=None,
    offers_after=None,
    selected_id: str = "",
    replaced_id: str = "",
    cost: int = 0,
    refund: int = 0,
    points_before=None,
    glyphs_before=None,
    axioms_before=None,
):
    """Record upgrade-choice behavior for future balance analysis."""
    if not _enabled(game):
        return None
    try:
        path = _telemetry_dir(game) / "decision_telemetry.csv"
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_version": GAME_VERSION,
            "run_id": game.run_id,
            "seed": game.seed,
            "difficulty": getattr(game, "difficulty", "medium"),
            "round_index": game.round_index,
            "chapter": game.chapter,
            "round_in_chapter": game.round_in_chapter,
            "decision_type": decision_type,
            "action": action,
            "offers_before": "|".join(offers_before or []),
            "offers_after": "|".join(offers_after or []),
            "selected_id": selected_id,
            "replaced_id": replaced_id,
            "cost": cost,
            "refund": refund,
            "points_before": game.points if points_before is None else points_before,
            "points_after": game.points,
            "glyphs_before": "|".join(glyphs_before if glyphs_before is not None else game.glyphs),
            "glyphs_after": "|".join(game.glyphs),
            "axioms_before": "|".join(axioms_before if axioms_before is not None else game.axioms),
            "axioms_after": "|".join(game.axioms),
        }
        _append(path, DECISION_FIELDS, row)
        return path
    except OSError:
        return None


def record_run_event(game, event: str):
    if not _enabled(game):
        return None
    try:
        path = _telemetry_dir(game) / "run_events.csv"
        r = game.round
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_version": GAME_VERSION,
            "run_id": game.run_id,
            "seed": game.seed,
            "difficulty": getattr(game, "difficulty", "medium"),
            "event": event,
            "round_index": game.round_index,
            "chapter": game.chapter,
            "round_in_chapter": game.round_in_chapter,
            "endless": int(game.endless),
            "points": game.points,
            "total_earned": game.total_earned,
            "boss_id": (r.boss_id if r else "") or "",
            "word": r.word.word if r else "",
            "glyphs": "|".join(game.glyphs),
            "axioms": "|".join(game.axioms),
        }
        _append(path, RUN_EVENT_FIELDS, row)
        return path
    except OSError:
        return None
