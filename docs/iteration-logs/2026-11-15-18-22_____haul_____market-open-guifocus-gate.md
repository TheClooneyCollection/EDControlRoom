# Gate market navigation on Starport Services focus

## Cause and verified assumption
- Six forge incidents traced to a lost station-services Select followed by blind Down/Select on Launch. UI_Back does not reset the docked-menu cursor.
- User verified on forge VR: docked menu GuiFocus 0, Starport Services and commodities GuiFocus 5; updates appear within about 1–1.5s. Focus 5 cannot replace Market.json station validation.

## Changes
- `market_buy` / `market_sell` require an explicit `read_status_fn`; two-way haul (including cargo recovery), multi-leg haul, Control Room buy/sell/sell-all and the routine CLI pass the real Status.json reader. Its optional result reflects missing runtime files, not a test-only API relaxation.
- After entering station services, poll every 0.25s for GuiFocus 5, up to 10s per Select. Retry only while docked at focus 0, at most three Selects total (initial plus two retries; 30s maximum wait). No cursor-moving press is sent on failure.
- Once focus 5 appears, settle 1.5s and verify focus/docked again before navigating Down/Select. The existing market-load 5s wait and Market.json station validation remain.
- Before station re-navigation and outer trade retries, check the docked flag. Also check after navigation before station validation, so undocking reports `undocked during buy/sell` instead of a stale-station error. Missing status fails without navigation; other/unknown focus never gets a retry Select.
- Semantic actions only. Existing sell journal pre/post checks remain.

## Validation
- Added seven behavior tests with plain status/clock functions: permanently lost Select (both sides, three Selects/no Down), late focus on the third poll with settle, unknown/other focus, undocking during wait/settle, between station attempts and between outer buy/sell attempts, and missing status.
- Existing market wrappers explicitly provide docked focus 5. `uv run python3 -m unittest tests/test_routines.py`: 70 tests / 0.025s, OK.
- `uv run python3 -m unittest discover -s tests`: 1241 tests / 0.790s, OK (1 skipped), above 0.7446s budget already exceeded on main.
- Required timing report: suite_status=ok, 1241 tests / 0.706s; largest existing central-history test 0.012s. No unrelated timing edits.
- Not run against the live game; coordinator owns deployment and forge validation.
