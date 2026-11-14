# Haul Status Archive

Prepend displaced older status blocks from `docs/status/haul.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

## Archived 2026-11-14

- `haul search [system]` now treats `home` as the saved `control_room.home_system`, defaults from local ignored search config, accepts `max_station_distance_ls=any`, shows compact profit/distance detail, restores cargo capacity from latest journal `Loadout`, maps live Inara aliases, lets Enter load the highlighted route, `d` set `dest` to the first station system, `t` start travel to that station, `haul start` run the selected/saved route, and keeps `connect` search/results local until a structured route/destination/travel dispatch is submitted.

## Archived 2026-11-11

- Two-way `haul` loads ignored repo-root `haul.toml` by default via `haul load [path]`; the tracked profile shape lives in `defaults/haul.toml`, and the default haul docking timeout is now `1200s`.

## Archived 2026-11-10

- Two-way `haul` now accepts one-sided loops: station 1 or station 2 buy cargo may be blank as long as the other side is configured, and the routine skips the missing buy/sell leg cleanly during prompt flow, launch, and resume detection.
- Two-way and multi-leg haul transit now announce the next station immediately after hyperspace arrival before opening the nav panel, and abort/TTS `haul_aborted` instead of requesting docking if an `Interdicted` event precedes the transit `SupercruiseExit`.

## Archived 2026-11-09

- Shared station transit mechanics now live in neutral `edap.routines.transit` helpers reused by two-way haul, multi-leg haul, and `travel`; haul cargo/runtime support remains in `edap.routines.haul_support`, and two-way `haul` remains the primary operator path while standalone `multi_leg_haul` / `mult` handles finite external JSON or Spansh-driven routes.

## Archived 2026-11-07

- Haul prompt resume/edit now prefills the command input with the saved station names, systems, cargo legs, and timing values, and deleting a prefilled cargo/station field now leaves it truly blank instead of silently restoring saved text.
