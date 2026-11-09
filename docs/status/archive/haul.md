# Haul Status Archive

Prepend displaced older status blocks from `docs/status/haul.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

## Archived 2026-11-09

- Shared station transit mechanics now live in neutral `edap.routines.transit` helpers reused by two-way haul, multi-leg haul, and `travel`; haul cargo/runtime support remains in `edap.routines.haul_support`, and two-way `haul` remains the primary operator path while standalone `multi_leg_haul` / `mult` handles finite external JSON or Spansh-driven routes.

## Archived 2026-11-07

- Haul prompt resume/edit now prefills the command input with the saved station names, systems, cargo legs, and timing values, and deleting a prefilled cargo/station field now leaves it truly blank instead of silently restoring saved text.
