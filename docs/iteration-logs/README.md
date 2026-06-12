# Iteration Logs

Use one file per substantive work session that changes project understanding, status, code, docs workflow, or recommended next steps.

## Naming

- Create new logs with `uv run python3 tools/iteration_logs.py new "<area>" "<title>"`.
- Format: `YYYY-MM-DD-HH-MM_<area>_<title>.md`
- `_` separates fields; `-` separates words inside a field
- `<area>` is a short kebab-case slug center-padded with underscores to width `12`
- `control-room` is the maximum-width area slug

Examples:

- `2026-06-11-13-45_____docs_____iteration-log-migration.md`
- `2026-06-11-13-50______ci______test-timing-threshold-bump.md`
- `2026-06-11-13-55_control-room_error-text-yaml-migration.md`

## Numbering

- Legacy manual session counting stopped at `133`
- Generated iteration numbering starts at `134`
- Derive the next number with `uv run python3 tools/iteration_logs.py next-number`
- Validate the directory with `uv run python3 tools/iteration_logs.py validate` before committing, pushing, or opening a PR
- Promotion PR automation should normally refresh `docs/iteration-archive.md` on `promote-dev-to-main--generated-iteration-archive`
- Regenerate `docs/iteration-archive.md` manually with `uv run python3 tools/iteration_logs.py render-archive` only when you need a local refresh or release-prep validation

## Scope

- Keep logs concise and operational
- Prefer project-impacting facts, validation notes, and follow-ups
- Leave older pre-migration handoff history in `docs/status-archive.md`
