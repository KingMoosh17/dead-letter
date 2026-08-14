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
