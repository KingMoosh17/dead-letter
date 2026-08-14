# GitHub update setup

Dead Letter v1.1.1 is preconfigured for:

```text
KingMoosh17/dead-letter
```

The in-game updater uses **public GitHub Releases**. Players do not need a GitHub account or a ChatGPT connection.

## One-time setup

1. Keep the game source in this repository.
2. For each public version, create a GitHub Release with a version tag such as `v1.2`.
3. Attach the packaged build as a ZIP named like:

```text
Dead_Letter_v1.2.zip
```

The ZIP must contain `VERSION.txt` and `main.py` at its root or one folder below its root.

## Update behavior

- The game checks GitHub's latest public Release when the main menu opens, if update checks are enabled.
- No button appears when the current version is newest or the release feed cannot be reached.
- A downloaded archive is validated before installation.
- Player data remains in `%APPDATA%\DeadLetter` and is not replaced.
- A Continue Run is deleted only after the new archive downloads and validates successfully, and only after the player confirms the update.
