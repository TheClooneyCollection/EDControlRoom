# Iteration Log

- Area: `web`
- Title: `mobile-haul-layout`
- Started: `2026-07-04 17:33`

## Summary

- Added a phone/tablet responsive layout for `web/haul-v1.html` and made `/haul` reread the HTML file on each browser reload.

## Changes

- Removed the page-level `min-width: 1160px` and added mobile breakpoints that collapse the sidebar/topbar, stack summary/forms/controls, and render route results as card-like rows below 760px.
- Added a static regression test to pin the mobile breakpoints and prevent the old desktop min-width from returning.
- Verified the static page at a 390px viewport with Playwright: document `scrollWidth` matched `clientWidth`, `.shell` resolved to `display: block`, and the route table resolved to mobile block layout.
- Changed the `/haul` Starlette route to read `web/haul-v1.html` per request and return `Cache-Control: no-store`, so editing the file only requires refreshing the browser rather than restarting `serve`.

## Follow-ups

- Live check on an actual phone or remote tablet browser once `/haul` is served from the operator host; full automatic browser live-reload would still require a watcher/SSE dev-only path.
