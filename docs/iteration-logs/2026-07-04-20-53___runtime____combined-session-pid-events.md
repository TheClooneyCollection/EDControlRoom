# Iteration Log

- Area: `runtime`
- Title: `combined-session-pid-events`
- Started: `2026-07-04 20:53`

## Summary

- Switched macOS pid-targeted Quartz keyboard events to use the combined-session event source and captured the live result: native background typing works, CrossOver/Elite still does not.

## Changes

- Changed `_make_default_pid_poster()` to create pid-targeted events with `kCGEventSourceStateCombinedSessionState`, matching the background-mode pattern found in `macos-desktop-control`.
- Kept foreground macOS input on the existing HID event-tap path.
- Added a focused unit test that stubs Quartz and verifies the pid poster chooses the combined-session source.
- Live-tested background typing against Sublime successfully, which confirms the pid-targeted event construction can work for native macOS apps.
- Live-tested CrossOver/Elite with combined-session pid events and flash-focus; both failed as background-control paths, so the bottleneck appears specific to CrossOver/Elite input translation.
- Updated runtime status to record the native-app success and CrossOver/Elite limitation.

## Follow-ups

- Investigate CrossOver/Wine-specific input translation or Windows-side options before spending more effort on macOS `CGEventPostToPid` variants.
