# Tolerate transient market Status.json rewrites

## Changes
- Market-only `_read_market_status` wraps the existing injected reader, with explicit sleeper/time functions; the public callback signature and `edcr/status.py` remain unchanged.
- None, JSONDecodeError and OSError mean unknown. Retry every 0.1s until a usable status arrives or a 1s deadline expires; never reuse stale docked/focus values or issue input during that wait.
- Every new market navigation/docked gate uses this wrapper. Valid undocked state still stops immediately; persistent unknown produces the existing clear unavailable error.

## Validation
- Behavior cases: one None, JSONDecodeError or OSError during the first services poll followed by focus 5 all complete a sell with no extra Select; persistent None fails after 1s with no inputs.
- `uv run python3 -m unittest tests/test_routines.py`: 71 tests / 0.024s, OK.
- Full suite: 1242 tests / 0.768s, OK (1 skipped), above 0.7452s budget; required timing report suite_status=ok / 0.790s. No unrelated optimization.
- No live run or deployment; follows c5f77d9 on the same branch.
