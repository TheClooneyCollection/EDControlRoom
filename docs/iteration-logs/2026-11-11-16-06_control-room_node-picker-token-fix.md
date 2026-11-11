# Iteration Log

- Area: `control-room`
- Title: `node-picker-token-fix`
- Started: `2026-11-11 16:06`

## Summary

- The hub's node picker never showed in a real browser. `nav.js` loads in the sidebar, before the page script that sets `window.EDCR_WEB_CONFIG`, so it captured an empty config, sent `/api/hub-status` and `/api/nodes` without the default access token, got 401 and stayed hidden. The Hub chip still worked because `hub-status.js` is deferred.
- `nav.js` now reads the config when it makes a request and asks the hub only after the document is parsed. A ship with a blank name shows its type instead of a stray separator.

## Verification

- Headless Chrome against a running hub: the picker lists the hub and a linked peer. A server test pins the script order and the lazy config read.
