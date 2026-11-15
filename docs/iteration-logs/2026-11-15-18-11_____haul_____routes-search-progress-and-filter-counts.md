# Routes search progress and filter counts

## Changes
- Frontend only: `web/routes.js` and `web/routes.html`.
- Search status ticks `Searching… N s`; Search is disabled and aria-busy while old results dim and become inert to keyboard and pointer input.
- Each new request replaces the previous timer and clears field counts. Stale success/error/finally paths cannot overwrite the current status, hints or busy state. Current errors retain `Search failed: <message>`.
- Nonzero age, station distance, carrier, carrier-access and surface counts appear below their fields. Mapped reasons leave the status line; pad, construction depot, coordinates, no usable prices, departed carriers and unknown reasons remain there.
- Departed carriers stay in status because departure is independent of the open-access filter. Min supply has no market count. Hints explain first-failed-filter counting.

## Validation
- `node --check web/routes.js` passed.
- Temporary Node VM DOM/clock/fetch harness (`/private/tmp/edcr-routes-ui-check.cjs`) exercised the complete script: elapsed seconds, busy/inert state, mapped/unmapped/unknown reasons, zero and cleared counts, current failure with escaped message, superseded failure/success and timer cleanup. Passed; no existing JS harness was present, no new test infrastructure added.
- `uv run python3 -m unittest discover -s tests`: 1234 tests in 0.819s, OK (1 skipped). Above the 0.7404s timing budget, already exceeded on main.
- Required timing report: 1234 tests in 0.730s, suite_status=ok; largest entry existing hub status at 0.010s. No unrelated performance edits.
- No live hub restart or deployment; browser visual validation remains for deployment.
