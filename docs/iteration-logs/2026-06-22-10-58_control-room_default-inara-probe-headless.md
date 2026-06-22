# Iteration Log

- Area: `control-room`
- Title: `default-inara-probe-headless`
- Started: `2026-06-22 10:58`

## Summary

- Switched the Inara Playwright probe to headless-by-default execution so normal runs do not briefly flash a browser window.

## Changes

- Replaced the old opt-in `--headless` flag with opt-in `--show-browser`, making invisible execution the default path for both the scratch probe and the future backend it will inform.
- Improved the access-check messaging so headless runs explicitly tell the operator to retry with `--show-browser` if manual confirmation is needed.
- Updated scratch-tool and CLI-reference docs to show both the default headless call and the visible-browser override.
- Re-ran the live probe in its new default mode against the Inara traderoutes URL; it still fetched 50 route rows successfully.
- Re-ran the full unittest suite after the UX change; `521` tests passed in `0.229s`.

## Follow-ups

- Keep the eventual shared Inara backend headless by default and reserve visible-browser mode for explicit recovery or debugging paths.
