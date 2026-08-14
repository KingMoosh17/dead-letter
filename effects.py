"""Event-driven Glyph effects for Dead Letter v1.1."""
from __future__ import annotations

VOWELS = set("aeiou")
RARE = set("jqxz")
ALPHABET = set("abcdefghijklmnopqrstuvwxyz")


def _absent_letters(game):
    r = game.round
    return list(ALPHABET - set(r.word.word) - r.guessed_letters - r.eliminated_letters)


def _eliminate(game, count: int, candidates=None) -> list[str]:
    if candidates is None:
        candidates = _absent_letters(game)
    else:
        candidates = list(set(candidates) - game.round.guessed_letters - game.round.eliminated_letters)
    game.rng.shuffle(candidates)
    picked = candidates[:count]
    game.round.eliminated_letters.update(picked)
    return picked


def _auto_reveal(game, ch: str):
    if ch and ch not in game.round.guessed_letters:
        game._guess_letter_internal(ch, auto=True)


def starting_time_delta(game, word, boss_id) -> float:
    """Glyph-only starting-time changes; called after the word has been selected."""
    letters = set(word.word)
    delta = 0.0
    if game.has_glyph("pencil_eraser"):
        delta -= 3.0
    if game.has_glyph("hourglass"):
        delta += 7.0
    if game.has_glyph("rush_job"):
        delta -= 7.0
    if game.has_glyph("nest_egg") and game.points >= 1500:
        delta += 3.0
    if game.has_glyph("sesquipedalian") and word.length >= 9:
        delta += 2.0
    if game.has_glyph("short_story") and word.length <= 6:
        delta += 3.0
    if game.has_glyph("no_vowels") and len(letters & VOWELS) <= 1:
        delta += 4.0
    if game.has_glyph("odd_job") and word.length % 2 == 1:
        delta += 5.0
    if game.has_glyph("even_keel") and word.length % 2 == 0:
        delta += 5.0
    if game.has_glyph("vowel_rich") and len(letters & VOWELS) >= 3:
        delta += 2.0
    if game.has_glyph("scholar") and word.complexity >= 6.5:
        delta += 2.0
    if game.has_glyph("rare_form") and word.complexity >= 8.0:
        delta += 3.0
    if game.has_glyph("common_ground") and word.complexity <= 5.0:
        delta += 3.0
    if game.has_glyph("inkblot"):
        delta -= 5.0
    if game.has_glyph("double_entry"):
        delta -= 4.0
    if game.has_glyph("deadline_writer"):
        delta += float(game.glyph_state.get("deadline_writer_time", 0.0))
    if game.has_glyph("rolling_press"):
        delta += float(game.glyph_state.get("rolling_press_time", 0.0))
    delta += float(getattr(game, "next_word_time_bonus", 0.0))
    return delta


def on_round_started(game, ctx):
    r = game.round

    if game.has_glyph("lottery_ticket") and game.rng.random() < 0.20:
        r.max_mistakes += 1
        r.initial_time += 5.0
        r.remaining_time += 5.0
        r.log.append("Lottery Ticket hit: +1 mistake capacity, +5.0s")

    if game.has_glyph("field_notes"):
        unique_vowels = len(set(r.word.word) & VOWELS)
        repeated = len(set(r.word.word)) < r.word.length
        fam = r.word.familiarity_score
        familiarity = "common" if fam >= 0.72 else "uncommon" if fam >= 0.48 else "obscure"
        r.extra_clues = [
            f"{unique_vowels} unique vowel{'s' if unique_vowels != 1 else ''}",
            "repeated letter" if repeated else "no repeated letters",
            f"{familiarity} vocabulary",
        ]

    if game.has_glyph("thesaurus"):
        pages = int(game.glyph_state.get("thesaurus_pages", 0))
        if pages >= 3:
            _eliminate(game, min(4, pages // 3))
    if game.has_glyph("index_cards"):
        solved = int(game.glyph_state.get("index_cards_words", 0))
        if solved >= 4:
            _eliminate(game, min(4, solved // 4))
    if game.has_glyph("inkblot"):
        _eliminate(game, 7)

    if game.has_glyph("frequency_chart"):
        present = list(set(r.word.word))
        absent = _absent_letters(game)
        game.rng.shuffle(present)
        game.rng.shuffle(absent)
        hints = present[:2] + absent[:max(0, 4 - min(2, len(present)))]
        while len(hints) < 4 and len(present) > len(hints):
            hints.append(present[len(hints)])
        game.rng.shuffle(hints)
        r.highlight_letters.update(hints[:4])

    if game.has_glyph("alphabetizer"):
        _eliminate(game, 4)
    if game.has_glyph("lexicographer"):
        _eliminate(game, 2)
    if game.has_glyph("vowel_census"):
        absent_vowels = list(VOWELS - set(r.word.word))
        _eliminate(game, 1, absent_vowels)
    if game.has_glyph("unique_voice") and len(set(r.word.word)) == r.word.length:
        _eliminate(game, 2)

    if game.has_axiom("open_book"):
        _eliminate(game, 1)
    if game.has_axiom("annotations"):
        _eliminate(game, 2)
    if game.has_axiom("preparation") and r.boss_id:
        _eliminate(game, 2)

    # Automatic reveals are the effects The Purist disables.
    if r.boss_id != "purist":
        if game.has_glyph("acrostic"):
            _auto_reveal(game, r.word.word[0])
        if game.has_glyph("epilogue") and game.status in {"playing", "boss_ready"}:
            _auto_reveal(game, r.word.word[-1])

    if game.has_glyph("dividend") and game.points > 0:
        gain = min(150, int(game.points * 0.03))
        if gain:
            game.points += gain
            game.total_earned += gain
            r.log.append(f"Dividend +{gain}")


def on_correct_letter(game, ctx):
    r = game.round
    ch = ctx["letter"]
    count = ctx["count"]
    auto = ctx.get("auto", False)

    if not auto:
        r.correct_streak += 1

        if r.comeback_armed and game.has_glyph("comeback"):
            game.add_time(7.0)
            r.comeback_armed = False
            r.log.append("Comeback +7.0s")

        if game.has_axiom("letter_of_law") and r.correct_letter_guesses == 1:
            game.add_time(2.0)

        if game.has_glyph("momentum"):
            added = float(getattr(r, "momentum_added", 0.0))
            grant = min(1.25, 7.5 - added)
            if grant > 0:
                game.add_time(grant)
                r.momentum_added = added + grant

        if game.has_glyph("quick_study") and r.correct_letter_guesses <= 2:
            game.add_time(4.0)
        if game.has_glyph("stopwatch") and r.correct_letter_guesses % 3 == 0:
            game.add_time(3.5)
        if game.has_glyph("chain_reaction") and r.correct_streak % 3 == 0:
            game.add_time(4.5)
        if game.has_glyph("vowel_clock") and ch in VOWELS:
            game.add_time(2.0)
        if game.has_glyph("consonant_clock") and ch not in VOWELS:
            added = float(getattr(r, "consonant_clock_added", 0.0))
            grant = min(1.5, 7.5 - added)
            if grant > 0:
                game.add_time(grant)
                r.consonant_clock_added = added + grant
        if game.has_glyph("emergency_fund") and r.remaining_time < 10.0 and not getattr(r, "emergency_used", False):
            r.emergency_used = True
            game.add_time(6.0)
            r.log.append("Emergency Fund +6.0s")

    if count >= 2 and game.has_glyph("second_wind") and not getattr(r, "second_wind_used", False):
        r.second_wind_used = True
        game.add_time(5.0)
    if count > 1 and game.has_glyph("echo"):
        game.add_time(5.0)
    if count > 1 and game.has_glyph("repeater") and not getattr(r, "repeater_time_used", False):
        r.repeater_time_used = True
        game.add_time(3.0)
    if r.boss_id == "deadline" and not auto:
        game.add_time(3.0)

    # Scoring effects
    if game.has_glyph("double_letter") and count > 1:
        r.bonus_points += 220
        r.log.append("Double Letter +220")
    if game.has_glyph("letterpress") and not auto:
        r.bonus_points += 65 * count
    if game.has_glyph("cash_flow") and not auto:
        r.bonus_points += 60
    if ch in VOWELS and ch not in r.vowels_rewarded and game.has_glyph("vowel_collector"):
        r.vowels_rewarded.add(ch)
        r.bonus_points += 120

    if not auto and ch not in VOWELS:
        r.consonant_streak += 1
        if game.has_glyph("consonance"):
            r.bonus_points += 35 * r.consonant_streak
            if r.consonant_streak % 3 == 0:
                game.add_time(1.5)
    elif not auto:
        r.consonant_streak = 0

    if not auto and game.has_glyph("first_draft") and r.total_letter_guesses == 1:
        r.bonus_points += 250
        game.add_time(2.5)
        r.log.append("First Draft +250, +2.5s")
    if not auto and game.has_glyph("blind_faith") and r.total_letter_guesses == 1:
        r.bonus_points += 300
        r.log.append("Blind Faith +300")
    if (not auto and game.has_glyph("high_scrabble") and ch in RARE
            and not getattr(r, "high_scrabble_used", False)):
        r.high_scrabble_used = True
        r.bonus_points += 400
        game.add_time(3.0)
        r.log.append("High Scrabble +400, +3.0s")
    if (not auto and game.has_glyph("bookends") and not getattr(r, "bookends_used", False)
            and ch in {r.word.word[0], r.word.word[-1]}):
        r.bookends_used = True
        r.bonus_points += 200
        _eliminate(game, 2)

    # v1.1 utility synergies
    if auto and game.has_glyph("quiet_room"):
        added = float(getattr(r, "quiet_room_added", 0.0))
        grant = min(1.5, 4.5 - added)
        if grant > 0:
            game.add_time(grant)
            r.quiet_room_added = added + grant

    if (auto and game.has_glyph("double_entry") and not getattr(r, "double_entry_used", False)
            and r.boss_id != "purist"):
        r.double_entry_used = True
        candidates = list(set(r.word.word) - r.guessed_letters)
        if candidates:
            _auto_reveal(game, game.rng.choice(candidates))

    if not auto and game.has_glyph("precision") and r.correct_streak % 3 == 0:
        _eliminate(game, 2)

    if not auto and game.has_glyph("tightrope") and r.max_mistakes - r.mistakes == 1:
        game.add_time(2.5)

    if (not auto and game.has_glyph("streak_mark") and r.correct_streak >= 4
            and r.mistakes > 0 and not getattr(r, "streak_mark_used", False)):
        r.streak_mark_used = True
        r.mistakes -= 1
        r.log.append("Streak Mark erased 1 mistake")

    if (game.has_glyph("spotlight") and not getattr(r, "spotlight_used", False)
            and len(set(r.word.word) & r.guessed_letters) >= max(1, (len(set(r.word.word)) + 1) // 2)):
        r.spotlight_used = True
        present = list(set(r.word.word) - r.guessed_letters)
        absent = _absent_letters(game)
        game.rng.shuffle(present)
        game.rng.shuffle(absent)
        hints = present[:2] + absent[:2]
        while len(hints) < 4 and present:
            candidate = game.rng.choice(present)
            if candidate not in hints:
                hints.append(candidate)
            else:
                break
        game.rng.shuffle(hints)
        r.highlight_letters.update(hints[:4])

    # Information effects
    if (not auto and game.has_glyph("vowel_movement") and ch in VOWELS
            and not r.vowel_movement_used and r.boss_id != "purist"):
        r.vowel_movement_used = True
        candidates = list((set(r.word.word) & VOWELS) - r.guessed_letters)
        if candidates:
            reveal = game.rng.choice(candidates)
            _auto_reveal(game, reveal)
            r.log.append(f"Vowel Movement revealed {reveal.upper()}")

    if not auto and game.has_glyph("process_elimination") and r.correct_letter_guesses % 2 == 0:
        picked = _eliminate(game, 1)
        if picked:
            r.log.append(f"Process of Elimination crossed out {picked[0].upper()}")

    if not auto and game.has_glyph("steady_hand") and r.correct_letter_guesses == 2:
        _eliminate(game, 2)

    if (not auto and game.has_glyph("pattern_reader") and r.correct_letter_guesses >= 4
            and not getattr(r, "pattern_reader_used", False) and r.boss_id != "purist"):
        r.pattern_reader_used = True
        candidates = list(set(r.word.word) - r.guessed_letters)
        if candidates:
            reveal = game.rng.choice(candidates)
            _auto_reveal(game, reveal)
            r.log.append(f"Pattern Reader revealed {reveal.upper()}")


def on_wrong_action(game, ctx):
    r = game.round
    attempted = ctx.get("attempted", ctx.get("amount", 0))

    r.correct_streak = 0

    if game.has_glyph("bookmark") and not getattr(r, "bookmark_used", False):
        r.bookmark_used = True
        game.add_time(3.5)

    if game.has_glyph("dead_letter") and ctx.get("kind") == "letter":
        _eliminate(game, 2)

    if (game.has_glyph("red_string") and getattr(r, "wrong_actions", 0) >= 3
            and not getattr(r, "red_string_used", False)):
        r.red_string_used = True
        game.add_time(2.0)
        if r.boss_id != "purist":
            candidates = list(set(r.word.word) - r.guessed_letters)
            if candidates:
                _auto_reveal(game, game.rng.choice(candidates))

    if (game.has_glyph("panic_button") and r.max_mistakes - r.mistakes == 1
            and not getattr(r, "panic_button_used", False)):
        r.panic_button_used = True
        game.add_time(6.0)

    if (game.has_glyph("last_word") and r.max_mistakes - r.mistakes == 1
            and not getattr(r, "last_word_used", False)):
        r.last_word_used = True
        game.add_time(4.0)
        if r.boss_id != "purist":
            candidates = list(set(r.word.word) - r.guessed_letters)
            if candidates:
                _auto_reveal(game, game.rng.choice(candidates))

    if (game.has_glyph("bailout") and r.max_mistakes - r.mistakes == 1
            and not getattr(r, "bailout_used", False) and game.points >= 500):
        r.bailout_used = True
        game.points -= 500
        r.max_mistakes += 1
        r.log.append("Bailout spent 500 Points for +1 mistake capacity")

    if game.has_glyph("comeback"):
        r.comeback_armed = True

    if game.has_glyph("red_pen") and attempted > 0:
        r.remaining_time = max(0.0, r.remaining_time - attempted * 2.0)
        r.bonus_points += attempted * 110

    if game.has_axiom("footnotes") and not getattr(r, "footnotes_used", False):
        r.footnotes_used = True
        _eliminate(game, 2)

    if game.has_glyph("cross_reference") and not r.cross_reference_used:
        r.cross_reference_used = True
        present = list(set(r.word.word) - r.guessed_letters)
        absent = _absent_letters(game)
        game.rng.shuffle(present)
        game.rng.shuffle(absent)
        hints = present[:2] + absent[:2]
        game.rng.shuffle(hints)
        r.highlight_letters.update(hints)

    if (game.has_glyph("safety_net") and not r.safety_net_used
            and r.max_mistakes - r.mistakes <= 1 and not r.failed):
        r.safety_net_used = True
        _eliminate(game, 4)
        game.add_time(2.0)
        r.log.append("Safety Net crossed out 4 letters and restored 2.0s")

    if (game.has_glyph("recovery_room") and not getattr(r, "recovery_room_used", False)
            and r.mistakes >= 2 and not r.failed):
        r.recovery_room_used = True
        game.add_time(6.0)
        r.log.append("Recovery Room +6.0s")


def solve_bonus(game, method: str) -> int:
    r = game.round
    bonus = 0
    unique_count = len(set(r.word.word))
    revealed_before = len(set(r.word.word) & r.guessed_letters)

    if game.has_glyph("proofreading") and r.mistakes == 0:
        bonus += 400
    if game.has_glyph("time_dividend") and r.remaining_time >= r.initial_time * 0.50:
        bonus += 450
    if game.has_glyph("cliffhanger") and r.max_mistakes - r.mistakes <= 1:
        bonus += 650
    if game.has_glyph("hard_copy") and r.word.complexity >= r.target_complexity + 0.30:
        bonus += 500
    if game.has_glyph("gambler") and method == "full_word":
        bonus += 450
    if (game.has_glyph("cold_read") and method == "full_word"
            and revealed_before < max(1, (unique_count + 1) // 2)):
        bonus += 500
    if game.has_glyph("snowball") and r.mistakes == 0:
        streak = int(game.glyph_state.get("snowball_streak", 0)) + 1
        bonus += 110 * streak
    if game.has_glyph("tightrope") and r.max_mistakes - r.mistakes == 1:
        bonus += 300
    return bonus


def score_multiplier(game) -> float:
    r = game.round
    w = r.word
    letters = set(w.word)
    mult = 1.0

    # Structure / complexity
    if game.has_glyph("sesquipedalian") and w.length >= 9:
        mult *= 1.35
    if game.has_glyph("short_story") and w.length <= 6:
        mult *= 1.35
    if game.has_glyph("no_vowels") and len(letters & VOWELS) <= 1:
        mult *= 1.30
    if game.has_glyph("repeater") and len(letters) < w.length:
        mult *= 1.30
    if game.has_glyph("unique_voice") and len(letters) == w.length:
        mult *= 1.25
    if game.has_glyph("alphabet_soup") and len(letters) >= 7:
        mult *= 1.25
    if game.has_glyph("odd_job") and w.length % 2 == 1:
        mult *= 1.12
    if game.has_glyph("even_keel") and w.length % 2 == 0:
        mult *= 1.12
    if game.has_glyph("vowel_rich") and len(letters & VOWELS) >= 3:
        mult *= 1.30
    if game.has_glyph("middle_ground") and 6 <= w.length <= 9:
        mult *= 1.18
    if game.has_glyph("scholar") and w.complexity >= 6.5:
        mult *= 1.22
    if game.has_glyph("rare_form") and w.complexity >= 8.0:
        mult *= 1.40
    if game.has_glyph("common_ground") and w.complexity <= 5.0:
        mult *= 1.25

    # Risk / economy
    if game.has_glyph("hourglass"):
        mult *= 0.90
    if game.has_glyph("rush_job"):
        mult *= 1.35
    if game.has_glyph("glass_cannon"):
        mult *= 1.45
    if game.has_glyph("margin_note"):
        mult *= 0.88
    if game.has_glyph("final_answer") and r.solve_method == "full_word":
        mult *= 1.50
    if game.has_glyph("compound_interest"):
        mult *= 1.0 + min(0.20, (game.points // 500) * 0.01)

    # Persistent scalers
    if game.has_glyph("perfect_copy"):
        mult *= float(game.glyph_state.get("perfect_copy_mult", 1.0))

    # Axioms
    if game.has_axiom("high_standards"):
        mult *= 1.25
    if game.has_axiom("overtime"):
        mult *= 0.96
    if game.has_axiom("sharp_deadline"):
        mult *= 1.12
    if game.has_axiom("familiar_ground"):
        mult *= 0.95
    if game.has_axiom("deep_cut"):
        mult *= 1.18
    if game.has_axiom("boss_bounty") and r.boss_id:
        mult *= 1.45
    if game.has_axiom("perfect_binding") and r.mistakes == 0:
        mult *= 1.12
    return mult


def after_solve(game):
    r = game.round
    unique_count = len(set(r.word.word))

    if game.has_glyph("perfect_copy") and r.mistakes == 0:
        game.glyph_state["perfect_copy_mult"] = min(
            4.0, float(game.glyph_state.get("perfect_copy_mult", 1.0)) + 0.05
        )
    if game.has_glyph("thesaurus") and unique_count >= 6:
        game.glyph_state["thesaurus_pages"] = int(game.glyph_state.get("thesaurus_pages", 0)) + 1
    if game.has_glyph("deadline_writer") and r.remaining_time < 10.0:
        game.glyph_state["deadline_writer_time"] = min(
            7.0, float(game.glyph_state.get("deadline_writer_time", 0.0)) + 0.35
        )
    if game.has_glyph("rolling_press") and r.boss_id:
        game.glyph_state["rolling_press_time"] = min(
            6.0, float(game.glyph_state.get("rolling_press_time", 0.0)) + 0.60
        )

    if game.has_glyph("snowball"):
        if r.mistakes == 0:
            game.glyph_state["snowball_streak"] = int(game.glyph_state.get("snowball_streak", 0)) + 1
        else:
            game.glyph_state["snowball_streak"] = 0

    if game.has_glyph("index_cards"):
        game.glyph_state["index_cards_words"] = int(game.glyph_state.get("index_cards_words", 0)) + 1

    if game.has_glyph("market_maker") and r.boss_id:
        gain = min(500, int(game.points * 0.05))
        if gain > 0:
            game.points += gain
            game.total_earned += gain
            r.log.append(f"Market Maker +{gain}")

    if game.has_glyph("proofreading") and r.mistakes == 0:
        game.next_word_time_bonus = min(10.0, float(getattr(game, "next_word_time_bonus", 0.0)) + 2.0)
    if game.has_glyph("time_dividend") and r.remaining_time >= r.initial_time * 0.50:
        game.next_word_time_bonus = min(10.0, float(getattr(game, "next_word_time_bonus", 0.0)) + 1.5)
    if game.has_glyph("cliffhanger") and r.max_mistakes - r.mistakes <= 1:
        game.next_word_time_bonus = min(10.0, float(getattr(game, "next_word_time_bonus", 0.0)) + 2.0)
