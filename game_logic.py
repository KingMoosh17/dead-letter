from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from content import GLYPHS, AXIOMS, BOSSES, DIFFICULTIES, RARITY_WEIGHTS, RARITY_TRASH_VALUE, BOSS_COMPLEXITY_BUDGET
import effects
import telemetry
from wordbank import WordBank, WordEntry, BANKS

VOWELS = set("aeiou")
ALPHABET = set("abcdefghijklmnopqrstuvwxyz")


@dataclass
class RoundState:
    word: WordEntry
    target_complexity: float
    variance: float
    initial_time: float
    remaining_time: float
    max_mistakes: int
    boss_id: Optional[str] = None
    guessed_letters: set[str] = field(default_factory=set)
    eliminated_letters: set[str] = field(default_factory=set)
    reveal_times: dict[str, float] = field(default_factory=dict)
    mistakes: int = 0
    elapsed: float = 0.0
    bonus_points: int = 0
    correct_letter_guesses: int = 0
    total_letter_guesses: int = 0
    letter_guess_sequence: list[str] = field(default_factory=list)
    wrong_letter_sequence: list[str] = field(default_factory=list)
    correct_streak: int = 0
    consonant_streak: int = 0
    vowels_rewarded: set[str] = field(default_factory=set)
    highlight_letters: set[str] = field(default_factory=set)
    vowel_movement_used: bool = False
    eraser_used: bool = False
    reserve_ink_triggered: bool = False
    pressure_notes_triggered: bool = False
    cross_reference_used: bool = False
    safety_net_used: bool = False
    comeback_armed: bool = False
    solved: bool = False
    failed: bool = False
    solve_method: str = ""
    last_message: str = ""
    log: list[str] = field(default_factory=list)
    attempted_mistakes: int = 0
    wrong_letter_guesses: int = 0
    wrong_full_word_guesses: int = 0
    full_word_attempts: int = 0
    auto_revealed_letters: int = 0
    points_at_start: int = 0
    telemetry_recorded: bool = False
    wrong_actions: int = 0
    extra_clues: list[str] = field(default_factory=list)
    mistake_cap_ceiling: int = 6
    censored_letter: str = ""
    forbidden_letter: str = ""


class GameState:
    CHAPTERS = 8
    WORDS_PER_CHAPTER = 4

    def __init__(self, bank: WordBank, seed: Optional[int] = None, difficulty: str = "medium",
                 data_dir=None, telemetry_enabled: bool = True, bank_id: str | None = None):
        self.bank = bank
        self.bank_id = bank_id if bank_id in BANKS else getattr(bank, "bank_id", "standard")
        self.difficulty = difficulty if difficulty in DIFFICULTIES else "medium"
        self.data_dir = data_dir
        self.telemetry_enabled = bool(telemetry_enabled)
        self.seed = seed if seed is not None else random.randrange(1, 10**9)
        self.rng = random.Random(self.seed)
        self.run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{self.seed}"
        self.points = 0
        self.total_earned = 0
        self.round_index = 0
        self.used_families: set[str] = set()
        self.glyphs: list[str] = []
        self.axioms: list[str] = []
        self.glyph_state: dict[str, float | int] = {}
        self.round: Optional[RoundState] = None
        self.last_result: dict = {}
        self.glyph_offers: list[str] = []
        self.axiom_offers: list[str] = []
        self.glyph_rerolls = 0
        self.axiom_rerolled = False
        self.fresh_ink_available = False
        self.endless = False
        self.final_boss_axiom_pending = False
        self.next_word_time_bonus = 0.0
        self.run_stats = {
            "words_solved": 0, "bosses_defeated": 0, "perfect_words": 0,
            "full_word_solves": 0, "highest_complexity_solved": 0.0,
            "fastest_solve": None, "attempted_mistakes": 0, "auto_reveals": 0,
        }

        boss_ids = list(BOSSES)
        self.rng.shuffle(boss_ids)
        self.chapter_bosses = boss_ids[:]
        self.status = "ready"  # ready, boss_ready, playing, glyph_choice, axiom_choice, won, lost

    @property
    def chapter(self):
        return self.round_index // self.WORDS_PER_CHAPTER + 1

    @property
    def round_in_chapter(self):
        return self.round_index % self.WORDS_PER_CHAPTER + 1

    @property
    def completed_chapters(self):
        return self.round_index // self.WORDS_PER_CHAPTER

    @property
    def is_boss_round(self):
        return self.round_in_chapter == self.WORDS_PER_CHAPTER

    def _ensure_boss_for_chapter(self, chapter: int):
        while len(self.chapter_bosses) < chapter:
            cycle = list(BOSSES)
            self.rng.shuffle(cycle)
            if self.chapter_bosses and cycle and cycle[0] == self.chapter_bosses[-1] and len(cycle) > 1:
                cycle[0], cycle[1] = cycle[1], cycle[0]
            self.chapter_bosses.extend(cycle)

    @property
    def current_boss_id(self):
        self._ensure_boss_for_chapter(self.chapter)
        return self.chapter_bosses[self.chapter - 1]

    @property
    def difficulty_def(self):
        return DIFFICULTIES[self.difficulty]

    def has_glyph(self, glyph_id):
        return glyph_id in self.glyphs

    def has_axiom(self, axiom_id):
        return axiom_id in self.axioms

    def glyph_slots(self):
        slots = 5
        if self.has_axiom("expanded_vocabulary"):
            slots += 1
        if self.has_axiom("archive"):
            slots += 2
        if self.has_axiom("scaling_ink"):
            slots += self.completed_chapters // 4
        return slots

    def target_for_round(self):
        # v0.6 eases the opening and midgame so builds have time to develop.
        # The curve still reaches genuinely difficult vocabulary by Chapter 8.
        if self.round_index <= 31:
            progress = self.round_index / 31
            target = 1.80 + 6.40 * (progress ** 1.10)
        else:
            extra_chapters = (self.round_index - 31) / 4.0
            target = 8.20 + 0.12 * extra_chapters
        if self.has_axiom("high_standards"):
            target += 0.5
        if self.is_boss_round:
            target -= BOSS_COMPLEXITY_BUDGET.get(self.current_boss_id, 0.25)
        return max(1.0, min(9.70, target))

    def variance_for_round(self):
        if self.round_index <= 31:
            progress = self.round_index / 31
            variance = 0.70 - 0.25 * progress
        else:
            extra_chapters = (self.round_index - 31) / 4.0
            variance = max(0.28, 0.45 - 0.012 * extra_chapters)
        if self.has_axiom("narrow_definition"):
            variance *= 0.60
        return variance

    def base_time_for_round(self):
        if self.round_index <= 31:
            progress = self.round_index / 31
            base = 50.0 - 28.0 * progress
        else:
            extra_chapters = (self.round_index - 31) / 4.0
            base = max(14.0, 22.0 - 0.45 * extra_chapters)
        if self.has_axiom("long_game"):
            base += min(8.0, 0.5 * self.completed_chapters)
        return base

    def _familiarity_bias(self):
        if self.has_axiom("familiar_ground") and not self.has_axiom("deep_cut"):
            return "familiar"
        if self.has_axiom("deep_cut") and not self.has_axiom("familiar_ground"):
            return "obscure"
        return None

    def start_round(self):
        if self.round_index >= self.CHAPTERS * self.WORDS_PER_CHAPTER and not self.endless:
            self.status = "won"
            return

        target = self.target_for_round()
        variance = self.variance_for_round()
        word = self.bank.choose(
            target, variance, self.used_families, self.rng,
            familiarity_bias=self._familiarity_bias(),
        )
        self.used_families.add(word.family_id)

        boss_id = self.current_boss_id if self.is_boss_round else None
        initial = 18.0 if boss_id == "deadline" else self.base_time_for_round()
        initial += self.difficulty_def.time_delta
        if self.has_axiom("countermeasure") and boss_id:
            initial += 4.0
        if self.has_axiom("grace_period"):
            initial += 4
        if self.has_axiom("overtime"):
            initial += 3
        if self.has_axiom("sharp_deadline"):
            initial -= 3
        if self.has_axiom("archive"):
            initial -= 3
        initial += effects.starting_time_delta(self, word, boss_id)
        if self.has_glyph("deadline_extension") and initial < 24.0:
            initial += 6.0
        initial = max(8.0, initial)
        self.next_word_time_bonus = 0.0

        max_mistakes = 6
        if self.has_axiom("margin_error"):
            max_mistakes += 1
        if self.has_axiom("boss_insurance") and boss_id:
            max_mistakes += 1
        if self.has_glyph("war_chest") and boss_id and self.points >= 2500:
            max_mistakes += 1
        if self.has_axiom("archive"):
            max_mistakes -= 1
        if self.has_glyph("margin_note"):
            max_mistakes += 1
        if self.has_glyph("glass_cannon"):
            max_mistakes -= 1
        if boss_id == "minimalist":
            penalty = 1 if self.has_axiom("countermeasure") else 2
            max_mistakes -= penalty
        max_mistakes = max(2, max_mistakes)
        cap_ceiling = max_mistakes
        if boss_id == "executioner":
            max_mistakes = min(cap_ceiling, 4 if self.has_axiom("countermeasure") else 3)

        self.round = RoundState(word, target, variance, initial, initial, max_mistakes, boss_id,
                                mistake_cap_ceiling=cap_ceiling)
        if boss_id == "censor":
            self.round.censored_letter = self.rng.choice(sorted(set(word.word)))
        if boss_id == "forbidden":
            self.round.forbidden_letter = self.rng.choice(sorted(set(word.word)))
        self.round.points_at_start = self.points
        self.status = "boss_ready" if boss_id else "playing"
        self._dispatch("round_started", {})

    def enter_boss(self):
        if self.status == "boss_ready" and self.round and self.round.boss_id:
            self.status = "playing"
            return True
        return False

    def _dispatch(self, event, ctx):
        fn = getattr(effects, f"on_{event}", None)
        if fn:
            fn(self, ctx)

    def add_time(self, amount):
        if self.round and not self.round.solved and not self.round.failed:
            self.round.remaining_time = min(self.round.initial_time + 12.0, self.round.remaining_time + amount)

    def _eliminate_absent(self, count=1):
        if not self.round:
            return []
        absent = list(ALPHABET - set(self.round.word.word) - self.round.guessed_letters - self.round.eliminated_letters)
        self.rng.shuffle(absent)
        picked = absent[:count]
        self.round.eliminated_letters.update(picked)
        return picked

    def tick(self, dt):
        if self.status != "playing" or not self.round:
            return None
        r = self.round
        r.elapsed += dt
        r.remaining_time -= dt

        if (self.has_glyph("reserve_ink") and not r.reserve_ink_triggered
                and r.remaining_time <= r.initial_time * 0.25):
            r.reserve_ink_triggered = True
            r.max_mistakes += 1
            r.last_message = "Reserve Ink grants +1 mistake capacity."

        if (self.has_glyph("pressure_notes") and not r.pressure_notes_triggered
                and r.remaining_time <= r.initial_time * 0.50):
            r.pressure_notes_triggered = True
            picked = self._eliminate_absent(3)
            if picked:
                r.last_message = f"Pressure Notes crossed out {len(picked)} absent letters."

        if r.remaining_time <= 0:
            if (self.has_glyph("second_draft")
                    and self.glyph_state.get("second_draft_chapter") != self.chapter
                    and r.mistakes + 1 < r.max_mistakes):
                self.glyph_state["second_draft_chapter"] = self.chapter
                r.mistakes += 1
                r.attempted_mistakes += 1
                r.remaining_time = 8.0
                r.last_message = "Second Draft: +1 mistake, timer restored to 8 seconds."
                return {"rescued": True, "source": "second_draft"}
            r.remaining_time = 0
            return self._fail("Time expired.")
        return None

    def can_guess_letter(self, ch):
        if self.status != "playing" or not self.round:
            return False, "No active word."
        ch = ch.lower()
        if ch not in ALPHABET:
            return False, "Enter a letter A-Z."
        if ch in self.round.guessed_letters or ch in self.round.eliminated_letters:
            return False, "That letter is already accounted for."
        mute_duration = 8.0 if self.has_axiom("countermeasure") else 10.0
        if self.round.boss_id == "mute" and ch in VOWELS and self.round.elapsed < mute_duration:
            return False, f"The Mute blocks vowels for {mute_duration - self.round.elapsed:.1f}s more."
        if self.round.boss_id == "forbidden" and ch == self.round.forbidden_letter:
            return False, f"The Forbidden blocks {ch.upper()} from direct guesses."
        if self.round.boss_id == "alternator" and self.round.letter_guess_sequence:
            prev = self.round.letter_guess_sequence[-1]
            if (prev in VOWELS) == (ch in VOWELS):
                need = "a consonant" if prev in VOWELS else "a vowel"
                return False, f"The Alternator requires {need} next."
        return True, ""

    def guess_letter(self, ch):
        ok, msg = self.can_guess_letter(ch)
        if not ok:
            if self.round:
                self.round.last_message = msg
            return {"ok": False, "message": msg}
        return self._guess_letter_internal(ch.lower(), auto=False)

    def _guess_letter_internal(self, ch, auto=False):
        r = self.round
        if ch in r.guessed_letters:
            return {"ok": False, "message": "Already guessed."}
        r.guessed_letters.add(ch)
        r.reveal_times[ch] = r.elapsed
        if not auto:
            r.letter_guess_sequence.append(ch)
            if r.boss_id == "clockmaker":
                penalty = 1.2 if self.has_axiom("countermeasure") else 1.5
                r.remaining_time = max(0.0, r.remaining_time - penalty)
        count = r.word.word.count(ch)
        if count:
            if auto:
                r.auto_revealed_letters += 1
            if not auto:
                r.total_letter_guesses += 1
                r.correct_letter_guesses += 1
            r.last_message = f"{ch.upper()} appears {count} time{'s' if count != 1 else ''}."
            if r.boss_id == "executioner" and not auto and r.max_mistakes < r.mistake_cap_ceiling:
                r.max_mistakes += 1
                r.last_message += " The Executioner restores +1 mistake capacity."
            if r.boss_id == "redactor":
                # A correct read gives the player a brief chance to reconstruct the
                # whole pattern instead of forcing perfect long-term memorization.
                for revealed in r.guessed_letters:
                    if revealed in r.word.word:
                        r.reveal_times[revealed] = r.elapsed
            self._dispatch("correct_letter", {"letter": ch, "count": count, "auto": auto})
            if set(r.word.word) <= r.guessed_letters:
                return self._solve("letters")
            return {"ok": True, "correct": True, "count": count}
        if auto:
            return {"ok": False, "message": "Auto reveal selected absent letter."}
        r.total_letter_guesses += 1
        r.wrong_letter_guesses += 1
        r.wrong_letter_sequence.append(ch)
        r.consonant_streak = 0
        wrong_cost = 1 + (1 if self.has_glyph("blind_faith") and r.total_letter_guesses == 1 else 0)
        self._apply_wrong_mistakes(wrong_cost, f"{ch.upper()} is not in the word.", kind="letter")
        return {"ok": True, "correct": False}

    def _apply_wrong_mistakes(self, amount, message, kind="action"):
        r = self.round
        attempted = amount
        r.attempted_mistakes += attempted
        r.wrong_actions += 1
        if self.has_glyph("pencil_eraser") and not r.eraser_used:
            r.eraser_used = True
            amount = max(0, amount - 1)
            message += " Pencil Eraser softened the mistake."
        if (amount and self.has_glyph("lifeline")
                and self.glyph_state.get("lifeline_chapter") != self.chapter
                and r.mistakes + amount >= r.max_mistakes):
            self.glyph_state["lifeline_chapter"] = self.chapter
            amount = max(0, r.max_mistakes - 1 - r.mistakes)
            message += " Lifeline leaves you at one mistake remaining."
        if amount:
            r.mistakes += amount
            if r.boss_id == "editor":
                per_mistake = 3.2 if self.has_axiom("countermeasure") else 4.0
                r.remaining_time = max(0, r.remaining_time - per_mistake * amount)
            if r.boss_id == "taxman":
                per = 100 if self.has_axiom("countermeasure") else 125
                loss = min(self.points, per * amount)
                self.points -= loss
                message += f" The Taxman took {loss} Points."
        r.last_message = message
        self._dispatch("wrong_action", {"amount": amount, "attempted": attempted, "kind": kind})
        if r.mistakes >= r.max_mistakes or r.remaining_time <= 0:
            self._fail("Too many mistakes." if r.mistakes >= r.max_mistakes else "Time expired.")

    def guess_word(self, text):
        if self.status != "playing" or not self.round:
            return {"ok": False, "message": "No active word."}
        guess = "".join(c for c in text.lower().strip() if c.isalpha())
        if not guess:
            return {"ok": False, "message": "Type a word first."}
        if self.round.boss_id == "examiner":
            msg = "The Examiner disables full-word guesses. Reveal the letters to solve."
            self.round.last_message = msg
            return {"ok": False, "message": msg}
        if self.round.boss_id == "gatekeeper" and self.round.correct_letter_guesses < 3:
            left = 3 - self.round.correct_letter_guesses
            msg = f"The Gatekeeper needs {left} more manual correct letter guess{'es' if left != 1 else ''}."
            self.round.last_message = msg
            return {"ok": False, "message": msg}
        self.round.full_word_attempts += 1
        if self.round.boss_id == "perfectionist" and not (set(self.round.word.word) <= self.round.guessed_letters):
            msg = "The Perfectionist blocks full-word guesses until every unique letter is revealed."
            self.round.last_message = msg
            return {"ok": False, "message": msg}
        if guess == self.round.word.word:
            return self._solve("full_word")

        self.round.wrong_full_word_guesses += 1
        cost = 2
        if self.has_glyph("gambler"):
            cost += 1
        if self.has_glyph("final_answer"):
            cost += 2
        if self.has_glyph("spellcheck"):
            cost -= 1
        if self.has_axiom("safe_answer"):
            cost -= 1
        cost = max(1, cost)
        self._apply_wrong_mistakes(cost, f"{guess.upper()} is incorrect. Full-word guesses cost {cost} mistake{'s' if cost != 1 else ''}.", kind="full_word")
        return {"ok": True, "correct": False}

    def _solve(self, method):
        r = self.round
        if r.solved or r.failed:
            return None
        if method == "full_word" and self.has_glyph("spellcheck"):
            r.remaining_time = min(r.initial_time + 12.0, r.remaining_time + 3.0)
        r.solved = True
        r.solve_method = method

        base = int(round(r.word.complexity * 100))
        mistake_penalty = int(round(base * min(0.60, 0.12 * r.mistakes)))
        speed_ratio = r.remaining_time / max(1.0, r.initial_time)
        speed_bonus = int(round(base * 0.25 * max(0.0, min(1.0, speed_ratio))))
        bonus = r.bonus_points + effects.solve_bonus(self, method)
        mult = effects.score_multiplier(self)
        subtotal = max(0, base - mistake_penalty + speed_bonus + bonus)
        total = max(1, int(round(subtotal * mult)))

        self.points += total
        self.total_earned += total
        self.last_result = {
            "word": r.word.word.upper(),
            "complexity": r.word.complexity,
            "raw_complexity": r.word.raw_complexity,
            "base": base,
            "mistake_penalty": mistake_penalty,
            "speed_bonus": speed_bonus,
            "glyph_bonus": bonus,
            "multiplier": mult,
            "total": total,
            "mistakes": r.mistakes,
            "remaining_time": r.remaining_time,
            "initial_time": r.initial_time,
            "target": r.target_complexity,
        }
        effects.after_solve(self)
        stats = self.run_stats
        stats["words_solved"] = int(stats.get("words_solved", 0)) + 1
        if r.boss_id:
            stats["bosses_defeated"] = int(stats.get("bosses_defeated", 0)) + 1
        if r.mistakes == 0:
            stats["perfect_words"] = int(stats.get("perfect_words", 0)) + 1
        if method == "full_word":
            stats["full_word_solves"] = int(stats.get("full_word_solves", 0)) + 1
        stats["highest_complexity_solved"] = max(float(stats.get("highest_complexity_solved", 0.0)), r.word.complexity)
        fastest = stats.get("fastest_solve")
        stats["fastest_solve"] = r.elapsed if fastest is None else min(float(fastest), r.elapsed)
        stats["attempted_mistakes"] = int(stats.get("attempted_mistakes", 0)) + r.attempted_mistakes
        stats["auto_reveals"] = int(stats.get("auto_reveals", 0)) + r.auto_revealed_letters
        telemetry.record_round(self, "solved")
        self.status = "glyph_choice"
        self.glyph_rerolls = 0
        self._roll_glyph_offers()
        return {"solved": True, "score": total}

    def _fail(self, reason):
        if not self.round or self.round.failed:
            return None
        self.round.failed = True
        self.round.last_message = reason
        telemetry.record_round(self, "failed", reason)
        telemetry.record_run_event(self, "endless_loss" if self.endless else "loss")
        self.status = "lost"
        return {"failed": True, "reason": reason}

    def visible_word(self):
        if not self.round:
            return ""
        out = []
        fade = 12.0 if self.has_axiom("countermeasure") else 10.0
        blackout = False
        if self.round.boss_id == "blackout" and self.round.elapsed >= 5.5:
            phase = self.round.elapsed % 8.0
            duration = 2.0 if self.has_axiom("countermeasure") else 2.5
            blackout = phase >= 8.0 - duration
        for ch in self.round.word.word:
            guessed = ch in self.round.guessed_letters
            if guessed and blackout:
                out.append("·")
            elif (guessed and self.round.boss_id == "censor" and ch == self.round.censored_letter):
                out.append("■")
            elif guessed and self.round.boss_id == "redactor":
                reveal_time = self.round.reveal_times.get(ch, self.round.elapsed)
                show = self.round.elapsed - reveal_time <= fade
                out.append(ch.upper() if show else "·")
            else:
                out.append(ch.upper() if guessed else "_")
        return " ".join(out)

    def complexity_display(self):
        if not self.round:
            return ""
        if self.has_axiom("open_book"):
            return f"Exact Complexity: {self.round.word.complexity:.2f}"
        lo = max(1.0, self.round.target_complexity - self.round.variance)
        hi = min(10.0, self.round.target_complexity + self.round.variance)
        return f"Expected Complexity: {lo:.2f}–{hi:.2f}"

    def round_info_text(self):
        if not self.round:
            return ""
        bits = []
        if self.has_glyph("lexicographer"):
            bits.append(f"Part of speech: {self.round.word.pos_tags or 'unknown'}")
        if self.has_glyph("vowel_census"):
            bits.append(f"Unique vowels: {len(set(self.round.word.word) & VOWELS)}")
        bits.extend(getattr(self.round, "extra_clues", []))
        if self.round.boss_id == "forbidden" and self.round.forbidden_letter:
            bits.append(f"Forbidden letter: {self.round.forbidden_letter.upper()}")
        if self.round.boss_id == "gatekeeper":
            bits.append(f"Gatekeeper: {min(3, self.round.correct_letter_guesses)}/3 manual correct")
        return "  •  ".join(bits)

    def _weighted_glyph_pick(self, excluded):
        candidates = [g for g in GLYPHS.values() if g.id not in excluded]
        weights = []
        for g in candidates:
            weight = RARITY_WEIGHTS[g.rarity]
            if self.has_axiom("deep_shelves"):
                if g.rarity == "Rare":
                    weight *= 2.0
                elif g.rarity == "Uncommon":
                    weight *= 1.15
            weights.append(weight)
        return self.rng.choices(candidates, weights=weights, k=1)[0].id

    def _roll_glyph_offers(self):
        count = self.difficulty_def.glyph_choices + (1 if self.has_axiom("three_choices") else 0)
        offers = []
        excluded = set(self.glyphs)
        for _ in range(count):
            gid = self._weighted_glyph_pick(excluded | set(offers))
            offers.append(gid)
        self.glyph_offers = offers

    def glyph_reroll_cost(self):
        if self.has_axiom("fresh_ink") and self.fresh_ink_available:
            return 0
        growth = 1.75 if not self.has_axiom("cheap_revision") else 1.3375
        cost = int(round(100 * (growth ** self.glyph_rerolls)))
        if self.has_glyph("frugal"):
            cost = int(round(cost * 0.55))
        return max(0, cost)

    def reroll_glyphs(self):
        if self.status != "glyph_choice":
            return False, "Not choosing Glyphs."
        cost = self.glyph_reroll_cost()
        if self.points < cost:
            return False, "Not enough Points."
        offers_before = list(self.glyph_offers)
        points_before = self.points
        glyphs_before = list(self.glyphs)
        axioms_before = list(self.axioms)
        self.points -= cost
        if cost > 0 and self.has_glyph("reinvestment"):
            self.next_word_time_bonus = min(8.0, self.next_word_time_bonus + 2.0)
        if cost == 0 and self.has_axiom("fresh_ink"):
            self.fresh_ink_available = False
        self.glyph_rerolls += 1
        self._roll_glyph_offers()
        refunded = 0
        if cost > 0 and self.has_glyph("loaded_dice") and self.rng.random() < 0.30:
            self.points += cost
            refunded = cost
        telemetry.record_decision(
            self, "glyph", "reroll",
            offers_before=offers_before, offers_after=list(self.glyph_offers),
            cost=cost, points_before=points_before,
            glyphs_before=glyphs_before, axioms_before=axioms_before,
        )
        if refunded:
            return True, f"Loaded Dice refunded the {cost} Point reroll."
        return True, f"Rerolled for {cost} Points."

    def _init_glyph_state(self, gid):
        if gid == "perfect_copy":
            self.glyph_state.setdefault("perfect_copy_mult", 1.0)
        elif gid == "thesaurus":
            self.glyph_state.setdefault("thesaurus_pages", 0)
        elif gid == "deadline_writer":
            self.glyph_state.setdefault("deadline_writer_time", 0.0)
        elif gid == "snowball":
            self.glyph_state.setdefault("snowball_streak", 0)
        elif gid == "rolling_press":
            self.glyph_state.setdefault("rolling_press_time", 0.0)
        elif gid == "index_cards":
            self.glyph_state.setdefault("index_cards_words", 0)

    def _clear_glyph_state(self, gid):
        key = {
            "perfect_copy": "perfect_copy_mult",
            "thesaurus": "thesaurus_pages",
            "deadline_writer": "deadline_writer_time",
            "snowball": "snowball_streak",
            "rolling_press": "rolling_press_time",
            "index_cards": "index_cards_words",
        }.get(gid)
        if key:
            self.glyph_state.pop(key, None)

    def glyph_description(self, gid):
        base = GLYPHS[gid].description
        if gid == "perfect_copy" and gid in self.glyphs:
            return f"{base}  Current: x{float(self.glyph_state.get('perfect_copy_mult', 1.0)):.2f}."
        if gid == "thesaurus" and gid in self.glyphs:
            pages = int(self.glyph_state.get("thesaurus_pages", 0))
            return f"{base}  Current: {pages} page{'s' if pages != 1 else ''}; {min(4, pages // 3)} extra cross-outs."
        if gid == "deadline_writer" and gid in self.glyphs:
            return f"{base}  Current: +{float(self.glyph_state.get('deadline_writer_time', 0.0)):.2f}s."
        if gid == "snowball" and gid in self.glyphs:
            return f"{base}  Current streak: {int(self.glyph_state.get('snowball_streak', 0))}."
        if gid == "rolling_press" and gid in self.glyphs:
            return f"{base}  Current: +{float(self.glyph_state.get('rolling_press_time', 0.0)):.2f}s."
        if gid == "index_cards" and gid in self.glyphs:
            solved = int(self.glyph_state.get("index_cards_words", 0))
            return f"{base}  Current: {solved} solved; {min(4, solved // 4)} extra cross-outs."
        return base

    def take_glyph(self, offer_index, replace_index=None):
        if self.status != "glyph_choice" or not (0 <= offer_index < len(self.glyph_offers)):
            return False, "Invalid Glyph selection."
        gid = self.glyph_offers[offer_index]
        offers_before = list(self.glyph_offers)
        points_before = self.points
        glyphs_before = list(self.glyphs)
        axioms_before = list(self.axioms)
        had_curator = self.has_glyph("curator")
        replaced = ""
        if len(self.glyphs) < self.glyph_slots():
            self.glyphs.append(gid)
            action = "take"
        else:
            if replace_index is None or not (0 <= replace_index < len(self.glyphs)):
                return False, "Choose a Glyph to replace."
            old = self.glyphs[replace_index]
            replaced = old
            if self.has_glyph("liquidation"):
                old_rarity = GLYPHS[old].rarity
                gain = 150 if old_rarity == "Common" else 300 if old_rarity == "Uncommon" else 500
                self.points += gain
                self.total_earned += gain
            self._clear_glyph_state(old)
            self.glyphs[replace_index] = gid
            action = "replace"
        self._init_glyph_state(gid)

        if had_curator:
            rarity = GLYPHS[gid].rarity
            gain = 125 if rarity == "Common" else 250 if rarity == "Uncommon" else 550
            if gain:
                self.points += gain
                self.total_earned += gain

        telemetry.record_decision(
            self, "glyph", action,
            offers_before=offers_before, selected_id=gid, replaced_id=replaced,
            points_before=points_before, glyphs_before=glyphs_before,
            axioms_before=axioms_before,
        )
        self._advance_after_glyph()
        return True, "Glyph taken."

    def skip_glyph(self):
        if self.status == "glyph_choice":
            offers_before = list(self.glyph_offers)
            points_before = self.points
            glyphs_before = list(self.glyphs)
            axioms_before = list(self.axioms)
            if self.has_glyph("clean_copy"):
                self.points += 500
                self.total_earned += 500
            telemetry.record_decision(
                self, "glyph", "skip",
                offers_before=offers_before, points_before=points_before,
                glyphs_before=glyphs_before, axioms_before=axioms_before,
            )
            self._advance_after_glyph()

    def trash_glyph(self, index):
        if not (0 <= index < len(self.glyphs)):
            return False, "Invalid Glyph."
        points_before = self.points
        glyphs_before = list(self.glyphs)
        axioms_before = list(self.axioms)
        gid = self.glyphs.pop(index)
        self._clear_glyph_state(gid)
        refund = 0
        if self.has_axiom("recycling"):
            refund = RARITY_TRASH_VALUE[GLYPHS[gid].rarity]
            self.points += refund
        telemetry.record_decision(
            self, "glyph", "trash", selected_id=gid, refund=refund,
            points_before=points_before, glyphs_before=glyphs_before,
            axioms_before=axioms_before,
        )
        return True, f"Trashed {GLYPHS[gid].name}" + (f" for {refund} Points." if refund else ".")

    def _advance_after_glyph(self):
        was_boss = self.is_boss_round
        if was_boss and self.has_axiom("chapter_bonus"):
            self.points += 500
            self.total_earned += 500
        if was_boss and self.has_axiom("fresh_ink"):
            self.fresh_ink_available = True

        self.round_index += 1
        if self.round_index >= self.CHAPTERS * self.WORDS_PER_CHAPTER and not self.endless:
            self.status = "won"
            self.final_boss_axiom_pending = was_boss
            telemetry.record_run_event(self, "main_win")
            return
        if was_boss:
            self.status = "axiom_choice"
            self.axiom_rerolled = False
            self._roll_axiom_offers()
        else:
            self.start_round()

    def _roll_axiom_offers(self):
        available = [a.id for a in AXIOMS.values() if a.id not in self.axioms]
        self.rng.shuffle(available)
        count = self.difficulty_def.axiom_choices + (1 if self.has_axiom("library_card") else 0)
        self.axiom_offers = available[:count]

    def reroll_axioms(self):
        if self.status != "axiom_choice" or not self.has_axiom("second_opinion"):
            return False, "Second Opinion is required."
        if self.axiom_rerolled:
            return False, "Axiom selection already rerolled this boss."
        if self.points < 500:
            return False, "Not enough Points."
        offers_before = list(self.axiom_offers)
        points_before = self.points
        glyphs_before = list(self.glyphs)
        axioms_before = list(self.axioms)
        self.points -= 500
        self.axiom_rerolled = True
        self._roll_axiom_offers()
        telemetry.record_decision(
            self, "axiom", "reroll",
            offers_before=offers_before, offers_after=list(self.axiom_offers),
            cost=500, points_before=points_before,
            glyphs_before=glyphs_before, axioms_before=axioms_before,
        )
        return True, "Axioms rerolled."

    def take_axiom(self, offer_index):
        if self.status != "axiom_choice" or not (0 <= offer_index < len(self.axiom_offers)):
            return False, "Invalid Axiom selection."
        aid = self.axiom_offers[offer_index]
        offers_before = list(self.axiom_offers)
        points_before = self.points
        glyphs_before = list(self.glyphs)
        axioms_before = list(self.axioms)
        self.axioms.append(aid)
        if aid == "deep_pockets":
            self.points += 1800
            self.total_earned += 1800
        if aid == "fresh_ink":
            self.fresh_ink_available = True
        telemetry.record_decision(
            self, "axiom", "take",
            offers_before=offers_before, selected_id=aid,
            points_before=points_before, glyphs_before=glyphs_before,
            axioms_before=axioms_before,
        )
        self.final_boss_axiom_pending = False
        self.start_round()
        return True, "Axiom taken."

    def continue_without_axiom(self):
        if self.status == "axiom_choice" and not self.axiom_offers:
            self.final_boss_axiom_pending = False
            self.start_round()
            return True
        return False

    def continue_endless(self):
        if self.status != "won" or self.round_index < self.CHAPTERS * self.WORDS_PER_CHAPTER:
            return False
        self.endless = True
        telemetry.record_run_event(self, "endless_entered")
        if self.final_boss_axiom_pending:
            self.status = "axiom_choice"
            self.axiom_rerolled = False
            self._roll_axiom_offers()
        else:
            self.start_round()
        return True


    @staticmethod
    def _encode_value(value):
        if isinstance(value, set):
            return {"__type__": "set", "items": [GameState._encode_value(v) for v in sorted(value)]}
        if isinstance(value, tuple):
            return {"__type__": "tuple", "items": [GameState._encode_value(v) for v in value]}
        if isinstance(value, list):
            return [GameState._encode_value(v) for v in value]
        if isinstance(value, dict):
            return {str(k): GameState._encode_value(v) for k, v in value.items()}
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise TypeError(f"Unsupported save value: {type(value)!r}")

    @staticmethod
    def _decode_value(value):
        if isinstance(value, list):
            return [GameState._decode_value(v) for v in value]
        if isinstance(value, dict):
            kind = value.get("__type__")
            if kind == "set":
                return set(GameState._decode_value(v) for v in value.get("items", []))
            if kind == "tuple":
                return tuple(GameState._decode_value(v) for v in value.get("items", []))
            return {k: GameState._decode_value(v) for k, v in value.items()}
        return value

    def can_save(self):
        return self.status in {"glyph_choice", "axiom_choice", "boss_ready", "won"}

    def to_save_dict(self):
        if not self.can_save():
            raise ValueError("Runs can only be saved while the timer is paused.")
        attrs = {}
        for key, value in self.__dict__.items():
            if key in {"bank", "rng", "round", "data_dir"}:
                continue
            attrs[key] = self._encode_value(value)
        round_data = None
        if self.round is not None:
            round_data = {
                "word": self.round.word.word,
                "attrs": {
                    key: self._encode_value(value)
                    for key, value in self.round.__dict__.items()
                    if key != "word"
                },
            }
        return {
            "attrs": attrs,
            "rng_state": self._encode_value(self.rng.getstate()),
            "round": round_data,
        }

    @classmethod
    def from_save_dict(cls, bank: WordBank, payload: dict, data_dir=None, telemetry_enabled=True):
        attrs = payload.get("attrs", {})
        difficulty = attrs.get("difficulty", "medium")
        seed = int(attrs.get("seed", 1))
        game = cls(bank, seed=seed, difficulty=difficulty, data_dir=data_dir,
                   telemetry_enabled=telemetry_enabled, bank_id=attrs.get("bank_id", getattr(bank, "bank_id", "standard")))
        for key, value in attrs.items():
            if key in {"bank", "rng", "round", "data_dir"}:
                continue
            setattr(game, key, cls._decode_value(value))
        game.data_dir = data_dir
        game.telemetry_enabled = bool(telemetry_enabled)
        state = cls._decode_value(payload.get("rng_state"))
        if state:
            game.rng.setstate(state)
        rdata = payload.get("round")
        if rdata:
            word_text = rdata.get("word", "")
            word = bank.by_word.get(word_text)
            if word is None:
                raise ValueError(f"Saved word {word_text!r} is not present in this word bank.")
            decoded = {k: cls._decode_value(v) for k, v in rdata.get("attrs", {}).items()}
            required = {
                "target_complexity": decoded.pop("target_complexity"),
                "variance": decoded.pop("variance"),
                "initial_time": decoded.pop("initial_time"),
                "remaining_time": decoded.pop("remaining_time"),
                "max_mistakes": decoded.pop("max_mistakes"),
                "boss_id": decoded.pop("boss_id", None),
            }
            round_state = RoundState(word=word, **required)
            for key, value in decoded.items():
                setattr(round_state, key, value)
            game.round = round_state
        else:
            game.round = None
        return game

    def record_difficulty_feedback(self, rating: str):
        return False, "Manual ratings were removed in v0.4; automatic telemetry remains active in v1.1; word performance is logged automatically."
