"""Dead Letter v1.1.11 balance pass.

This patch targets clear dominance cases: effects where another option at the
same layer did the same job earlier, more strongly, and/or with no downside.
It intentionally avoids broad difficulty changes.
"""
from __future__ import annotations

from contextlib import contextmanager

import chapter_patch
import effects
import telemetry
from content import AXIOMS, GLYPHS, AxiomDef, GlyphDef, RARITY_TRASH_VALUE
from game_logic import GameState


# ---------------------------------------------------------------------------
# Player-facing definitions
# ---------------------------------------------------------------------------

def _glyph(gid: str, description: str) -> None:
    old = GLYPHS[gid]
    GLYPHS[gid] = GlyphDef(old.id, old.name, old.rarity, description, old.category)


def _axiom(aid: str, description: str) -> None:
    old = AXIOMS[aid]
    AXIOMS[aid] = AxiomDef(old.id, old.name, description)


def _replace_definitions() -> None:
    # Time: Quick Study was crowding out several Common time engines.
    _glyph("momentum",
           "Manual correct letter guesses restore 1.5 seconds, up to 10.5 seconds per word.")
    _glyph("stopwatch",
           "Every 3rd manual correct letter guess restores 5 seconds.")
    _glyph("chain_reaction",
           "Every 3 consecutive manual correct letter guesses restores 7 seconds.")
    _glyph("consonant_clock",
           "Manual correct consonant guesses restore 2 seconds, up to 10 seconds per word.")
    _glyph("second_wind",
           "The first correct guess each word that reveals 2+ copies restores 8 seconds.")

    # Information: Alphabetizer remains the best immediate Common baseline,
    # while delayed/scaling options now have a reason to be chosen over it.
    _glyph("process_elimination",
           "After every 2 manual correct letter guesses, cross out 2 absent letters.")
    _glyph("pressure_notes",
           "When the timer first falls below 50%, cross out 6 absent letters.")
    _glyph("steady_hand",
           "Your second manual correct letter guess each word crosses out 5 absent letters.")
    _glyph("index_cards",
           "Cross out 2 absent letters at word start. Every 4 words solved while owned permanently adds +1 more, up to 6 total.")
    _glyph("thesaurus",
           "Cross out 1 absent letter at word start. Solved words with 6+ unique letters add a page; every 3 pages permanently adds +1 more cross-out, up to 7 total.")

    # Economy: create genuine tradeoffs rather than weaker copies.
    _glyph("cash_flow",
           "Each manual correct letter guess earns +100 Points.")
    _glyph("loaded_dice",
           "Paid Glyph rerolls have a 50% chance to refund their full cost after the new choices appear.")
    _glyph("market_maker",
           "After each Boss, gain 10% of held Points. The rate permanently rises by 2 percentage points per Boss defeated while owned, up to 20%; each payout is capped at 1,200 Points.")

    # Wording/consistency leftovers from the earlier charged-mistake cleanup.
    _glyph("streak_mark",
           "Four consecutive manual correct letter guesses erase 1 mistake from the meter, once per word.")
    _glyph("snowball",
           "Perfect solves build a streak worth +110 Points per streak level; any mistake added to the meter resets it.")

    # Axioms: these were literal subsets of another Axiom's effect.
    _axiom("overtime",
           "Every word starts with +7 seconds, but all scores x0.94.")
    _axiom("boss_insurance",
           "Boss words have +2 mistake capacity.")
    _axiom("preparation",
           "At the start of each Boss, cross out 5 absent letters.")
    _axiom("footnotes",
           "After the first wrong guess each word, cross out 5 absent letters.")
    _axiom("long_game",
           "Gain +0.75 starting seconds per completed Chapter, up to +9 seconds. Continues scaling in Endless.")


@contextmanager
def _hide(game: GameState, *, glyphs=(), axioms=()):
    """Temporarily suppress old implementations while preserving all others."""
    old_glyphs = game.glyphs
    old_axioms = game.axioms
    try:
        if glyphs:
            blocked = set(glyphs)
            game.glyphs = [gid for gid in old_glyphs if gid not in blocked]
        if axioms:
            blocked = set(axioms)
            game.axioms = [aid for aid in old_axioms if aid not in blocked]
        yield
    finally:
        game.glyphs = old_glyphs
        game.axioms = old_axioms


# ---------------------------------------------------------------------------
# Effect replacements
# ---------------------------------------------------------------------------

def patched_on_round_started(game, ctx):
    with _hide(game, glyphs={"thesaurus", "index_cards"}, axioms={"preparation"}):
        original_on_round_started(game, ctx)

    if game.has_glyph("thesaurus"):
        pages = int(game.glyph_state.get("thesaurus_pages", 0))
        effects._eliminate(game, min(7, 1 + pages // 3))

    if game.has_glyph("index_cards"):
        solved = int(game.glyph_state.get("index_cards_words", 0))
        effects._eliminate(game, min(6, 2 + solved // 4))

    if game.has_axiom("preparation") and game.round and game.round.boss_id:
        effects._eliminate(game, 5)


def patched_on_correct_letter(game, ctx):
    replaced = {
        "momentum", "stopwatch", "chain_reaction", "consonant_clock",
        "second_wind", "cash_flow", "process_elimination", "steady_hand",
    }
    with _hide(game, glyphs=replaced):
        original_on_correct_letter(game, ctx)

    r = game.round
    if r is None:
        return
    ch = ctx["letter"]
    count = ctx["count"]
    auto = ctx.get("auto", False)

    if count >= 2 and game.has_glyph("second_wind") and not getattr(r, "second_wind_used", False):
        r.second_wind_used = True
        game.add_time(8.0)

    if not auto:
        if game.has_glyph("momentum"):
            added = float(getattr(r, "momentum_added", 0.0))
            grant = min(1.5, 10.5 - added)
            if grant > 0:
                game.add_time(grant)
                r.momentum_added = added + grant

        if game.has_glyph("stopwatch") and r.correct_letter_guesses % 3 == 0:
            game.add_time(5.0)

        if game.has_glyph("chain_reaction") and r.correct_streak % 3 == 0:
            game.add_time(7.0)

        if game.has_glyph("consonant_clock") and ch not in effects.VOWELS:
            added = float(getattr(r, "consonant_clock_added", 0.0))
            grant = min(2.0, 10.0 - added)
            if grant > 0:
                game.add_time(grant)
                r.consonant_clock_added = added + grant

        if game.has_glyph("cash_flow"):
            r.bonus_points += 100

        if game.has_glyph("process_elimination") and r.correct_letter_guesses % 2 == 0:
            picked = effects._eliminate(game, 2)
            if picked:
                r.log.append(f"Process of Elimination crossed out {len(picked)} letters")

        if game.has_glyph("steady_hand") and r.correct_letter_guesses == 2:
            effects._eliminate(game, 5)


def patched_on_wrong_action(game, ctx):
    # Annotations gives two guaranteed cross-outs at word start. Footnotes now
    # waits for a mistake, but pays much more strongly when that recovery trigger
    # is actually needed.
    with _hide(game, axioms={"footnotes"}):
        original_on_wrong_action(game, ctx)
    r = game.round
    if (
        r is not None
        and game.has_axiom("footnotes")
        and not getattr(r, "footnotes_used", False)
    ):
        r.footnotes_used = True
        effects._eliminate(game, 5)


def patched_tick(game, dt):
    # Pressure Notes used to be a delayed, smaller Alphabetizer. Suppress the
    # old 3-letter trigger and apply the stronger delayed payoff instead.
    with _hide(game, glyphs={"pressure_notes"}):
        result = original_tick(game, dt)
    r = game.round
    if (
        r is not None
        and game.status == "playing"
        and game.has_glyph("pressure_notes")
        and not r.pressure_notes_triggered
        and r.remaining_time <= r.initial_time * 0.50
    ):
        r.pressure_notes_triggered = True
        picked = effects._eliminate(game, 6)
        if picked:
            r.last_message = f"Pressure Notes crossed out {len(picked)} absent letters."
    return result


def patched_after_solve(game):
    # Dividend pays every word. Market Maker is now a true boss-based scaler
    # instead of a rarer, lower-EV version of Dividend.
    with _hide(game, glyphs={"market_maker"}):
        original_after_solve(game)

    r = game.round
    if r and r.boss_id and game.has_glyph("market_maker"):
        bosses = int(game.glyph_state.get("market_maker_bosses", 0))
        rate = min(0.20, 0.10 + 0.02 * bosses)
        gain = min(1200, int(game.points * rate))
        if gain > 0:
            game.points += gain
            game.total_earned += gain
            r.log.append(f"Market Maker +{gain}")
        game.glyph_state["market_maker_bosses"] = bosses + 1


def patched_starting_time_delta(game, word, boss_id):
    delta = original_starting_time_delta(game, word, boss_id)
    # The base start_round implementation already gives Overtime +3. Adding
    # the remaining +4 here makes the intended +7 happen before threshold
    # effects such as Deadline Extension are evaluated.
    if game.has_axiom("overtime"):
        delta += 4.0
    return delta


def patched_score_multiplier(game):
    mult = original_score_multiplier(game)
    if game.has_axiom("overtime"):
        mult *= 0.94 / 0.96
    # The player-facing No Vowels text has said x1.35; the implementation was
    # accidentally left at x1.30.
    if game.has_glyph("no_vowels") and game.round:
        letters = set(game.round.word.word)
        if len(letters & effects.VOWELS) <= 1:
            mult *= 1.35 / 1.30
    return mult


def patched_base_time_for_round(game):
    base = original_base_time_for_round(game)
    if game.has_axiom("long_game"):
        completed = game.completed_chapters
        old_bonus = min(8.0, 0.5 * completed)
        new_bonus = min(9.0, 0.75 * completed)
        base += new_bonus - old_bonus
    return base


def patched_start_round(game):
    result = original_start_round(game)
    r = game.round
    # chapter_patch may stop at the untimed preview with no round generated.
    if r is None or not r.boss_id or not game.has_axiom("boss_insurance"):
        return result

    # The original implementation has already granted +1. Add the second point
    # to the normal ceiling. The Executioner still begins at 3, but can recover
    # toward the larger insured ceiling through correct guesses.
    r.mistake_cap_ceiling = int(getattr(r, "mistake_cap_ceiling", r.max_mistakes)) + 1
    if r.boss_id != "executioner":
        r.max_mistakes += 1
    return result


def patched_reroll_glyphs(game):
    if game.status != "glyph_choice":
        return False, "Not choosing Glyphs."
    cost = game.glyph_reroll_cost()
    if game.points < cost:
        return False, "Not enough Points."
    offers_before = list(game.glyph_offers)
    points_before = game.points
    glyphs_before = list(game.glyphs)
    axioms_before = list(game.axioms)
    game.points -= cost
    if cost > 0 and game.has_glyph("reinvestment"):
        game.next_word_time_bonus = min(8.0, game.next_word_time_bonus + 2.0)
    if cost == 0 and game.has_axiom("fresh_ink"):
        game.fresh_ink_available = False
    game.glyph_rerolls += 1
    game._roll_glyph_offers()
    refunded = 0
    if cost > 0 and game.has_glyph("loaded_dice") and game.rng.random() < 0.50:
        game.points += cost
        refunded = cost
    telemetry.record_decision(
        game, "glyph", "reroll",
        offers_before=offers_before, offers_after=list(game.glyph_offers),
        cost=cost, points_before=points_before,
        glyphs_before=glyphs_before, axioms_before=axioms_before,
    )
    if refunded:
        return True, f"Loaded Dice refunded the {cost} Point reroll."
    return True, f"Rerolled for {cost} Points."


def patched_init_glyph_state(game, gid):
    original_init_glyph_state(game, gid)
    if gid == "market_maker":
        game.glyph_state.setdefault("market_maker_bosses", 0)


def patched_clear_glyph_state(game, gid):
    original_clear_glyph_state(game, gid)
    if gid == "market_maker":
        game.glyph_state.pop("market_maker_bosses", None)


def _with_sell_value(game, gid: str, text: str) -> str:
    if game.has_axiom("recycling"):
        value = RARITY_TRASH_VALUE[GLYPHS[gid].rarity]
        if "Sell value:" not in text:
            text += f"  Sell value: {value} Points."
    return text


def patched_glyph_description(game, gid):
    if gid == "thesaurus" and gid in game.glyphs:
        pages = int(game.glyph_state.get("thesaurus_pages", 0))
        total = min(7, 1 + pages // 3)
        text = f"{GLYPHS[gid].description}  Current: {pages} page{'s' if pages != 1 else ''}; {total} cross-outs."
        return _with_sell_value(game, gid, text)
    if gid == "index_cards" and gid in game.glyphs:
        solved = int(game.glyph_state.get("index_cards_words", 0))
        total = min(6, 2 + solved // 4)
        text = f"{GLYPHS[gid].description}  Current: {solved} solved; {total} cross-outs."
        return _with_sell_value(game, gid, text)
    if gid == "market_maker" and gid in game.glyphs:
        bosses = int(game.glyph_state.get("market_maker_bosses", 0))
        rate = min(20, 10 + 2 * bosses)
        text = f"{GLYPHS[gid].description}  Current rate: {rate}%."
        return _with_sell_value(game, gid, text)
    return original_glyph_description(game, gid)


# ---------------------------------------------------------------------------
# Chapter-preview parity
# ---------------------------------------------------------------------------

def patched_preview_base_time(game, round_index):
    base = original_preview_base_time(game, round_index)
    if game.has_axiom("long_game"):
        completed = round_index // game.WORDS_PER_CHAPTER
        old_bonus = min(8.0, 0.5 * completed)
        new_bonus = min(9.0, 0.75 * completed)
        base += new_bonus - old_bonus
    return base


def patched_preview_glyph_time(game, first_round):
    delta = original_preview_glyph_time(game, first_round)
    if game.has_axiom("overtime"):
        delta += 4.0
    return delta


def apply_patch(main_module):
    global original_on_round_started, original_on_correct_letter, original_on_wrong_action, original_after_solve
    global original_tick, original_starting_time_delta, original_score_multiplier
    global original_base_time_for_round, original_start_round, original_reroll_glyphs
    global original_init_glyph_state, original_clear_glyph_state, original_glyph_description
    global original_preview_base_time, original_preview_glyph_time

    _replace_definitions()

    original_on_round_started = effects.on_round_started
    original_on_correct_letter = effects.on_correct_letter
    original_on_wrong_action = effects.on_wrong_action
    original_after_solve = effects.after_solve
    original_starting_time_delta = effects.starting_time_delta
    original_score_multiplier = effects.score_multiplier
    original_tick = GameState.tick
    original_base_time_for_round = GameState.base_time_for_round
    original_start_round = GameState.start_round
    original_reroll_glyphs = GameState.reroll_glyphs
    original_init_glyph_state = GameState._init_glyph_state
    original_clear_glyph_state = GameState._clear_glyph_state
    original_glyph_description = GameState.glyph_description

    effects.on_round_started = patched_on_round_started
    effects.on_correct_letter = patched_on_correct_letter
    effects.on_wrong_action = patched_on_wrong_action
    effects.after_solve = patched_after_solve
    effects.starting_time_delta = patched_starting_time_delta
    effects.score_multiplier = patched_score_multiplier
    GameState.tick = patched_tick
    GameState.base_time_for_round = patched_base_time_for_round
    GameState.start_round = patched_start_round
    GameState.reroll_glyphs = patched_reroll_glyphs
    GameState._init_glyph_state = patched_init_glyph_state
    GameState._clear_glyph_state = patched_clear_glyph_state
    GameState.glyph_description = patched_glyph_description

    # chapter_patch mirrors predictable time formulas for its preview screen.
    original_preview_base_time = chapter_patch._base_time_at
    original_preview_glyph_time = chapter_patch._predictable_glyph_time_delta
    chapter_patch._base_time_at = patched_preview_base_time
    chapter_patch._predictable_glyph_time_delta = patched_preview_glyph_time
