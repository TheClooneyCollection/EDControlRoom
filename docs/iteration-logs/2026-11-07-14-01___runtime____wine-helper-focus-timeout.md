# Iteration Log

- Area: `runtime`
- Title: `wine-helper-focus-timeout`
- Started: `2026-11-07 14:01`

## Summary

- **Bug:** after a few live routines on main 9598814: `wine helper transport failed; ... interrupted input burst aborted`, raised from `_request('focus')`. `helper.log`: `focus_failed fg=explorer.exe err=5 child=101`, then `disconnected`.
- **Timing:** `child=101` means the child was killed at its 700ms deadline. A Wine process alone takes about 0.7s to start, so the child was mostly still starting. A focus op with the fallback took about 1.0-1.1s (`helper.log` gaps between consecutive results), right at `request_timeout_s = 1.0`, so the socket timed out and the client treated it as a transport failure.
- `focus_failed fg=EliteDangerous64.exe ... child=101`: the child focused Elite near its deadline, but success required exit code 0.

## Changes

- Helper: child focus deadline 1500ms; success is judged by the foreground after the child, whatever its exit code. Worst-case `focus` is about 1.7s.
- Client: default `request_timeout_s` 3.0 (config, `defaults/input.toml`, docs). A timed-out `focus` reconnects (dropping the late reply) and raises `FocusFailed`, which the 3x focus retry handles; other timeouts still abort the burst.

## Follow-ups

- Live retest: count `child_focus` vs `focus_failed ... child=N` in `helper.log`.
