# Iteration Log

- Area: `ci-release`
- Title: `measure-test-timing-hotspots`
- Started: `2026-06-27 13:53`

## Summary

- Measured the current unittest baseline at `539` tests in about `0.55s`, above the repo `0.3s` target, then brought the suite back under budget.
- Final baseline after the test rewrite is `541` tests in about `0.296s`.

## Changes

- Ran `uv run python3 -m unittest discover -s tests` and `UV_CACHE_DIR=/private/tmp/uv-cache uv run python3 tools/report_test_timing.py --top 20 --sort slowest`.
- Identified `tests/test_control_room_client.py` as the dominant hotspot: the three observer-app mount tests account for about `0.27s`, and the top two `ObserverControlRoomApp.run_test()` cases account for about `0.24s`.
- Checked the slowest test bodies and confirmed the expensive cases mount the full Textual observer app, subscribe the backend, apply snapshots, pause the pilot loop, and query widgets before asserting.
- Rewrote the slow observer tests to skip full Textual mounts and instead assert direct snapshot-to-state sync plus stubbed command-input refresh behavior.
- Re-ran the targeted client file, the full suite, and the timing report; the observer client file dropped to `25` tests in `0.009s`, and the suite’s remaining slowest tests are all under `0.01s` each.

## Follow-ups

- Leave the remaining bindings/path/server/haul timing outliers alone unless the suite regresses again; none of them individually dominates runtime now.
