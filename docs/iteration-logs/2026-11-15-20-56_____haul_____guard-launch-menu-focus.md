# Iteration Log

- Area: `haul`
- Title: `guard-launch-menu-focus`
- Started: `2026-11-15 20:56`

## Summary

- Fix launch navigation attempted while Station Services remains open.

## Changes

- Replace the blind repeated Back with up to ten individual paced presses, stopping at confirmed docked GuiFocus 0. Recheck immediately before Down and Select.
- Require an explicit status reader in standalone undock and the shared transit launch helper; wire real Status.json readers in both production paths. Retry transient missing/partial status for one second, then fail closed.
- Six new flow tests cover lost Back, stuck Services, unavailable/unknown/undocked status, focus changes, partial writes and dispatch failure. Existing travel/haul fixtures now provide docked menu status.
- Full suite: 1249 tests, 0.995s, OK (1 skipped). Timing threshold 0.7494s exceeded; required timing report: 0.964s, slowest four existing transit tests 0.035–0.038s each. Unmodified main baseline: 1243 tests in 1.076s, OK (1 skipped); this change does not regress the existing timing overrun.

## Follow-ups

- Live-check departure from Station Services, including slow or lost Back input; no live game input was sent during implementation.
- Secondary integrates the isolated fix/launch-services-focus branch and handles deployment.
