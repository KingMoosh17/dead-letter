# Dead Letter v1.1.2

A timed Hangman roguelike. Solve increasingly difficult words, build around passive Glyphs, earn permanent Axioms from Bosses, clear Chapter 8, then continue into Endless.

## Run the game

On Windows, double-click **`DeadLetter.exe`**. The public build is standalone and does not require a separate Python installation.

The repository still includes the Python source for development and debugging.

## Core rules

- Six charged mistakes or an empty timer ends the run.
- Each Chapter is Word 1 → Word 2 → Word 3 → Boss.
- Solved words award Points and a Glyph choice. Points pay for rerolls.
- Bosses award permanent Axioms.
- Beat Chapter 8 to win; Endless continues until defeat.
- Word Complexity is a Hangman-focused 1–10 rating rather than a length score.

## Difficulty

- **Easy:** +10 seconds per word; 3 base Glyph and Axiom options.
- **Medium:** standard timing; 2 base Glyph and Axiom options.
- **Hard:** -6 seconds per word; 1 base Glyph and Axiom option.

All difficulties use six base mistakes.

## Word banks

Five large pools can be selected for each run:

- **Standard:** the full balanced lexicon, ranging from familiar to obscure vocabulary (~35k words).
- **Common Tongue:** leans toward familiar everyday words and cleaner spellings.
- **Longform:** leans toward longer, less-common vocabulary and denser spellings.
- **Quickfire:** favors compact short/mid-length words where each reveal carries less information.
- **Labyrinth:** favors unusual spelling, rare letters, awkward vowel structures, and deceptive patterns.

The four alternate pools contain ~28,000 words each and intentionally overlap with Standard so they remain viable in long Endless runs.

## Content

- 96 Glyphs
- 31 Axioms
- 16 Bosses before the Boss pool repeats
- 5 word banks
- Easy / Medium / Hard
- Endless mode
- Compendium, persistent stats, tutorial, sound, display options, and reduced motion

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

The game checks the configured public GitHub Releases feed. When a newer release is available, an **Update to vX.Y.Z** button appears on the main menu. Updates preserve settings, stats, and telemetry. A saved Continue Run must be discarded before updating, and the game asks for confirmation first.

Public releases include a standalone `DeadLetterUpdater.exe`, allowing executable builds to update themselves without requiring Python.
