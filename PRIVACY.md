# Dead Letter Telemetry & Privacy

Dead Letter records optional local playtest telemetry to help improve word difficulty and roguelike balance.

## Local telemetry

When **Local play telemetry** is enabled in Settings, Dead Letter stores gameplay telemetry in the player's per-user Dead Letter data folder. This may include:

- run and round identifiers scoped to a single run;
- game version, difficulty, selected word bank, chapter, and round;
- the word played and its calculated difficulty features;
- timing, guesses, mistakes, crossed-out/revealed letters, score, and outcome;
- Boss encounters;
- Glyph/Axiom offers, rerolls, selections, replacements, skips, and trashing;
- run milestones such as entering Endless Mode or finishing a run.

Local telemetry can be disabled in Settings.

## Anonymous playtest sharing

Online sharing is **off until the player explicitly opts in**. If enabled, Dead Letter may send the same gameplay/balance telemetry described above to the developer's Supabase database.

Dead Letter does not intentionally send a player's name, email address, account information, personal files, or a persistent device/player identifier. Events contain a run ID used only to connect events from the same individual run.

Online sharing can be disabled at any time in Settings. Disabling it stops new uploads. Network failures do not interrupt gameplay; locally queued events may be retried later while sharing remains enabled.

## Purpose

Telemetry is used for development purposes such as:

- tuning the word Complexity model;
- comparing difficulty and word-bank performance;
- evaluating Glyph, Axiom, and Boss balance;
- identifying unusual or broken run patterns;
- improving pacing and progression.
