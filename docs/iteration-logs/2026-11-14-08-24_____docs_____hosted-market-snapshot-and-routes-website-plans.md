# Iteration Log

- Area: `docs`
- Title: `hosted-market-snapshot-and-routes-website-plans`
- Started: `2026-11-14 08:24`

## Summary

- Discussed hosting the market DB so a first run, or a player back after a while, starts with data, and a public routes website on top of it. Both are written up as thought experiments for a future EDCR team, not scheduled: [plan 0017](../plans/0017-hosted-market-snapshot.md) and [plan 0018](../plans/0018-static-routes-website.md).

## Changes

- Plan 0017: a VPS runs the EDDN listener and uploads a full gzip snapshot plus `manifest.json` to Cloudflare R2 every hour or so; public, no delta packs; clients fetch on an empty DB and refresh in the background, so `eddn.enabled` stays off by default; a Cloudflare Worker serves `/status` and alarms to Discord.
- Plan 0018: an all-static website (VPS-generated files on R2, Cloudflare Pages); Global is best deals plus filtering, ranked per ton per hour, with candidates from the Pareto front over margin, route distance and station time; distances, jumps and trip time computed in the browser.
- Both plans list the rejected ideas with their reasons.
- Measured on the local DB, 2026-11-13: 18,985 markets, 1.56M prices, `VACUUM INTO` 70 MB, gzip -9 27 MB, zstd -19 21 MB; system coordinates 127,584 systems at 2.2 MB gzip (12,869 with stations, 195 KB).

## Follow-ups

- Nothing scheduled. If picked up, start with plan 0018 step 1: generate the candidates from a real DB, time and size them, and compare against `/routes`.
