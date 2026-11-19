# Iteration Log

- Area: `tests`
- Title: `snapshot-fixture-timing`
- Started: `2026-11-19 23:10`

## Summary

- Reduce repeated SQLite fixture creation and host proxy discovery without changing production code or removing assertions.

## Changes

- Snapshot writers copy an empty serialized schema; live WAL snapshot and legacy/future schema reopening checks remain real.
- Fetch tests reuse the existing memory-store fixture, create import-equivalence input directly, and use a real HTTP opener with proxies explicitly disabled for local traffic and invalid-URL checks.
- Route fixtures cache immutable seed bytes and deserialize independent stores; the database-file query test writes those bytes directly.
- Three-run wall clocks after stashing changes: snapshot 7 tests 0.042/0.045/0.043s; fetch 11 tests 0.042/0.042/0.044s; routes 12 tests 0.019/0.018/0.019s. Final: snapshot 0.035/0.037/0.042s; fetch 0.024/0.026/0.026s; routes 0.016/0.015/0.014s.
- Full suite: 1295 tests in 1.096s, OK (1 skipped). Required timing report: 1.160s; still above the 0.777s budget before integration with other timing slices.
- Haul web flow (0.082/0.066/0.068s) and route-compare endpoint (0.032/0.032/0.030s) remain unchanged: no justified production seam or behavior reduction.

## Follow-ups

- Integrate other timing slices and rerun the full suite; the Node subprocess flow and haul transit waits dominate this isolated branch.
