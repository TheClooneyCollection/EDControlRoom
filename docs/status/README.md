# Status Index

Read this file first, then open the area files that match the work you are touching.

- `ci-release.md`: CI policy, release automation, promotion PR automation
- `control-room.md`: Control Room UX, messages, logging, operator-facing surface
- `docs-process.md`: handoff workflow, iteration docs, status maintenance rules
- `haul.md`: two-way haul, multi-leg haul, station-flow caveats
- `runtime.md`: platform validation, journal/runtime plumbing, CV gap

Rules:

- Each `docs/status/<area>.md` file is capped at 20 lines.
- Keep only high-value current truth there; chronology belongs in `docs/iteration-logs/`.
- If an area file would overflow, compress first, then prepend displaced history to `docs/status/archive/<area>.md`.
- Legacy pre-split status history remains in [../status-archive.md](../status-archive.md).
