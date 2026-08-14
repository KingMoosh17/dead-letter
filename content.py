from dataclasses import dataclass


@dataclass(frozen=True)
class GlyphDef:
    id: str
    name: str
    rarity: str
    description: str
    category: str = "General"


@dataclass(frozen=True)
class AxiomDef:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class BossDef:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class DifficultyDef:
    id: str
    name: str
    time_delta: float
    glyph_choices: int
    axiom_choices: int
    description: str


DIFFICULTIES = {
    d.id: d for d in [
        DifficultyDef("easy", "Easy", 10.0, 3, 3,
                      "+10 seconds per word, with three Glyph and three Axiom options."),
        DifficultyDef("medium", "Medium", 0.0, 2, 2,
                      "Standard timing with two Glyph and two Axiom options."),
        DifficultyDef("hard", "Hard", -6.0, 1, 1,
                      "-6 seconds per word, with one Glyph and one Axiom option."),
    ]
}


# v0.4 balance philosophy:
# - Common Glyphs should be noticeable on most rounds, not microscopic bonuses.
# - Narrow triggers receive much larger payoffs.
# - Blanket survivability has a cost or higher rarity so it is not an auto-pick.
# - Information and economy effects are strong enough to compete with raw time/lives.
# - Persistent scalers have room to matter in Endless.
GLYPHS = {
    g.id: g for g in [
        # ------------------------------------------------------------------
        # Accuracy / recovery
        # ------------------------------------------------------------------
        GlyphDef("pencil_eraser", "Pencil Eraser", "Rare",
                 "The first wrong action each word costs 1 fewer mistake, but every word starts with 3 fewer seconds.", "Accuracy"),
        GlyphDef("reserve_ink", "Reserve Ink", "Uncommon",
                 "When the timer first drops below 25%, gain +1 mistake capacity for that word.", "Accuracy"),
        GlyphDef("spellcheck", "Spellcheck", "Uncommon",
                 "Wrong full-word guesses cost 1 fewer mistake. Correct full-word solves also restore 3 seconds before scoring.", "Accuracy"),
        GlyphDef("safety_net", "Safety Net", "Uncommon",
                 "The first time you fall to 1 remaining mistake, cross out 4 absent letters and gain 2 seconds.", "Accuracy"),
        GlyphDef("comeback", "Comeback", "Common",
                 "After a wrong guess, your next correct letter restores 7 seconds.", "Accuracy"),
        GlyphDef("proofreading", "Proofreading", "Common",
                 "Zero-mistake solves earn +400 Points and your next word starts with +2 seconds.", "Accuracy"),
        GlyphDef("margin_note", "Margin Note", "Rare",
                 "+1 mistake capacity every word, but all scores x0.88.", "Accuracy"),
        GlyphDef("recovery_room", "Recovery Room", "Uncommon",
                 "After your second charged mistake each word, immediately restore 6 seconds.", "Accuracy"),
        GlyphDef("glass_cannon", "Glass Cannon", "Rare",
                 "Start each word with 1 fewer mistake capacity; all scores x1.45.", "Risk"),
        GlyphDef("red_pen", "Red Pen", "Uncommon",
                 "Each wrong guess removes 2 extra seconds but adds +110 Points to that word's score.", "Risk"),

        # ------------------------------------------------------------------
        # Time
        # ------------------------------------------------------------------
        GlyphDef("momentum", "Momentum", "Common",
                 "Manual correct letter guesses restore 1.25 seconds, up to 7.5 seconds per word.", "Time"),
        GlyphDef("second_wind", "Second Wind", "Uncommon",
                 "The first correct guess each word that reveals 2+ copies restores 5 seconds.", "Time"),
        GlyphDef("stopwatch", "Stopwatch", "Common",
                 "Every 3rd manual correct letter guess restores 3.5 seconds.", "Time"),
        GlyphDef("echo", "Echo", "Common",
                 "Correct guesses revealing multiple copies restore 5 seconds.", "Time"),
        GlyphDef("hourglass", "Hourglass", "Uncommon",
                 "Start each word with +7 seconds, but all scores x0.90.", "Time"),
        GlyphDef("quick_study", "Quick Study", "Common",
                 "Your first two manual correct letter guesses each restore 4 seconds.", "Time"),
        GlyphDef("chain_reaction", "Chain Reaction", "Uncommon",
                 "Every 3 consecutive manual correct letter guesses restores 4.5 seconds.", "Time"),
        GlyphDef("vowel_clock", "Vowel Clock", "Common",
                 "Manual correct vowel guesses restore 2 seconds.", "Time"),
        GlyphDef("consonant_clock", "Consonant Clock", "Common",
                 "Manual correct consonant guesses restore 1.5 seconds, up to 7.5 seconds per word.", "Time"),
        GlyphDef("rush_job", "Rush Job", "Rare",
                 "Start each word with 7 fewer seconds; all scores x1.35.", "Risk"),
        GlyphDef("time_dividend", "Time Dividend", "Common",
                 "Solve with at least half your starting time remaining for +450 Points and +1.5 seconds on the next word.", "Time"),
        GlyphDef("emergency_fund", "Emergency Fund", "Uncommon",
                 "The first manual correct guess made below 10 seconds restores 6 seconds.", "Time"),
        GlyphDef("deadline_writer", "Deadline Writer", "Rare",
                 "Each solve below 10 seconds permanently adds +0.35 starting seconds, up to +7 seconds.", "Scaler"),

        # ------------------------------------------------------------------
        # Information
        # ------------------------------------------------------------------
        GlyphDef("vowel_movement", "Vowel Movement", "Uncommon",
                 "The first correct vowel each word reveals another present vowel, if possible.", "Information"),
        GlyphDef("process_elimination", "Process of Elimination", "Common",
                 "After every 2 manual correct letter guesses, cross out one absent letter.", "Information"),
        GlyphDef("frequency_chart", "Frequency Chart", "Uncommon",
                 "At word start, highlight 4 letters; at least 2 are present in the word.", "Information"),
        GlyphDef("lexicographer", "Lexicographer", "Common",
                 "Display the word's part-of-speech tag(s) and cross out 2 absent letters at word start.", "Information"),
        GlyphDef("acrostic", "Acrostic", "Uncommon",
                 "Automatically reveal the first letter of each word.", "Information"),
        GlyphDef("epilogue", "Epilogue", "Uncommon",
                 "Automatically reveal the last letter of each word.", "Information"),
        GlyphDef("alphabetizer", "Alphabetizer", "Common",
                 "At word start, cross out 4 absent letters.", "Information"),
        GlyphDef("cross_reference", "Cross Reference", "Uncommon",
                 "After your first wrong guess, highlight 4 unaccounted letters; at least 2 are present.", "Information"),
        GlyphDef("vowel_census", "Vowel Census", "Common",
                 "Display the number of unique A/E/I/O/U vowels and cross out one absent vowel at word start.", "Information"),
        GlyphDef("pressure_notes", "Pressure Notes", "Uncommon",
                 "When the timer first falls below 50%, cross out 3 absent letters.", "Information"),
        GlyphDef("pattern_reader", "Pattern Reader", "Rare",
                 "After 4 manual correct letter guesses, automatically reveal one remaining letter, if possible.", "Information"),
        GlyphDef("steady_hand", "Steady Hand", "Common",
                 "Your second manual correct letter guess each word crosses out 2 absent letters.", "Information"),

        # ------------------------------------------------------------------
        # Structure / general scoring. Conditions are common or rewards are large.
        # ------------------------------------------------------------------
        GlyphDef("double_letter", "Double Letter", "Common",
                 "Correct guesses revealing multiple copies earn +220 Points.", "Structure"),
        GlyphDef("vowel_collector", "Vowel Collector", "Common",
                 "Each newly revealed unique vowel earns +120 Points.", "Structure"),
        GlyphDef("letterpress", "Letterpress", "Common",
                 "Manual correct letter guesses earn +65 Points per revealed position.", "Structure"),
        GlyphDef("consonance", "Consonance", "Common",
                 "Consecutive manual correct consonants earn +35, +70, +105... Points; every third in the streak also restores 1.5 seconds.", "Structure"),
        GlyphDef("first_draft", "First Draft", "Common",
                 "If your first manual letter guess is correct, earn +250 Points and restore 2.5 seconds.", "Structure"),
        GlyphDef("hard_copy", "Hard Copy", "Common",
                 "Words at least 0.30 Complexity above their target earn +500 Points.", "Structure"),
        GlyphDef("sesquipedalian", "Sesquipedalian", "Uncommon",
                 "Words of 9+ letters start with +2 seconds and score x1.35.", "Structure"),
        GlyphDef("short_story", "Short Story", "Uncommon",
                 "Words of 6 letters or fewer start with +3 seconds and score x1.35.", "Structure"),
        GlyphDef("no_vowels", "No Vowels", "Uncommon",
                 "Words with 1 or fewer unique A/E/I/O/U vowels start with +4 seconds and score x1.35.", "Structure"),
        GlyphDef("repeater", "Repeater", "Uncommon",
                 "Words containing a repeated letter score x1.30; the first multi-copy reveal also restores 3 seconds.", "Structure"),
        GlyphDef("unique_voice", "Unique Voice", "Uncommon",
                 "Words with no repeated letters begin with 2 absent letters crossed out and score x1.25.", "Structure"),
        GlyphDef("alphabet_soup", "Alphabet Soup", "Uncommon",
                 "Words containing at least 7 unique letters score x1.25.", "Structure"),
        GlyphDef("odd_job", "Odd Job", "Common",
                 "Odd-length words start with +5 seconds and score x1.12.", "Structure"),
        GlyphDef("even_keel", "Even Keel", "Common",
                 "Even-length words start with +5 seconds and score x1.12.", "Structure"),
        GlyphDef("vowel_rich", "Vowel Rich", "Uncommon",
                 "Words containing at least 3 unique vowels start with +2 seconds and score x1.30.", "Structure"),
        GlyphDef("middle_ground", "Middle Ground", "Common",
                 "Words 6–9 letters long score x1.18.", "Structure"),
        GlyphDef("bookends", "Bookends", "Common",
                 "Manually reveal the first or last letter to earn +200 Points and cross out 2 absent letters; once per word.", "Structure"),

        # ------------------------------------------------------------------
        # Complexity / risk
        # ------------------------------------------------------------------
        GlyphDef("scholar", "Scholar", "Uncommon",
                 "Complexity 6.5+ words start with +2 seconds and score x1.22.", "Complexity"),
        GlyphDef("rare_form", "Rare Form", "Rare",
                 "Complexity 8.0+ words start with +3 seconds and score x1.40.", "Complexity"),
        GlyphDef("common_ground", "Common Ground", "Uncommon",
                 "Complexity 5.0 or lower words start with +3 seconds and score x1.25.", "Complexity"),
        GlyphDef("cold_read", "Cold Read", "Rare",
                 "Full-word solve before half of its unique letters are revealed earns +500 Points.", "Risk"),
        GlyphDef("gambler", "Gambler", "Rare",
                 "Wrong full-word guesses cost +1 mistake; correct full-word guesses earn +450 Points.", "Risk"),
        GlyphDef("final_answer", "Final Answer", "Rare",
                 "Correct full-word solves score x1.50; wrong full-word guesses cost +2 additional mistakes.", "Risk"),
        GlyphDef("high_scrabble", "High Scrabble", "Uncommon",
                 "The first correct J, Q, X, or Z guess each word earns +400 Points and restores 3 seconds.", "Risk"),
        GlyphDef("cliffhanger", "Cliffhanger", "Uncommon",
                 "Solve with 1 or fewer mistakes remaining for +650 Points and +2 seconds on the next word.", "Risk"),
        GlyphDef("blind_faith", "Blind Faith", "Rare",
                 "Your first manual correct letter each word earns +300 Points; if your first letter guess is wrong, it costs +1 mistake.", "Risk"),

        # ------------------------------------------------------------------
        # Economy
        # ------------------------------------------------------------------
        GlyphDef("compound_interest", "Compound Interest", "Uncommon",
                 "Gain +1% score per 500 Points currently held, up to +20%.", "Economy"),
        GlyphDef("frugal", "Frugal", "Common",
                 "Glyph rerolls cost 45% less.", "Economy"),
        GlyphDef("clean_copy", "Clean Copy", "Common",
                 "Skipping a Glyph selection grants 500 Points.", "Economy"),
        GlyphDef("curator", "Curator", "Uncommon",
                 "Taking a Common Glyph grants 125 Points, Uncommon grants 250, and Rare grants 550.", "Economy"),
        GlyphDef("dividend", "Dividend", "Uncommon",
                 "At word start, gain 3% of held Points, up to 150 Points.", "Economy"),
        GlyphDef("cash_flow", "Cash Flow", "Common",
                 "Each manual correct letter guess earns +60 Points.", "Economy"),
        GlyphDef("nest_egg", "Nest Egg", "Uncommon",
                 "While holding at least 1,500 Points, every word starts with +3 seconds.", "Economy"),
        GlyphDef("reinvestment", "Reinvestment", "Uncommon",
                 "Each paid Glyph reroll adds +2 seconds to your next word, up to +8 seconds.", "Economy"),

        # ------------------------------------------------------------------
        # v1.0 utility / synergy additions
        # ------------------------------------------------------------------
        GlyphDef("last_word", "Last Word", "Rare",
                 "The first time you reach 1 remaining mistake each word, restore 4 seconds and automatically reveal one remaining letter if allowed.", "Accuracy"),
        GlyphDef("second_draft", "Second Draft", "Rare",
                 "Once per Chapter, if the timer would expire, take 1 mistake and return to 8 seconds instead, if that mistake would not kill you.", "Accuracy"),
        GlyphDef("panic_button", "Panic Button", "Uncommon",
                 "The first time you reach 1 remaining mistake each word, restore 6 seconds.", "Accuracy"),
        GlyphDef("lifeline", "Lifeline", "Rare",
                 "Once per Chapter, a wrong action that would end the run is softened just enough to leave you at 1 remaining mistake.", "Accuracy"),
        GlyphDef("bookmark", "Bookmark", "Common",
                 "Your first wrong action each word restores 3.5 seconds.", "Time"),
        GlyphDef("deadline_extension", "Deadline Extension", "Rare",
                 "Any word that would start below 24 seconds instead starts with +6 seconds.", "Time"),
        GlyphDef("quiet_room", "Quiet Room", "Uncommon",
                 "Automatic letter reveals restore 1.5 seconds each, up to 4.5 seconds per word.", "Time"),
        GlyphDef("red_string", "Red String", "Rare",
                 "After your third wrong action in a word, restore 2 seconds and automatically reveal one remaining letter if allowed.", "Information"),
        GlyphDef("spotlight", "Spotlight", "Uncommon",
                 "When at least half of a word's unique letters are revealed, highlight 4 unaccounted letters; at least 2 are present, if possible.", "Information"),
        GlyphDef("dead_letter", "Dead Letter", "Rare",
                 "Every wrong letter guess crosses out 2 additional absent letters.", "Information"),
        GlyphDef("inkblot", "Inkblot", "Rare",
                 "Cross out 7 absent letters at word start, but every word starts with 5 fewer seconds.", "Information"),
        GlyphDef("double_entry", "Double Entry", "Rare",
                 "The first automatic reveal each word also reveals a second remaining letter, but every word starts with 4 fewer seconds.", "Information"),
        GlyphDef("index_cards", "Index Cards", "Rare",
                 "Every 4 words solved while owned permanently adds +1 absent letter crossed out at word start, up to 4.", "Scaler"),
        GlyphDef("precision", "Precision", "Uncommon",
                 "Every third consecutive manual correct letter guess crosses out 2 absent letters.", "Information"),
        GlyphDef("loaded_dice", "Loaded Dice", "Rare",
                 "Paid Glyph rerolls have a 30% chance to refund their full cost after the new choices appear.", "Economy"),
        GlyphDef("war_chest", "War Chest", "Rare",
                 "While holding at least 2,500 Points, Boss words have +1 mistake capacity.", "Economy"),
        GlyphDef("market_maker", "Market Maker", "Rare",
                 "After defeating a Boss, gain 5% of your currently held Points, up to 500 Points.", "Scaler"),
        GlyphDef("liquidation", "Liquidation", "Uncommon",
                 "Replacing a Glyph pays 150/300/500 Points based on the rarity of the Glyph removed.", "Economy"),
        GlyphDef("lottery_ticket", "Lottery Ticket", "Rare",
                 "At word start, a 20% chance grants +1 mistake capacity and +5 seconds for that word.", "Risk"),
        GlyphDef("tightrope", "Tightrope", "Rare",
                 "While you have exactly 1 mistake remaining, manual correct letter guesses restore 2.5 seconds. Solving there earns +300 Points.", "Risk"),
        GlyphDef("streak_mark", "Streak Mark", "Rare",
                 "Four consecutive manual correct letter guesses erase 1 charged mistake, once per word.", "Accuracy"),
        GlyphDef("field_notes", "Field Notes", "Uncommon",
                 "Display the word's unique-vowel count, whether it repeats a letter, and a broad familiarity clue.", "Information"),
        GlyphDef("bailout", "Bailout", "Rare",
                 "The first time you would fall to 1 remaining mistake, automatically spend 500 Points to gain +1 mistake capacity for that word, if affordable.", "Economy"),

        # ------------------------------------------------------------------
        # Persistent scalers for long/endless runs
        # ------------------------------------------------------------------
        GlyphDef("perfect_copy", "Perfect Copy", "Rare",
                 "Starts at x1.00. Each zero-mistake solve permanently adds +0.05 to this Glyph's multiplier.", "Scaler"),
        GlyphDef("thesaurus", "Thesaurus", "Rare",
                 "Solved words with 6+ unique letters add a page. Every 3 pages permanently crosses out +1 absent letter at word start, up to 4.", "Scaler"),
        GlyphDef("snowball", "Snowball", "Uncommon",
                 "Perfect solves build a streak worth +110 Points per streak level; any charged mistake resets it.", "Scaler"),
        GlyphDef("rolling_press", "Rolling Press", "Rare",
                 "Each Boss defeated while owned permanently adds +0.6 starting seconds to every future word, up to +6 seconds.", "Scaler"),
    ]
}


AXIOMS = {
    a.id: a for a in [
        AxiomDef("expanded_vocabulary", "Expanded Vocabulary", "+1 Glyph slot."),
        AxiomDef("second_opinion", "Second Opinion", "Axiom selections may be rerolled once per boss for 500 Points."),
        AxiomDef("three_choices", "Expanded Selection", "Glyph selections contain +1 option beyond your difficulty's normal amount."),
        AxiomDef("recycling", "Recycling", "Trashed Glyphs refund Points based on rarity."),
        AxiomDef("grace_period", "Grace Period", "Every word starts with +4 seconds."),
        AxiomDef("margin_error", "Margin for Error", "Maximum mistakes increases by 1."),
        AxiomDef("narrow_definition", "Narrow Definition", "Word-complexity variance is reduced by 40%."),
        AxiomDef("high_standards", "High Standards", "Target Complexity +0.5; all word scores x1.25."),
        AxiomDef("fresh_ink", "Fresh Ink", "Your first Glyph reroll after each boss is free."),
        AxiomDef("cheap_revision", "Cheap Revision", "Glyph reroll costs escalate 45% more slowly."),
        AxiomDef("open_book", "Open Book", "Show exact word Complexity and cross out one absent letter at the start of every word."),
        AxiomDef("deep_pockets", "Deep Pockets", "Immediately gain 1,800 Points."),

        # Choice / build space
        AxiomDef("library_card", "Library Card", "Axiom selections contain +1 option beyond your difficulty's normal amount."),
        AxiomDef("deep_shelves", "Deep Shelves", "Uncommon Glyphs appear slightly more often and Rare Glyphs appear twice as often."),
        AxiomDef("archive", "The Archive", "+2 Glyph slots, but every word has -1 maximum mistake and -3 starting seconds."),
        AxiomDef("scaling_ink", "Scaling Ink", "Gain +1 Glyph slot for every 4 Chapters completed. Continues scaling in Endless."),

        # Broad Boss preparation. None target only one named Boss.
        AxiomDef("boss_insurance", "Boss Insurance", "Boss words have +1 mistake capacity."),
        AxiomDef("preparation", "Preparation", "At the start of each Boss, cross out 2 absent letters."),
        AxiomDef("countermeasure", "Countermeasure", "Boss words begin with +4 seconds. Numeric Boss penalties are also 20% weaker."),
        AxiomDef("boss_bounty", "Boss Bounty", "Boss-word scores x1.45."),

        # Global information / recovery
        AxiomDef("annotations", "Annotations", "At the start of every word, cross out 2 absent letters."),
        AxiomDef("footnotes", "Footnotes", "After the first wrong guess each word, cross out 2 absent letters."),
        AxiomDef("letter_of_law", "Letter of the Law", "The first manual correct letter guess each word restores 2 seconds."),

        # Global timing / risk rules
        AxiomDef("overtime", "Overtime", "Every word starts with +3 seconds, but all scores x0.96."),
        AxiomDef("sharp_deadline", "Sharp Deadline", "Every word starts with 3 fewer seconds; all scores x1.12."),
        AxiomDef("safe_answer", "Safe Answer", "Wrong full-word guesses cost 1 fewer mistake, to a minimum of 1."),
        AxiomDef("perfect_binding", "Perfect Binding", "Zero-mistake word solves score x1.12."),

        # Word-pool manipulation
        AxiomDef("familiar_ground", "Familiar Ground", "Bias word selection toward familiar vocabulary; all scores x0.95."),
        AxiomDef("deep_cut", "Deep Cut", "Bias word selection toward less familiar vocabulary; all scores x1.18."),

        # Chapter / endless scaling
        AxiomDef("chapter_bonus", "Chapter Bonus", "After each Boss, gain 500 Points."),
        AxiomDef("long_game", "Long Game", "Gain +0.5 starting seconds per completed Chapter, up to +8 seconds."),
    ]
}


BOSSES = {
    b.id: b for b in [
        BossDef("editor", "The Editor", "Wrong guesses also remove 4 seconds."),
        BossDef("minimalist", "The Minimalist", "Maximum mistakes is reduced by 2 for this word."),
        BossDef("mute", "The Mute", "Vowels cannot be guessed during the first 10 seconds."),
        BossDef("redactor", "The Redactor", "Revealed letters fade to dots after 10 seconds. Every correct letter guess refreshes all revealed letters."),
        BossDef("taxman", "The Taxman", "Each wrong guess costs 125 Points."),
        BossDef("purist", "The Purist", "Automatic letter-reveal Glyph effects are disabled."),
        BossDef("perfectionist", "The Perfectionist", "You cannot submit the full word until every unique letter is revealed."),
        BossDef("deadline", "The Deadline", "Begin with only 18 seconds before difficulty modifiers; correct letter guesses restore 3 seconds."),
        BossDef("blackout", "The Blackout", "Every 8 seconds, all revealed letters disappear for 2.5 seconds, then return."),
        BossDef("examiner", "The Examiner", "Full-word guesses are disabled. Solve by revealing the letters."),
        BossDef("executioner", "The Executioner", "Start with only 3 mistake capacity. Each manual correct letter restores +1 capacity up to your normal maximum."),
        BossDef("censor", "The Censor", "One letter stays blacked out even after you guess it correctly. You must remember what is underneath."),
        BossDef("clockmaker", "The Clockmaker", "Every manual letter guess removes 1.5 seconds from the clock."),
        BossDef("alternator", "The Alternator", "Manual letter guesses must alternate between vowels and consonants."),
        BossDef("forbidden", "The Forbidden", "One present letter cannot be guessed directly. Reveal it automatically or solve the full word."),
        BossDef("gatekeeper", "The Gatekeeper", "Full-word guesses are locked until you make 3 manual correct letter guesses."),
    ]
}


# How much intrinsic word Complexity is reduced on each Boss round.
# The modifier itself consumes part of the difficulty budget; stronger survival
# modifiers receive easier words. v0.6 gives The Redactor the largest budget
# after telemetry showed a 3/3 failure rate against it.
BOSS_COMPLEXITY_BUDGET = {
    "editor": 0.35,
    "minimalist": 0.45,
    "mute": 0.30,
    "redactor": 0.80,
    "taxman": 0.10,
    "purist": 0.25,
    "perfectionist": 0.20,
    "deadline": 0.40,
    "blackout": 0.55,
    "examiner": 0.25,
    "executioner": 0.90,
    "censor": 0.45,
    "clockmaker": 0.50,
    "alternator": 0.70,
    "forbidden": 0.70,
    "gatekeeper": 0.30,
}


RARITY_WEIGHTS = {"Common": 66, "Uncommon": 27, "Rare": 7}
RARITY_TRASH_VALUE = {"Common": 100, "Uncommon": 225, "Rare": 450}
