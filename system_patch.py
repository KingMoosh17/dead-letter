"""Dead Letter v1.1.12 systemic balance and Endless-selection fixes.

Telemetry from a deep Standard Endless run exposed two interaction-level issues:
very high Complexity bands collapsed toward compact words, and stacked automatic
absent-letter cross-outs could remove essentially every wrong letter.  This patch
addresses those systems without flattening individual word Complexity scores.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import math
import tkinter as tk

import effects
from content import GLYPHS, GlyphDef
from game_logic import GameState
from wordbank import BANKS, WordBank

M = None

# Automatic Glyph/Axiom cross-outs can provide enormous information, but they
# should never turn every remaining enabled key into a guaranteed hit. Manual
# wrong guesses may still account for letters below this floor because the
# player paid a mistake for that information.
AUTOMATIC_ABSENT_FLOOR = 8

# Endless length-bucket identities. Complexity filtering still happens first;
# these weights only stop candidate-count imbalance inside a valid band from
# making one word length dominate an entire deep run. Quickfire intentionally
# keeps the legacy compact selection behavior.
ENDLESS_BUCKET_WEIGHTS = {
    "standard": {"short": 0.30, "medium": 0.45, "long": 0.25},
    "common_tongue": {"short": 0.25, "medium": 0.55, "long": 0.20},
    "bookish": {"short": 0.08, "medium": 0.42, "long": 0.50},
    "labyrinth": {"short": 0.35, "medium": 0.40, "long": 0.25},
}


def _bucket(length: int) -> str:
    if length <= 5:
        return "short"
    if length <= 8:
        return "medium"
    return "long"


def _replace_definitions() -> None:
    old = GLYPHS["precision"]
    GLYPHS["precision"] = GlyphDef(
        old.id,
        old.name,
        old.rarity,
        "Every 3 consecutive manual correct letter guesses earn +350 Points and restore 3 seconds.",
        old.category,
    )


@contextmanager
def _hide_precision(game: GameState):
    old = game.glyphs
    try:
        game.glyphs = [gid for gid in old if gid != "precision"]
        yield
    finally:
        game.glyphs = old


def capped_eliminate(game, count: int, candidates=None) -> list[str]:
    """Cross out absent letters while preserving the automatic-info floor."""
    r = getattr(game, "round", None)
    if r is None or count <= 0:
        return []

    remaining_absent = set(effects.ALPHABET) - set(r.word.word) - r.guessed_letters - r.eliminated_letters
    room = max(0, len(remaining_absent) - AUTOMATIC_ABSENT_FLOOR)
    if room <= 0:
        r.information_saturated = True
        return []

    if candidates is None:
        eligible = list(remaining_absent)
    else:
        eligible = list(set(candidates) & remaining_absent)
    game.rng.shuffle(eligible)

    requested = min(int(count), len(eligible))
    picked = eligible[: min(requested, room)]
    r.eliminated_letters.update(picked)
    if len(picked) < requested:
        r.information_saturated = True
    return picked


def patched_eliminate_absent(game: GameState, count=1):
    return effects._eliminate(game, count)


def _base_candidate_weight(word, target: float, familiarity_bias: str | None) -> float:
    proximity = 1.0 / (0.12 + abs(word.complexity - target))
    desired_familiarity = max(0.38, min(0.88, 0.90 - 0.065 * target))
    natural = math.exp(-0.90 * abs(word.familiarity_score - desired_familiarity))
    if familiarity_bias == "familiar":
        bias = 0.45 + 1.55 * word.familiarity_score
    elif familiarity_bias == "obscure":
        bias = 0.45 + 1.55 * (1.0 - word.familiarity_score)
    else:
        bias = natural
    return proximity * bias


def patched_wordbank_choose(
    bank: WordBank,
    target: float,
    variance: float,
    used_families: set[str],
    rng,
    familiarity_bias: str | None = None,
):
    # Main-run selection is intentionally unchanged. Quickfire also keeps its
    # deliberate compact identity in Endless.
    if not getattr(bank, "_deadletter_endless", False) or bank.bank_id == "quickfire":
        return original_wordbank_choose(bank, target, variance, used_families, rng, familiarity_bias)

    low, high = max(1.0, target - variance), min(10.0, target + variance)
    pool = [w for w in bank.words if w.family_id not in used_families and low <= w.complexity <= high]

    widen = variance
    while not pool and widen < 3.0:
        widen += 0.25
        low, high = max(1.0, target - widen), min(10.0, target + widen)
        pool = [w for w in bank.words if w.family_id not in used_families and low <= w.complexity <= high]
    if not pool:
        pool = [w for w in bank.words if w.family_id not in used_families]
    if not pool:
        raise RuntimeError("Word bank exhausted: no unused word families remain.")

    groups = {"short": [], "medium": [], "long": []}
    group_candidate_weights = {"short": [], "medium": [], "long": []}
    for word in pool:
        bucket = _bucket(word.length)
        groups[bucket].append(word)
        group_candidate_weights[bucket].append(_base_candidate_weight(word, target, familiarity_bias))

    available = [bucket for bucket, words in groups.items() if words]
    if len(available) <= 1:
        weights = [_base_candidate_weight(w, target, familiarity_bias) for w in pool]
        return rng.choices(pool, weights=weights, k=1)[0]

    desired = ENDLESS_BUCKET_WEIGHTS.get(bank.bank_id, ENDLESS_BUCKET_WEIGHTS["standard"])
    recent = [_bucket(int(n)) for n in getattr(bank, "_deadletter_recent_lengths", [])[-6:]]
    recent_counts = Counter(recent[-4:])

    # Consecutive repetition matters more than an older occurrence. This does
    # not ban short hard words; it simply stops runs of the same length bucket.
    streak_bucket = recent[-1] if recent else None
    streak = 0
    if streak_bucket:
        for item in reversed(recent):
            if item != streak_bucket:
                break
            streak += 1

    avg_quality = {
        bucket: sum(group_candidate_weights[bucket]) / len(group_candidate_weights[bucket])
        for bucket in available
    }
    best_quality = max(avg_quality.values()) if avg_quality else 1.0

    bucket_weights = []
    for bucket in available:
        weight = float(desired.get(bucket, 0.0))
        # Keep Complexity proximity/familiarity meaningful without allowing raw
        # candidate counts to determine the entire length distribution.
        quality_ratio = avg_quality[bucket] / best_quality if best_quality > 0 else 1.0
        weight *= 0.75 + 0.25 * math.sqrt(max(0.0, quality_ratio))
        weight *= 0.72 ** recent_counts.get(bucket, 0)
        if bucket == streak_bucket and streak >= 2:
            weight *= 0.50 ** (streak - 1)
        bucket_weights.append(max(0.001, weight))

    chosen_bucket = rng.choices(available, weights=bucket_weights, k=1)[0]
    return rng.choices(
        groups[chosen_bucket],
        weights=group_candidate_weights[chosen_bucket],
        k=1,
    )[0]


def patched_start_round(game: GameState):
    # Feed only run context into the bank; the actual chooser remains responsible
    # for word selection. History is serialized automatically with other GameState
    # attributes, so safe-screen Continue Run remains deterministic.
    history = list(getattr(game, "word_length_history", []))
    game.word_length_history = history[-12:]
    game.bank._deadletter_endless = bool(game.endless)
    game.bank._deadletter_recent_lengths = list(game.word_length_history[-6:])

    previous_round = game.round
    previous_index = game.round_index
    result = original_start_round(game)

    if game.round is not None and game.round is not previous_round and game.round_index == previous_index:
        game.word_length_history = (game.word_length_history + [int(game.round.word.length)])[-12:]
    return result


def patched_on_correct_letter(game, ctx):
    had_precision = game.has_glyph("precision")
    if had_precision:
        with _hide_precision(game):
            result = original_on_correct_letter(game, ctx)
    else:
        result = original_on_correct_letter(game, ctx)

    r = game.round
    if (
        had_precision
        and r is not None
        and not ctx.get("auto", False)
        and r.correct_streak > 0
        and r.correct_streak % 3 == 0
    ):
        r.bonus_points += 350
        game.add_time(3.0)
        r.log.append("Precision +350, +3.0s")
    return result


def patched_run_chrome(self):
    original_run_chrome(self)
    if not self.game:
        return
    bank_id = getattr(self.game, "bank_id", getattr(getattr(self, "bank", None), "bank_id", "standard"))
    bank_name = BANKS.get(bank_id, BANKS["standard"]).name
    self.header_info.config(
        text=f"{self.game.difficulty_def.name}  •  {bank_name}  •  Seed {self.game.seed}"
    )


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def patched_show_tutorial(self, page=0):
    original_show_tutorial(self, page)
    if page != 2:
        return
    # Add the global rule beside the Glyph explanation instead of repeating it
    # inside every individual information-Glyph description.
    parent = None
    for widget in _walk(self.main):
        try:
            text = str(widget.cget("text"))
        except (tk.TclError, AttributeError):
            continue
        if text.startswith("•  Trash unwanted Glyphs"):
            parent = widget.master
            break
    if parent is not None:
        tk.Label(
            parent,
            text=("•  Information Saturation: automatic Glyph/Axiom cross-outs stop once "
                  f"{AUTOMATIC_ABSENT_FLOOR} unguessed absent letters remain. Wrong guesses can still account for them."),
            bg=M.PANEL,
            fg=M.MUTED,
            justify="left",
            wraplength=800,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(10, 0))


def apply_patch(main_module):
    global M
    global original_wordbank_choose, original_start_round, original_on_correct_letter
    global original_eliminate_absent, original_run_chrome, original_show_tutorial

    M = main_module
    _replace_definitions()

    original_wordbank_choose = WordBank.choose
    original_start_round = GameState.start_round
    original_on_correct_letter = effects.on_correct_letter
    original_eliminate_absent = GameState._eliminate_absent
    original_run_chrome = main_module.DeadLetterApp._run_chrome
    original_show_tutorial = main_module.DeadLetterApp.show_tutorial

    effects._eliminate = capped_eliminate
    GameState._eliminate_absent = patched_eliminate_absent
    WordBank.choose = patched_wordbank_choose
    GameState.start_round = patched_start_round
    effects.on_correct_letter = patched_on_correct_letter
    main_module.DeadLetterApp._run_chrome = patched_run_chrome
    main_module.DeadLetterApp.show_tutorial = patched_show_tutorial
