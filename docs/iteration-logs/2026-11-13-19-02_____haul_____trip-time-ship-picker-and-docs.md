# Iteration Log

- Area: `haul`
- Title: `trip-time-ship-picker-and-docs`
- Started: `2026-11-13 19:02`

## Summary

- The `/config` page now has a ship picker beside **Fitted**, ships have in-game names, and step 5 of [plan 0016](../plans/0016-journal-events-and-trip-time-fit.md) (docs) is done.

## Changes

- `[eddn.time_model] fit_ship`: `current` (default: the flown ship's fit, else pooled), `pooled`, or a ShipID whose fit every ship uses. `TripTimeModels.fitted_for(ship_id, pick)` picks it; `save_time_model` writes it.
- `GET /api/time-model?fit=` shows another fit without saving it (400 on a bad value); a peer passes it to the hub as `view` in the `time_model` request. The payload adds `view`, `ship_label`, `ships` (each ship with its own fit, most legs first), `pooled_legs`, and a `label` on `fitted` and `active`.
- Names come from the latest `Loadout` per ShipID (`Ship`, `ShipName`, `ShipIdent`), with `edcr/ship_types.py` mapping journal types to in-game names, e.g. `Panther Clipper Mk II MR-06P`. `/routes` and Best deal say "trip time fitted for <ship>".
- The picker lists `Current ship (<name>)`, each fitted ship with its legs, and `Every ship pooled`. Changing it reloads the table for that fit; Save stores it.
- Follow-up from the user: the Caspian (27 legs in 14 days) was missing and other nodes showed no list. The picker now lists every ship with legs in the window (`fitted: false` under 30, using the pooled fit, with a note), and `/api/time-model` is no longer a relayed node read: the hub answers it for the picked node's last reported ship (`viewed_ship`, as `/markets` does), editable, even when the node is offline or runs older code.
- Docs: `docs/user/trade-routes.md` (`fit_ship` and the picker), `docs/user/hub.md` (journal events and trip time rows in the roles table, a Trip time item under the hub's pages), `config.example.toml`, plan status.
- Checked with playwright on a scratch server on the live store at 1200 and 390 px. The first run showed the select taking the full row on desktop and pushing Save down, so it now sizes to its content.

## Follow-ups

- Live: a check that forge's journal events reach the hub (`tools/journal_events.py` on the hub).
