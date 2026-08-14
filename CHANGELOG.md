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
