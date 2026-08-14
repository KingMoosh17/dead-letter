# Dead Letter v1.1.6

A timed Hangman roguelike. Solve increasingly difficult words, build around passive Glyphs, earn permanent Axioms from Bosses, clear Chapter 8, then continue into Endless.

## Run the game

On Windows, double-click **`DeadLetter.exe`**. The public build is standalone and does not require a separate Python installation.

The repository also includes the Python source for development and debugging.

## Core rules

- Six mistakes added to your meter, or an empty timer, ends the run.
- Each Chapter is Word 1 → Word 2 → Word 3 → Boss.
- Solved words award Points and a Glyph choice. Points pay for rerolls.
- Bosses award permanent Axioms.
- Beat Chapter 8 to win; Endless continues until defeat.
- Word Complexity is a Hangman-focused 1–10 rating rather than a length score.

Protection can reduce a mistake before it reaches the meter. Internally telemetry distinguishes an attempted penalty from a mistake that actually counts, but player-facing rules refer to the meter directly.

## Difficulty

- **Easy:** +10 seconds per word; 3 base Glyph and Axiom options.
- **Medium:** standard timing; 2 base Glyph and Axiom options.
- **Hard:** -6 seconds per word; 1 base Glyph and Axiom option.

All difficulties use six base mistakes.

## Word banks

Five large pools can be selected for each run:

- **Standard:** the full balanced lexicon, ranging from familiar to obscure vocabulary.
- **Common Tongue:** leans toward familiar everyday words and cleaner spellings.
- **Longform:** leans toward longer, less-common vocabulary and denser spellings.
- **Quickfire:** favors compact short/mid-length words where each reveal carries less information.
- **Labyrinth:** favors unusual spelling, rare letters, awkward vowel structures, and deceptive patterns.

## Controls

- `A–Z`: guess a letter
- `/`: focus full-word guess
- `Esc`: leave the full-word box
- `F11`: toggle fullscreen/windowed
- **Restart:** always available during a run; starts a fresh run with the same difficulty and word bank
- **Save & Exit:** available only on untimed safe screens

## Saves and player data

On Windows, settings, stats, Continue Run saves, and optional telemetry are stored in:

```text
%APPDATA%\DeadLetter
```

They are kept outside the installation folder so game updates do not overwrite them. Local telemetry never uploads automatically.

## Updates

Dead Letter checks the public `KingMoosh17/dead-letter` GitHub Releases feed. The player does **not** need a GitHub account or login. When a newer release is available, an **Update to vX.Y.Z** button appears on the main menu.

Updates keep the installation path and the `DeadLetter.exe` filename stable, so a normal Windows shortcut to the executable continues to work after in-place updates. Settings, stats, and telemetry are preserved. A saved Continue Run must be discarded before updating, and the game asks for confirmation first.

Public releases include a standalone `DeadLetterUpdater.exe`; it has a deliberately different icon from the main game executable. v1.1.4 added retry-based handling for brief Windows executable locks and updater diagnostics at `%APPDATA%\DeadLetter\update.log`.

v1.1.5 made update discovery more resilient and adjusted The Forbidden so its blocked present letter stays hidden until the player probes it. v1.1.6 fixes the remaining New Run layout issue by reserving full-size word-bank selector controls before laying out each card's descriptive text.
