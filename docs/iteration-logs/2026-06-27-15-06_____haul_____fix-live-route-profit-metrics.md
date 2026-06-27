# Iteration Log

- Area: `haul`
- Title: `fix-live-route-profit-metrics`
- Started: `2026-06-27 15:06`

## Summary

- Fixed live Inara route parsing so haul picker rows and the selected-route detail can show the missing trip/hour profit fields again.

## Changes

- Added profit-label alias handling in the Inara trade-route parser so live rows using `PROFIT PER LOAD` and `PROFIT/HOUR` still populate the canonical trip/hour fields.
- Extended the live-layout parser fixture to assert `profit_per_trip` and `profit_per_hour` on the current Fontana City route shape, plus a direct alias extraction unit test.
- Re-ran `uv run python3 -m unittest discover -s tests`; the suite passed in `0.318s`, then `tools/report_test_timing.py --top 10 --sort slowest` reported `suite_status=ok total_seconds=0.311` per repo policy.

## Follow-ups

- Re-check one real haul search session to confirm the live Inara DOM has not introduced any additional profit-label variants beyond the aliases now covered.
