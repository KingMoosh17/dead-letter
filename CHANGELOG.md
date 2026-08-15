# Dead Letter v1.1.11

## Dominance balance pass
- Re-audited the full Glyph and Axiom pools for effects that were effectively weaker copies of another choice rather than genuinely different niches.
- **Thesaurus:** now starts at 1 absent-letter cross-out and scales to 7 total; every 3 pages still adds +1.
- **Index Cards:** now starts at 2 cross-outs and scales to 6 total, adding +1 every 4 solved words.
- **Process of Elimination:** now crosses out 2 absent letters every 2 manual correct guesses.
- **Steady Hand:** its delayed second-correct trigger now crosses out 5 absent letters.
- **Pressure Notes:** its half-timer trigger now crosses out 6 absent letters.
- **Momentum:** now restores 1.5s per manual correct letter, up to 10.5s per word.
- **Stopwatch:** now restores 5s every third manual correct letter.
- **Chain Reaction:** now restores 7s every three consecutive manual correct letters.
- **Consonant Clock:** now restores 2s per correct consonant, up to 10s per word.
- **Second Wind:** its first multi-copy reveal now restores 8s.
- **Cash Flow:** now earns 100 Points per manual correct letter, making it stronger on single-copy hits while Letterpress remains stronger on repeated letters.
- **Loaded Dice:** paid rerolls now have a 50% full-refund chance, giving it higher expected value than the deterministic Common Frugal while retaining variance.
- **Market Maker:** redesigned into a true Boss economy scaler. It begins at 10% of held Points after each Boss, rises by 2 percentage points per Boss defeated while owned, caps at 20%, and has a 1,200-Point payout cap.

## Axiom specialization
- **Overtime:** +7 starting seconds with x0.94 score instead of being a smaller, penalized Grace Period.
- **Boss Insurance:** +2 mistake capacity on Boss words instead of being a strict subset of Margin for Error.
- **Preparation:** 5 absent-letter cross-outs at Boss start instead of being a strict subset of Annotations.
- **Footnotes:** 5 absent-letter cross-outs after the first wrong guess instead of a delayed copy of Annotations.
- **Long Game:** now gains +0.75 starting seconds per completed Chapter, up to +9s, so it begins paying off during the main run while retaining its Endless identity.

## Consistency
- Corrected the No Vowels score implementation to its displayed x1.35 multiplier.
- Removed the remaining player-facing uses of the old `charged mistake` terminology from Streak Mark and Snowball.
- Chapter Preview time estimates use the new Overtime and Long Game values.

# Dead Letter v1.1.10

## Chapter previews
- Every Chapter now opens on an untimed **Chapter Preview** screen before Word 1 begins.
- New Run and Restart land on the Chapter 1 preview instead of jumping directly into a timed word.
- The preview shows the Chapter's average target Complexity, expected starting-time average/range, and upcoming Boss.
- Chapter previews are safe save points and include **Save & Exit**.
- Endless Chapters use the same preview flow.
- Starting-time previews account for difficulty, predictable Axiom effects, and predictable Glyph timing effects; word-dependent/random Glyph effects are excluded and identified as such.

## Flow
- Entering a Chapter explicitly starts Word 1, keeping timers fully paused until the player confirms.
- Existing Word 2, Word 3, Boss-approach, Glyph, and Axiom flows are unchanged.

# Dead Letter v1.1.9

## New Run layout
- Removed the fixed-height and post-layout geometry experiments from the New Run screen.
- Difficulty and word-bank cards now size naturally and share the same selector component.

# Dead Letter v1.1.5

## New Run polish
- Word-bank selectors now match the difficulty selectors in font weight and visual height.

## Boss balance
- **The Forbidden** no longer tells you its blocked present letter before the round.
- The forbidden letter is revealed only when you attempt to guess it.
- That discovery attempt is blocked harmlessly and does not add a mistake.
- Once discovered, the forbidden letter remains visible in the word-information line for the rest of the Boss round.

## Wording
- Removed player-facing use of the technical phrase **charged mistake**.
- Protection effects can still reduce an attempted penalty before it reaches the mistake meter; telemetry keeps that distinction internally.
- Recovery Room and How to Play now describe mistakes in terms of what is actually added to the meter.

## Update discovery
- Added a public GitHub release-page fallback when the GitHub API lookup fails or is rate-limited.
- Manual update checks now distinguish a network/release-service failure from a genuine up-to-date result.

# Dead Letter v1.1.4

## Updater hotfix
- Fixed an update failure introduced by the standalone one-file Windows executable build.
- The updater now waits briefly for the exiting PyInstaller bootloader and retries replacement of locked application files instead of failing on the first Windows file-lock error.
- File replacement is staged to temporary filenames and then swapped into place, reducing the chance of leaving a partially written executable.
- Added `%APPDATA%\DeadLetter\update.log` with timestamps and install steps for updater diagnostics.
- Windowed updater failures now show a visible error dialog instead of silently returning to the old version.
- The installed `VERSION.txt` is verified before the updated game is relaunched.

# Dead Letter v1.1.3

## Interface cleanup
- Removed repeated Boss-next messaging from reward screens. The Chapter tracker no longer adds a separate `BOSS NEXT` callout, the Word Cleared strip no longer repeats it, and the duplicate upcoming/next-Boss boxes are gone before the dedicated Boss approach screen.
- Removed the explanatory `The timer is paused...` sentence from Boss approach screens.
- Removed difficulty-specific `N options offered on ...` helper copy from Glyph/Axiom selections.
- Renamed the main-menu **Tutorial** button to **How to Play**.
- Replaced the main-menu record/content sidebar with the Dead Letter gallows/seal artwork.
- Removed decorative global content-count copy from the main menu and New Run screen.

## New Run polish
- Difficulty and word-bank selectors now update in place instead of rebuilding the whole screen, eliminating the most visible Windows button flash.
- The selectors use flat label controls instead of native Tk buttons for smoother selection transitions.
- Tightened the word-bank cards without reducing their text size.
- Kept representative example words on every bank card.
- Enlarged the seed field and centered a larger, more prominent **Start Run** button.
- Removed the redundant How-to-Play button from New Run.

## Compendium & Glyphs
- Glyph rarity totals are shown in the Compendium and the current filter reports how many entries are being shown.
- Rarity colors remain consistent across inventory, offers, replacement screens, and the Compendium.
- If **Recycling** is owned, Glyph descriptions now display their exact sell value.

## Windows build & updater
- `DeadLetter.exe` keeps the branded Dead Letter icon.
- `DeadLetterUpdater.exe` now uses a separate subdued updater icon.
- Loose `.ico` files are no longer included in the public release folder; the game icon is embedded/bundled instead.
- In-place updates keep the `DeadLetter.exe` path stable, so ordinary Windows shortcuts continue working across updates.
- The updater remains based on public GitHub Releases and requires no GitHub login for players.

# Dead Letter v1.1.2

## Windows build
- Public releases now include a standalone **DeadLetter.exe** with a custom Dead Letter icon.
- Added a standalone **DeadLetterUpdater.exe** so future executable builds can update without a Python installation.
- Retired the legacy `run_game.bat` launcher from public releases.

## Interface polish
- Removed the extra title-screen tagline for a cleaner title composition.
- Fixed difficulty/word-bank selection buttons flashing white while changing selections.
- Standardized selected-button typography so `SELECTED` is consistently bold.
- Added representative example words to every word-bank card.
- Enlarged the Hangman panel and figure.
- Bonus mistake capacity is now consumed visually before the six-part Hangman begins drawing.
- Standardized Glyph rarity colors across inventory, reward/reroll cards, replacement UI, and Compendium.
- Removed visible Glyph category labels; Glyph presentation is now name + rarity + description.
- Compendium Glyphs default to Common → Uncommon → Rare and now support rarity filters plus multiple sorting modes.
- Axiom and Boss compendium tabs also support ascending/descending name sorting.
- End-of-run build summary no longer tries to classify the build into a single Glyph category.

# Dead Letter v1.1.1

## Interface
- Reworked the New Run word-bank selector into a spacious two-row layout.
- Increased word-bank title/description/button text sizes substantially.
- Expanded the five bank descriptions so their gameplay identities are clearer before starting a run.

## Repository
- Prepared the project for its initial public source push to `KingMoosh17/dead-letter`.

## v1.1
## Run variety
- Boss pool expanded from 12 to **16**. Every Boss appears once before Endless begins a new shuffled cycle.
- Added **The Clockmaker**, **The Alternator**, **The Forbidden**, and **The Gatekeeper**.
- Added five selectable word banks: Standard, Common Tongue, Longform, Quickfire, and Labyrinth.
- Non-standard banks contain ~28,000 words each; Standard contains ~35,000.

## Quality of life
- Added an always-visible **Restart** button during runs. It starts a new run with the same difficulty and word bank using a fresh seed.
- Renamed **Save & Main Menu** to **Save & Exit**.
- Continue Run now restores the selected word bank.
- Trimmed tutorial, setup, telemetry, and menu wording to remove repeated explanations.
- Forbidden-letter Boss information is shown before entering the timed Boss round.

## Updates
- Added optional GitHub Releases update checks.
- A main-menu update button appears only when a newer configured release is found.
- The updater downloads and validates a ZIP, installs it after the game exits, and relaunches Dead Letter.
- Player stats, settings, and telemetry stay in the external player-data folder and survive updates.
- If a Continue Run exists, the player is warned that it will be deleted before installation. Failed downloads do not delete the save.

## Balance
- Revisited low-pick Glyphs using existing decision telemetry.
- Buffed several conditional Time, Structure, and Economy Glyphs so narrow triggers provide more meaningful value.
- Gambler and Compound Interest remain unchanged.
- Existing Axioms were re-audited; no broad redesign was needed.
- New high-pressure Bosses receive larger word-complexity reductions than mild Bosses.
