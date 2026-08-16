# v1.1.13 Telemetry Release

- Adds explicit opt-in anonymous gameplay sharing.
- Keeps local CSV telemetry as the source of truth.
- Uploads run-scoped round, decision, and run-event telemetry to Supabase only after consent.
- Does not create or transmit a persistent player/device identifier.
- Adds a reversible online-sharing control to Settings.
- Queues uploads locally and retries without blocking gameplay.
- Adds `PRIVACY.md` describing collected gameplay data and its development purpose.
- Adds automatic itch.io publishing alongside GitHub releases.
