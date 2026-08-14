from __future__ import annotations
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WordEntry:
    word: str
    complexity: float          # v0.8 telemetry-informed gameplay score
    raw_complexity: float      # v0.2 legacy displayed score (for comparison)
    model_complexity: float    # v0.5 structural score before legacy soft-blend
    v05_complexity: float      # displayed score used in v0.5-v0.7
    band: str
    family_id: str
    length: int
    pos_tags: str
    familiarity_score: float
    solver_misses: int = 0
    solver_guesses: int = 0
    solver_miss_difficulty: float = 0.0
    solver_guess_difficulty: float = 0.0
    ambiguity_difficulty: float = 0.0
    familiarity_difficulty: float = 0.0
    letter_rarity: float = 0.0
    ngram_rarity: float = 0.0
    vowel_oddity: float = 0.0
    length_difficulty: float = 0.0
    morphology_difficulty: float = 0.0
    repetition_difficulty: float = 0.0
    frequency_solver_misses: int = 0
    frequency_solver_guesses: int = 0
    frequency_complexity: float = 0.0



@dataclass(frozen=True)
class BankDef:
    id: str
    name: str
    description: str


BANKS = {
    b.id: b for b in [
        BankDef("standard", "Standard", "The full balanced lexicon, mixing familiar words with increasingly obscure and difficult spellings. This is the default Dead Letter experience."),
        BankDef("common_tongue", "Common Tongue", "Leans toward familiar, everyday vocabulary and cleaner spellings. Difficulty still rises normally, but the words tend to feel more recognizable."),
        BankDef("bookish", "Longform", "Leans toward longer, less-common vocabulary and denser spellings. Expect more elaborate words and fewer compact targets."),
        BankDef("quickfire", "Quickfire", "Favors compact words, especially short and mid-length targets. Less information per word can make even familiar vocabulary deceptively dangerous."),
        BankDef("labyrinth", "Labyrinth", "Favors unusual spelling, rare letters, awkward vowel structures and deceptive patterns. Built for players who want stranger Hangman puzzles."),
    ]
}


def _profile_score(entry: "WordEntry", bank_id: str) -> float:
    """Affinity score used to form broad themed banks from the same vetted lexicon."""
    fam = entry.familiarity_score
    length = entry.length
    if bank_id == "common_tongue":
        return 2.2 * fam - 0.06 * abs(length - 6) - 0.25 * entry.ngram_rarity
    if bank_id == "bookish":
        noun_adj = 0.15 if ("NN" in entry.pos_tags or "JJ" in entry.pos_tags) else 0.0
        return 1.4 * (1.0 - fam) + 0.045 * length + 0.35 * entry.ngram_rarity + noun_adj
    if bank_id == "quickfire":
        compact = 1.0 - min(1.0, abs(length - 5) / 12.0)
        return 1.5 * compact + 0.45 * fam + 0.25 * (1.0 - entry.repetition_difficulty)
    if bank_id == "labyrinth":
        return (0.65 * entry.ngram_rarity + 0.55 * entry.letter_rarity
                + 0.45 * entry.vowel_oddity + 0.35 * entry.ambiguity_difficulty
                + 0.25 * (1.0 - fam))
    return 0.0


class WordBank:
    def __init__(self, csv_path: str | Path, bank_id: str = "standard"):
        self.path = Path(csv_path)
        self.bank_id = bank_id if bank_id in BANKS else "standard"
        self.words: list[WordEntry] = []
        with self.path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                w = row["word"].strip().lower()
                if not w.isalpha() or not 3 <= len(w) <= 15:
                    continue
                pos = row.get("pos_tags", "")
                tags = {x.strip() for x in pos.split(",") if x.strip()}
                # Proper-noun-only entries are a bad fit for default Hangman.
                if tags and tags <= {"NNP", "NNPS"}:
                    continue

                def fv(name: str, default: float = 0.0) -> float:
                    try:
                        return float(row.get(name, default) or default)
                    except (TypeError, ValueError):
                        return default

                def iv(name: str, default: int = 0) -> int:
                    try:
                        return int(float(row.get(name, default) or default))
                    except (TypeError, ValueError):
                        return default

                complexity = fv("complexity", 5.0)
                raw = fv("raw_complexity", complexity)
                model = fv("model_complexity", complexity)
                familiarity = fv("familiarity_score", 0.5)
                self.words.append(WordEntry(
                    word=w,
                    complexity=round(max(1.0, min(10.0, complexity)), 2),
                    raw_complexity=raw,
                    model_complexity=model,
                    v05_complexity=fv("v05_complexity", complexity),
                    band=row.get("band", ""),
                    family_id=row.get("family_id", w) or w,
                    length=iv("length", len(w)),
                    pos_tags=pos,
                    familiarity_score=familiarity,
                    solver_misses=iv("solver_misses"),
                    solver_guesses=iv("solver_guesses"),
                    solver_miss_difficulty=fv("solver_miss_difficulty"),
                    solver_guess_difficulty=fv("solver_guess_difficulty"),
                    ambiguity_difficulty=fv("ambiguity_difficulty"),
                    familiarity_difficulty=fv("familiarity_difficulty"),
                    letter_rarity=fv("letter_rarity"),
                    ngram_rarity=fv("ngram_rarity"),
                    vowel_oddity=fv("vowel_oddity"),
                    length_difficulty=fv("length_difficulty"),
                    morphology_difficulty=fv("morphology_difficulty"),
                    repetition_difficulty=fv("repetition_difficulty"),
                    frequency_solver_misses=iv("frequency_solver_misses"),
                    frequency_solver_guesses=iv("frequency_solver_guesses"),
                    frequency_complexity=fv("frequency_complexity", complexity),
                ))
        if not self.words:
            raise ValueError(f"No playable words loaded from {self.path}")

        # The four themed banks remain deliberately large (~28k each) and may
        # overlap. They are alternate curated lenses on the same vetted lexicon,
        # not tiny novelty lists that would become repetitive in Endless.
        if self.bank_id != "standard":
            ranked = sorted(self.words, key=lambda w: (_profile_score(w, self.bank_id), w.word), reverse=True)
            self.words = ranked[: min(28000, len(ranked))]

        self.by_word = {w.word: w for w in self.words}

    def choose(
        self,
        target: float,
        variance: float,
        used_families: set[str],
        rng: random.Random,
        familiarity_bias: str | None = None,
    ) -> WordEntry:
        low, high = max(1.0, target - variance), min(10.0, target + variance)
        pool = [w for w in self.words if w.family_id not in used_families and low <= w.complexity <= high]

        # Widen gently if a future filtered bank leaves a sparse band.
        widen = variance
        while not pool and widen < 3.0:
            widen += 0.25
            low, high = max(1.0, target - widen), min(10.0, target + widen)
            pool = [w for w in self.words if w.family_id not in used_families and low <= w.complexity <= high]
        if not pool:
            pool = [w for w in self.words if w.family_id not in used_families]
        if not pool:
            raise RuntimeError("Word bank exhausted: no unused word families remain.")

        # Complexity proximity is dominant. Familiarity is a soft tie-breaker,
        # not an alternate difficulty system. v0.5 deliberately reduced the
        # direct familiarity weight inside Complexity after telemetry showed that
        # common short words can still be brutal Hangman targets.
        desired_familiarity = max(0.38, min(0.88, 0.90 - 0.065 * target))
        weights = []
        for w in pool:
            proximity = 1.0 / (0.12 + abs(w.complexity - target))
            natural = math.exp(-0.90 * abs(w.familiarity_score - desired_familiarity))
            if familiarity_bias == "familiar":
                bias = 0.45 + 1.55 * w.familiarity_score
            elif familiarity_bias == "obscure":
                bias = 0.45 + 1.55 * (1.0 - w.familiarity_score)
            else:
                bias = natural
            weights.append(proximity * bias)
        return rng.choices(pool, weights=weights, k=1)[0]
