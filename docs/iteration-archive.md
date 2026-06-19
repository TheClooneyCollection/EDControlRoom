# Iteration Archive

_This file is generated from `docs/iteration-logs/` by `uv run python3 tools/iteration_logs.py render-archive`. Refresh it whenever iteration logs change before commit, push, or PR._

- Legacy manual session baseline: `133`
- Generated iteration count: `45`
- Latest generated iteration number: `178`

## Iteration 134

- When: `2026-06-11 13:45`
- Area: `docs`
- Title: `status-split-and-promotion-automation`
- Source: [2026-06-11-13-45_____docs_____status-split-and-promotion-automation.md](iteration-logs/2026-06-11-13-45_____docs_____status-split-and-promotion-automation.md)

# Iteration Log

- Area: `docs`
- Title: `status-split-and-promotion-automation`
- Started: `2026-06-11 13:45`

## Summary

- Replaced the shared `docs/STATUS.md` handoff with split area status files under `docs/status/`, kept iteration logs as the chronological layer, and added a dedicated `dev -> main` promotion workflow branch that carries generated iteration-archive updates instead of pushing them directly onto `dev`.

## Changes

- Added `docs/status/README.md` plus durable area status files and per-area archive files, then removed the old top-level `docs/STATUS.md`.
- Updated `AGENTS.md`, `README.md`, `docs/README.md`, and the docs-planning references to point at the new status entrypoint and the new trimming/archive rules.
- Added `.github/workflows/promote-dev-to-main.yml` so `promote-dev-to-main--generated-iteration-archive` is rebuilt from `dev`, refreshed with the generated `docs/iteration-archive.md`, and used as the standing promotion PR head branch.

## Follow-ups

- Live-check the promotion workflow once merged by confirming the branch recreation, PR refresh, and token/CI behavior on GitHub.
- Watch a few real sessions to see whether any status area should be split further or collapsed back together.

## Iteration 135

- When: `2026-06-11 15:56`
- Area: `control-room`
- Title: `market-sell-revenue-wording`
- Source: [2026-06-11-15-56_control-room_market-sell-revenue-wording.md](iteration-logs/2026-06-11-15-56_control-room_market-sell-revenue-wording.md)

# Iteration Log

- Area: `control-room`
- Title: `market-sell-revenue-wording`
- Started: `2026-06-11 15:56`

## Summary

- Corrected the operator-facing and TTS wording for single `MarketSell` totals so Control Room reports sale revenue instead of profit.

## Changes

- Updated the Control Room market-sell announcement path and the default market-sell TTS text to say `revenue`.
- Added a regression test covering the single-sale wording while leaving haul/session profit tracking unchanged.

## Follow-ups

- Live-check the revised wording during a real station sale to make sure it still reads naturally in the operator activity stream and TTS output.

## Iteration 136

- When: `2026-06-11 16:16`
- Area: `haul`
- Title: `market-sell-indexing-and-config-cache`
- Source: [2026-06-11-16-16_____haul_____market-sell-indexing-and-config-cache.md](iteration-logs/2026-06-11-16-16_____haul_____market-sell-indexing-and-config-cache.md)

# Iteration Log

- Area: `haul`
- Title: `market-sell-indexing-and-config-cache`
- Started: `2026-06-11 16:16`

## Summary

- Fixed hidden-cargo sell-list indexing for market sales and removed repeated default-message reload overhead from Control Room routine launches.

## Changes

- Rebuilt the market sell list from the demand-sorted `Market.json` view plus the hidden-cargo subset from `Cargo.json` so hidden rows keep their correct cursor positions.
- Threaded `app._time_fn` through the Control Room routine launchers and cached default YAML message loads, cutting local full-suite runtime from `0.687s` to about `0.245s`.
- Added market-indexing and launcher/runtime regression coverage in `tests/test_routines.py`.

## Follow-ups

- Recheck the real market sell flow with multiple hidden cargo rows to confirm the corrected cursor math still matches the live station UI.

## Iteration 137

- When: `2026-06-11 18:47`
- Area: `haul`
- Title: `arrival-station-announcement`
- Source: [2026-06-11-18-47_____haul_____arrival-station-announcement.md](iteration-logs/2026-06-11-18-47_____haul_____arrival-station-announcement.md)

# Iteration Log

- Area: `haul`
- Title: `arrival-station-announcement`
- Started: `2026-06-11 18:47`

## Summary

- Moved the post-jump next-station callout into the haul transit routines so two-way and multi-leg haul announce the destination station at hyperspace arrival time.

## Changes

- Shifted the next-station TTS line out of the generic Control Room `FSDJump` announcement path and into the two haul transit flows.
- Added haul coverage for the new announcement timing in the two-way and multi-leg tests.

## Follow-ups

- Live-check the arrival callout timing against the real nav-panel open sequence to make sure the commander hears the station name before panel navigation starts.

## Iteration 138

- When: `2026-06-12 10:09`
- Area: `ci`
- Title: `discord-workflow-failure-notify`
- Source: [2026-06-12-10-09______ci______discord-workflow-failure-notify.md](iteration-logs/2026-06-12-10-09______ci______discord-workflow-failure-notify.md)

# Iteration Log

- Area: `ci`
- Title: `discord-workflow-failure-notify`
- Started: `2026-06-12 10:09`

## Summary

- Added a repo-level GitHub Actions failure notifier that posts failed `Tests`, `Release Please`, and `Promote Dev to Main` runs to Discord through the existing `DISCORD_WEBHOOK_URL` secret, then fixed the initial workflow YAML parse error and documented mandatory local workflow-YAML validation before push.

## Changes

- Added `.github/workflows/discord-workflow-failure-notify.yml`, triggered by `workflow_run`, with self-exclusion, metadata-rich payload formatting, and a no-secret skip path so forks or limited contexts do not fail on missing webhook configuration.
- Replaced the original embedded Python heredoc in the workflow with a YAML-safe one-line JSON payload builder after GitHub rejected the first draft on parse.
- Updated `AGENTS.md` with a standing GitHub Actions rule that future new or heavily rewritten workflows must keep the repo-wide Discord failure notification path intact and must locally parse-validate changed workflow YAML before push or PR update.
- Updated `docs/status/ci-release.md` so the current CI handoff reflects the notifier, the local YAML validation expectation, and the need for a live GitHub validation run.

## Follow-ups

- Trigger or observe one failing workflow run on GitHub to verify the Discord message formatting, branch/actor metadata, and webhook delivery end to end.

## Iteration 139

- When: `2026-06-12 10:09`
- Area: `docs`
- Title: `agent-worktree-requirement`
- Source: [2026-06-12-10-09_____docs_____agent-worktree-requirement.md](iteration-logs/2026-06-12-10-09_____docs_____agent-worktree-requirement.md)

# Iteration Log

- Area: `docs`
- Title: `agent-worktree-requirement`
- Started: `2026-06-12 10:09`

## Summary

- Updated the repo instructions so future delegated agents must work from their own git worktree and branch instead of sharing the main checkout.

## Changes

- Added explicit `AGENTS.md` rules for isolated agent worktrees/branches and for cleaning up agent worktrees after integration or discard.
- Updated `docs/status/docs-process.md` so the maintained docs-process handoff reflects the new delegated-agent isolation rule.

## Follow-ups

- Use the next agent-backed task to confirm the rule is practical in normal repo flow and tighten naming guidance only if friction shows up.

## Iteration 140

- When: `2026-06-12 10:18`
- Area: `docs`
- Title: `iteration-log-validation-workflow`
- Source: [2026-06-12-10-18_____docs_____iteration-log-validation-workflow.md](iteration-logs/2026-06-12-10-18_____docs_____iteration-log-validation-workflow.md)

# Iteration Log

- Area: `docs`
- Title: `iteration-log-validation-workflow`
- Started: `2026-06-12 10:18`

## Summary

- Added explicit iteration-log filename validation and documented the required `new` plus `validate` workflow in repo handoff instructions.

## Changes

- Added `validate_iteration_logs()` in `edap/iteration_logs.py` and a `validate` subcommand in `tools/iteration_logs.py`.
- Renamed the malformed `haul` iteration logs so they match the padded-area filename contract and no longer break archive generation.
- Updated `AGENTS.md`, `docs/iteration-logs/README.md`, and `docs/status/docs-process.md` to require tool-driven log creation and pre-commit/pre-PR validation.

## Follow-ups

- Consider wiring `uv run python3 tools/iteration_logs.py validate` into any future docs or PR-readiness automation so the rule is enforced mechanically.

## Iteration 141

- When: `2026-06-12 11:10`
- Area: `ci`
- Title: `pr13-workflow-root-cause-and-promotion-branch`
- Source: [2026-06-12-11-10______ci______pr13-workflow-root-cause-and-promotion-branch.md](iteration-logs/2026-06-12-11-10______ci______pr13-workflow-root-cause-and-promotion-branch.md)

# Iteration Log

- Area: `ci`
- Title: `pr13-workflow-root-cause-and-promotion-branch`
- Started: `2026-06-12 11:10`

## Summary

- Cherry-picked PR `#13`'s lone promotion-branch-only commit (`chore: update iteration archive`) onto a fresh `dev` worktree branch.
- Confirmed that the missing PR workflows were caused by the promotion PR being created or updated by Actions with `GITHUB_TOKEN`, which suppresses follow-on `pull_request` workflow triggers.
- Confirmed the `dev` vs `main` docs conflict is the legacy `docs/STATUS.md` and `docs/session-log.md` delete/modify collision from the split-status migration.

## Changes

- Added the generated iteration-archive update commit to `pr13-on-dev`.
- Updated `docs/status/ci-release.md` with the PR-13 workflow-trigger root cause and the token requirement for normal CI on bot-authored PRs.
- Updated `docs/status/docs-process.md` with the current promotion-conflict explanation and the preferred resolution direction.

## Follow-ups

- Merge the status/iteration-log migration onto `main` so future promotion PRs stop conflicting on the deleted legacy handoff files.
- If normal PR CI is desired on promotion and release PRs, create or reuse a PAT/App-backed `PROMOTION_PR_TOKEN` or `RELEASE_PLEASE_TOKEN` instead of relying on `GITHUB_TOKEN`.

## Iteration 142

- When: `2026-06-12 11:17`
- Area: `ci`
- Title: `promotion-dispatches-tests-with-github-token`
- Source: [2026-06-12-11-17______ci______promotion-dispatches-tests-with-github-token.md](iteration-logs/2026-06-12-11-17______ci______promotion-dispatches-tests-with-github-token.md)

# Iteration Log

- Area: `ci`
- Title: `promotion-dispatches-tests-with-github-token`
- Started: `2026-06-12 11:17`

## Summary

- Updated promotion verification to stay on `GITHUB_TOKEN` by dispatching the `Tests` workflow explicitly on the promotion branch after the PR is created or refreshed.

## Changes

- Added `workflow_dispatch` support to `.github/workflows/tests.yml`.
- Added `actions: write` permission and a follow-up `gh workflow run tests.yml --ref "$PROMOTION_BRANCH"` step to `.github/workflows/promote-dev-to-main.yml`.
- Updated `docs/status/ci-release.md` to document the new dispatch-based verification path and the remaining caveat for other bot-authored PRs.

## Follow-ups

- Live-check one promotion run after merge to confirm the explicit dispatch produces the expected `Tests` run on `promote-dev-to-main--generated-iteration-archive`.
- If `release-please` PRs also need automatic verification without separate credentials, add the same `workflow_dispatch` pattern there rather than relying on bot-authored `pull_request` events.

## Iteration 143

- When: `2026-06-13 16:29`
- Area: `ci`
- Title: `dev-branch-github-app-auth`
- Source: [2026-06-13-16-29______ci______dev-branch-github-app-auth.md](iteration-logs/2026-06-13-16-29______ci______dev-branch-github-app-auth.md)

# Iteration Log

- Area: `ci`
- Title: `dev-branch-github-app-auth`
- Started: `2026-06-13 16:29`

## Summary

- Moved promotion auth on `dev` from token-fallback auth to a GitHub App installation token generated from repo secrets so future promotion-branch rebuilds retain the change.

## Changes

- Added `actions/create-github-app-token` to `.github/workflows/promote-dev-to-main.yml`.
- Wired checkout, PR update, and workflow dispatch steps to use the generated app token via `BOT_APP_ID` and `BOT_APP_PRIVATE_KEY`.
- Updated `docs/status/ci-release.md` so the handoff reflects the GitHub App dependency and the live validation target.

## Follow-ups

- Merge this change into `dev`, then let the promotion workflow rebuild PR `#13` from `dev` so the branch no longer loses the app-auth patch on the next run.
- After merge, verify whether app-authenticated promotion updates produce PR-attached required checks or still only standalone branch-dispatched `Tests` runs.

## Iteration 144

- When: `2026-06-15 08:02`
- Area: `docs`
- Title: `main-only-release-policy`
- Source: [2026-06-15-08-02_____docs_____main-only-release-policy.md](iteration-logs/2026-06-15-08-02_____docs_____main-only-release-policy.md)

# Iteration Log

- Area: `docs`
- Title: `main-only-release-policy`
- Started: `2026-06-15 08:02`

## Summary

- Updated public-facing and maintainer docs to describe rolling updates on `main` instead of a long-lived `dev` branch.
- Documented the tradeoff explicitly: lower workflow overhead for a single maintainer, with tags and clear issue/feature-completeness notes used to signal stability.

## Changes

- Rewrote the `README.md` development section to explain the `main`-only workflow in public-facing language.
- Updated `AGENTS.md` to treat `main` as the active rolling-update branch and removed the old promotion-PR naming guidance.
- Removed stale `dev -> main` guidance from `.github/pull_request_template.md` and refreshed the related status index files.
- Deleted the legacy `.github/workflows/promote-dev-to-main.yml` workflow and removed its remaining live maintainer-doc reference.
- Added `worktrees/` to `.gitignore` so repo-local agent worktrees do not appear as untracked publish noise.
- Added a PR guard in `.github/workflows/tests.yml` that validates iteration-log filenames, renders `docs/iteration-archive.md`, and fails if the generated archive was not committed.
- Added `.github/workflows/sync-iteration-archive.yml` so same-repo PR activity regenerates and commits `docs/iteration-archive.md` automatically when iteration logs change.
- Removed `Promote Dev to Main` from the Discord notifier trigger list and made Discord webhook failures print the response body instead of only a curl status code.
- Updated the Discord notifier payload to show the first failed job and failed step first, link the workflow/repo/branch/commit/author details in markdown, and suppress Discord link previews.
- Removed `release-please` automation and restored the manual release guidance: release-prep commit, full test run, semantic version tag, and manual GitHub release publishing.

## Follow-ups

- Historical iteration logs and generated archives still mention the removed promotion path; keep those references as chronology unless history cleanup is explicitly needed.
- The current branch intentionally leaves `docs/iteration-archive.md` stale so the new PR guard can fail visibly before the archive is refreshed.
- The first notifier run for the intentional PR failure proved that the trigger path still works; after correcting the webhook URL variant locally, the remaining validation is live-render confirmation for the richer Discord message format.
- Historical docs also still mention `release-please` because they record the previous automation phase; current policy is the restored manual release flow.

## Iteration 145

- When: `2026-06-15 14:42`
- Area: `control-room`
- Title: `client-server-protocol-draft`
- Source: [2026-06-15-14-42_control-room_client-server-protocol-draft.md](iteration-logs/2026-06-15-14-42_control-room_client-server-protocol-draft.md)

# Iteration Log

- Area: `control-room`
- Title: `client-server-protocol-draft`
- Started: `2026-06-15 14:42`

## Summary

- Drafted the first Control Room client/server protocol around HTTP plus WebSocket for LAN use, with browser-compatible transport, full-word wire property names, and an explicit one-operator-plus-observers session model.

## Changes

- Added `docs/design/0002-control-room-client-server-protocol.md` with transport choice, topology, CLI direction, message vocabulary, payload contracts, and LAN/auth constraints.
- Added `docs/schemas/control_room_message.schema.json` for the versioned JSON envelope and initial command, event, state, and response payload families, including `client_role`, active-operator change events, announcement streaming, and a concrete `state.snapshot` shape mapped to current Control Room models.
- Added `docs/plans/0007-control-room-client-server-refactor.md` plus the first `edap/control_room/protocol/` Python types and `snapshot_from_app()` serializer with focused tests.
- Wired `ControlRoomApp._log()` and `ControlRoomApp._announce_tts()` into protocol-native activity-log and announcement caches so the future server path can stream existing operator outputs without changing UI behavior.
- Added a thin `ControlRoomEventSink` shim, an in-memory observer session broker, a headless runtime host, a Starlette observer server surface, and `control_room serve` wired to observer mode with tested HTTP/WebSocket endpoints.
- Updated control-room handoff status so the next session can resume from the protocol direction instead of rediscovering it.

## Follow-ups

- Extend the first serializer so replay selection and announcement history come from a real server-side state cache instead of direct app-owned lists.
- Add authentication and a concrete `connect` client path on top of the observer server surface.
- Decide whether the active operator may be explicitly transferred or only replaced by disconnect/reconnect in the first implementation.

## Iteration 146

- When: `2026-06-15 14:52`
- Area: `haul`
- Title: `optional-single-sided-haul`
- Source: [2026-06-15-14-52_____haul_____optional-single-sided-haul.md](iteration-logs/2026-06-15-14-52_____haul_____optional-single-sided-haul.md)

# Iteration Log

- Area: `haul`
- Title: `optional-single-sided-haul`
- Started: `2026-06-15 14:52`

## Summary

- Made two-station `haul` accept a blank station-1 or station-2 buy commodity as long as the opposite station still defines a valid outbound cargo leg.

## Changes

- Relaxed Control Room haul prompt and launch validation so both station buy prompts are optional, while launch still rejects the command when both buy commodities are blank.
- Updated two-way haul help text and launch labels to show missing buy legs explicitly instead of rendering an empty commodity name.
- Taught `edap.routines.haul_two_way` to skip missing buy/sell phases cleanly and to resume out of docked states by undocking immediately when the current station has no configured buy cargo.
- Added coverage for one-sided haul dispatch and one-sided haul iteration / phase-detection behavior.

## Follow-ups

- Live-test a station-1-only and station-2-only haul loop in-game to confirm menu timing, cargo detection, and resume semantics match the simulated path.

## Iteration 147

- When: `2026-06-15 15:29`
- Area: `haul`
- Title: `prefill-haul-prompt-values`
- Source: [2026-06-15-15-29_____haul_____prefill-haul-prompt-values.md](iteration-logs/2026-06-15-15-29_____haul_____prefill-haul-prompt-values.md)

# Iteration Log

- Area: `haul`
- Title: `prefill-haul-prompt-values`
- Started: `2026-06-15 15:29`

## Summary

- Changed haul prompt resume/edit to prefill the command input with the saved answers, and made blank text submission clear a field instead of restoring the previous saved text behind the operator's back.

## Changes

- Updated `edap.control_room.prompts` so haul prompt steps write the current answer into `#cmd.value`, keep the cursor at the end, and only use placeholders for guidance.
- Removed submit-time text fallback for haul station/cargo fields, so deleting a prefilled value now leaves that field empty; required fields still reject blank submission where the flow needs them.
- Changed seeded haul defaults merging so replay/edit can intentionally override a saved default with an empty string.
- Added Control Room tests covering prompt prefill and clearing a prefilled station-2 buy commodity.

## Follow-ups

- Live-test replay/edit of a saved haul entry in the real Textual UI to confirm the prefilled command box feels right and does not introduce focus/cursor quirks.

## Iteration 148

- When: `2026-06-15 16:00`
- Area: `ci-release`
- Title: `remove-auto-iteration-archive-sync`
- Source: [2026-06-15-16-00__ci-release__remove-auto-iteration-archive-sync.md](iteration-logs/2026-06-15-16-00__ci-release__remove-auto-iteration-archive-sync.md)

# Iteration Log

- Area: `ci-release`
- Title: `remove-auto-iteration-archive-sync`
- Started: `2026-06-15 16:00`

## Summary

- Removed the GitHub Actions workflow that auto-rendered and committed `docs/iteration-archive.md` back onto same-repo PR branches.
- Kept the `Tests` workflow archive-drift guard in place so archive refresh remains enforced, but now only through local/manual updates.

## Changes

- Deleted `.github/workflows/sync-iteration-archive.yml`.
- Removed the deleted workflow from `.github/workflows/discord-workflow-failure-notify.yml`.
- Updated `docs/status/ci-release.md` and `docs/status/docs-process.md` to reflect manual archive refresh instead of PR-branch auto-sync.

## Follow-ups

- If iteration logs change in a PR, refresh `docs/iteration-archive.md` locally before push so the `Tests` workflow passes.

## Iteration 149

- When: `2026-06-15 18:14`
- Area: `control-room`
- Title: `observer-auth-and-connect`
- Source: [2026-06-15-18-14_control-room_observer-auth-and-connect.md](iteration-logs/2026-06-15-18-14_control-room_observer-auth-and-connect.md)

# Iteration Log

- Area: `control-room`
- Title: `observer-auth-and-connect`
- Started: `2026-06-15 18:14`

## Summary

- Added shared-token authentication to the observer HTTP/WebSocket surface and a first observer-only `control_room connect` client that fetches authenticated snapshots, subscribes to the live session stream, prints activity/announcement events, and replays TTS locally from streamed announcement identifiers.

## Changes

- Added `ObserverServerAuth` plus `SharedAccessTokenAuth` in `edap/control_room/server/auth.py`.
- Protected `GET /capabilities`, `GET /snapshot`, and `WS /session`; left `GET /health` open for liveness probes.
- Extended `control_room serve` to require `--token`.
- Added `edap/control_room/client/connect.py` and CLI wiring for `control_room connect <host>:<port> --token ...`.
- Added client-target parsing tests and auth-aware server tests.
- Updated the protocol design note and control-room handoff status to reflect the concrete auth/connect behavior.

## Follow-ups

- Replace the thin observer CLI with the real Textual UI once the local-backend/remote-backend seam exists.
- Move session/client state ownership out of app-local caches and into a server-owned session/state layer.
- Add active-operator command routing and role enforcement after observer mode proves stable.

## Iteration 150

- When: `2026-06-15 18:15`
- Area: `haul`
- Title: `surface-landing-and-transit-fixes`
- Source: [2026-06-15-18-15_____haul_____surface-landing-and-transit-fixes.md](iteration-logs/2026-06-15-18-15_____haul_____surface-landing-and-transit-fixes.md)

# Iteration Log

- Area: `haul`
- Title: `surface-landing-and-transit-fixes`
- Started: `2026-06-15 18:15`

## Summary

- Fixed two haul regressions: intermediate jumps in multi-jump routes no longer count as destination arrival, and explicitly marked surface destinations now hand off for manual landing instead of trying to request station docking.
- Added a sell-side minimum hold floor so small-quantity commodity sells use a reliable `UI_Right` dwell even when tonnage-based timing would fall below 1 second.

## Changes

- Updated `edap/routines/haul_two_way.py` and `edap/routines/haul_multi_leg.py` to match `FSDJump` arrivals against the configured destination system, preserve the next-station nav-panel announcement, and stop cleanly with `manual landing required` for `on_land` destinations after `SupercruiseExit`.
- Extended two-way haul prompt/dispatch state to persist `station_1_on_land` / `station_2_on_land`, and extended the external multi-leg route model/schema/template with endpoint-level `on_land`.
- Added `controls.market.sell_min_hold_seconds` config plumbing and threaded it through Control Room sell/haul entry points into `edap/routines/market.py`.
- Expanded tests across config, Control Room haul prompt/dispatch, two-way haul, multi-leg haul, and market routines; full suite passed at `391 tests in 0.178s`.

## Follow-ups

- Live-check an actual settlement loop to decide whether the next iteration should automate any post-landing settlement UI or keep the current explicit handoff/resume model.
- Validate a real multi-jump haul route in-game to confirm the final-system-only nav-panel open timing feels correct with journal latency under CrossOver.

## Iteration 151

- When: `2026-06-15 18:20`
- Area: `control-room`
- Title: `local-backend-seam`
- Source: [2026-06-15-18-20_control-room_local-backend-seam.md](iteration-logs/2026-06-15-18-20_control-room_local-backend-seam.md)

# Iteration Log

- Area: `control-room`
- Title: `local-backend-seam`
- Started: `2026-06-15 18:20`

## Summary

- Added the first always-present local backend seam for embedded Control Room mode, moved snapshot/event subscription into `LocalControlRoomBackend`, switched the main status/haul/market panels to render from backend snapshots, and routed core operator input back through backend intent methods while keeping the old external event sink hook as a compatibility passthrough for observer transport.

## Changes

- Added `edap/control_room/backend.py` with `ControlRoomBackend` and `LocalControlRoomBackend`.
- `ControlRoomApp` now always owns a local backend and routes activity-log / announcement publication through it.
- The status, haul, and market panels now refresh from backend snapshots rather than directly rendering the live `_ship`, `_haul_stats`, and `_market` fields.
- Command submission, prompt confirmation, destination dispatch, and haul-loop launch now route through backend intent methods instead of direct app-private dispatch calls from the UI layer.
- Preserved `_protocol_event_sink` as a setter/getter shim backed by `_protocol_external_event_sink` so the headless observer server path keeps working unchanged.
- Added focused tests covering local backend event subscription, external sink passthrough, snapshot-driven panel rendering, and backend-routed command dispatch.
- Updated the control-room handoff and refactor plan to reflect the new backend seam.

## Follow-ups

- Move replay/history flows and the remaining UI actions onto the backend seam so local and remote clients can share the same dispatch surface.
- Replace the thin observer CLI with the real Textual UI once the remote backend exists.

## Iteration 152

- When: `2026-06-15 18:22`
- Area: `docs`
- Title: `update-agent-and-archive-policy`
- Source: [2026-06-15-18-22_____docs_____update-agent-and-archive-policy.md](iteration-logs/2026-06-15-18-22_____docs_____update-agent-and-archive-policy.md)

# Iteration Log

- Area: `docs`
- Title: `update-agent-and-archive-policy`
- Started: `2026-06-15 18:22`

## Summary

- Updated repo policy to treat `docs/iteration-archive.md` as a required refreshed artifact whenever iteration logs change before commit/push/PR, and tightened delegated-agent publish rules so slices must be committed before parent push/PR.

## Changes

- Corrected the stale `AGENTS.md` guidance that still described iteration archive refresh as optional/manual-only.
- Added explicit delegated-agent requirements in `AGENTS.md` for commit-before-publish and archive refresh before any push or PR that includes iteration-log changes.
- Updated `docs/status/docs-process.md` so the maintained handoff matches the new docs/archive and agent-publish workflow.

## Follow-ups

- Keep the workflow docs aligned with CI behavior whenever archive generation or delegated-agent publish rules change again.

## Iteration 153

- When: `2026-06-18 06:54`
- Area: `haul`
- Title: `market-hold-curve-and-sell-taps`
- Source: [2026-06-18-06-54_____haul_____market-hold-curve-and-sell-taps.md](iteration-logs/2026-06-18-06-54_____haul_____market-hold-curve-and-sell-taps.md)

# Iteration Log

- Area: `haul`
- Title: `market-hold-curve-and-sell-taps`
- Started: `2026-06-18 06:54`

## Summary

- Replaced market sell `MAX` quantity restore with configurable rapid `UI_Right` taps.
- Added configurable buy `MAX` hold timing modes plus a configurable hold cap so cargo-based hold duration can stay linear or taper with a log curve.
- Documented `log1p` in operator-facing terms and tuned the log defaults to land around `2.5s` at `300t` and `3.5s` at `700t`.

## Changes

- Added `controls.market.buy_max_hold_seconds`, `buy_hold_timing_function`, `buy_hold_log_base_seconds`, `buy_hold_log_multiplier`, `sell_quantity_restore_taps`, and `sell_quantity_restore_tap_delay_seconds`.
- Updated market, haul, and Control Room routine plumbing to pass the new quantity-adjust settings through shared trade helpers, and added an operator doc for market timing config.
- Extended config and routine tests, including coverage for the new log hold mode and sell rapid-tap behavior.

## Follow-ups

- Live-validate the log hold mode against larger cargo holds to tune operator-facing defaults before switching away from linear.

## Iteration 154

- When: `2026-06-18 06:54`
- Area: `control-room`
- Title: `replay-backend-intents`
- Source: [2026-06-18-06-54_control-room_replay-backend-intents.md](iteration-logs/2026-06-18-06-54_control-room_replay-backend-intents.md)

# Iteration Log

- Area: `control-room`
- Title: `replay-backend-intents`
- Started: `2026-06-18 06:54`

## Summary

- Moved replay-browser actions onto the backend seam so the Textual app no longer drives replay execution/edit/default-haul actions through replay-specific app-private helpers.

## Changes

- Extended `ControlRoomBackend` / `LocalControlRoomBackend` with replay-browser intents: open, close, refresh, filter update, replay selected history entry, and toggle default haul from a history entry.
- Added explicit replay wrapper methods on `ControlRoomApp` so `action_open_history()` and replay-mode key handling now go through the backend instead of `__getattr__`-resolved facade methods.
- Added focused protocol tests proving history-open and selected replay execution route through the backend seam.

## Follow-ups

- Move command-history/session ownership out of app-local state so replay/history snapshots can come from a server-owned session.
- Replace the thin observer `connect` client with a real `RemoteControlRoomBackend` that can drive the existing Textual UI.

## Iteration 155

- When: `2026-06-18 07:28`
- Area: `haul`
- Title: `segmented-market-buy-hold-timing`
- Source: [2026-06-18-07-28_____haul_____segmented-market-buy-hold-timing.md](iteration-logs/2026-06-18-07-28_____haul_____segmented-market-buy-hold-timing.md)

# Iteration Log

- Area: `haul`
- Title: `segmented-market-buy-hold-timing`
- Started: `2026-06-18 07:28`

## Summary

- Replaced the single buy-hold timing formula with ordered configurable buy-hold segments.
- Default buy timing now uses `0-99t` flat `1.0s`, `100-300t` linear, and `301t+` log tapering.

## Changes

- Added `[[controls.market.buy_hold_segments]]` config parsing and validation with per-segment `start`, `function`, and function-specific parameters.
- Updated market, Control Room, two-way haul, and multi-leg haul paths to use the new segmented buy-hold model.
- Rewrote the operator doc and example config to explain segment ordering, `log1p`, and the new default ranges.

## Follow-ups

- Live-validate the default `301t+` log segment against real large-capacity buys to see whether the post-300 drop from the linear segment should be softened.

## Iteration 156

- When: `2026-06-18 07:36`
- Area: `haul`
- Title: `haul-load-config`
- Source: [2026-06-18-07-36_____haul_____haul-load-config.md](iteration-logs/2026-06-18-07-36_____haul_____haul-load-config.md)

# Iteration Log

- Area: `haul`
- Title: `haul-load-config`
- Started: `2026-06-18 07:36`

## Summary

- Added a repo-root `haul.toml` profile plus a `haul load [path]` command path so operators can edit one text file and launch the existing two-way haul routine without the multi-step prompt.

## Changes

- Added `edap/haul_config.py` to parse a small TOML haul profile into the same parameter keys used by the existing haul dispatcher.
- Added repo-root `haul.toml` as the default editable profile file for `haul load`.
- Updated Control Room haul help, command placeholder text, and the haul launcher so `haul load` can read `haul.toml` or an explicit TOML path and then dispatch the standard two-way routine.
- Added unit coverage for haul profile parsing and for Control Room `haul load` success, default-path, missing-file, and help-text behavior.

## Follow-ups

- Live-validate the `haul load` flow in Control Room against a real edited `haul.toml` profile to confirm the operator-facing log wording and launch ergonomics.

## Iteration 157

- When: `2026-06-18 10:49`
- Area: `docs`
- Title: `document-haul-config-example`
- Source: [2026-06-18-10-49_____docs_____document-haul-config-example.md](iteration-logs/2026-06-18-10-49_____docs_____document-haul-config-example.md)

# Iteration Log

- Area: `docs`
- Title: `document-haul-config-example`
- Started: `2026-06-18 10:49`

## Summary

- Added a visible `haul.toml` example plus `haul load` guidance to user-facing docs so commanders can discover the new profile flow without reading status files or source code.

## Changes

- Updated `docs/operators/control-room.md` with `haul load [path]` guidance, a concrete `haul.toml` example, and short notes on optional buy cargo and `on_land`.
- Updated `README.md` start/haul guidance to point users at the text-editable haul profile workflow.
- Updated `docs/getting-started/quickstart.md` to point new users at the documented `haul.toml` example.

## Follow-ups

- If live use shows confusion around one-sided haul profiles or surface stops, tighten the `haul.toml` example notes with a short “common edits” section.

## Iteration 158

- When: `2026-06-18 10:58`
- Area: `control-room`
- Title: `home-command-config`
- Source: [2026-06-18-10-58_control-room_home-command-config.md](iteration-logs/2026-06-18-10-58_control-room_home-command-config.md)

# Iteration Log

- Area: `control-room`
- Title: `home-command-config`
- Started: `2026-06-18 10:58`

## Summary

- Added a reusable `home` command that routes to `control_room.home_system`, plus `home set <system>` to persist that destination into config from Control Room itself.

## Changes

- Extended `ControlRoomConfig` with `home_system`, added config load coverage, and implemented a narrow TOML upsert helper that updates or creates a valid repo-root `config.toml` when the app was running from the default example-config fallback.
- Routed `home` through the existing `dest` flow so the normal galaxy-map settle prompt, history logging, and navigation behavior stay shared.
- Updated command help, placeholder text, `config.example.toml`, quickstart/operator docs, and README so the new route shortcut is discoverable.
- Added command/config tests for `home`, `home set`, existing-config updates, and fallback-config creation.
- Verified with `uv run python3 -m unittest discover -s tests` (`411` tests, `0.172s`).

## Follow-ups

- Live-check the new `home` shortcut and `home set` config write path against a real CrossOver-backed operator setup.

## Iteration 159

- When: `2026-06-18 11:12`
- Area: `docs`
- Title: `retroactive-release-backfill`
- Source: [2026-06-18-11-12_____docs_____retroactive-release-backfill.md](iteration-logs/2026-06-18-11-12_____docs_____retroactive-release-backfill.md)

# Iteration Log

- Area: `docs`
- Title: `retroactive-release-backfill`
- Started: `2026-06-18 11:12`

## Summary

- Backfilled stable release milestones after `v1.7.3` into three coherent cuts: `v1.8.0`, `v1.9.0`, and `v1.10.0`.

## Changes

- Tagged `f0e99ce` as `v1.8.0` for the standalone multi-leg haul and control-room/operator improvements tranche.
- Tagged `36411f1` as `v1.9.0` for the haul-loop, arrival/sell timing, and release-process hardening tranche.
- Prepared `main` for `v1.10.0` by bumping `[project].version` to match the configurable timing/routing milestone at `HEAD`.
- Updated `docs/status/ci-release.md` to record the retroactive-tagging exception and the current stable tag state.

## Follow-ups

- Run `uv sync`, validate the full unittest suite, refresh `docs/iteration-archive.md`, and publish the GitHub releases for the backfilled tags.

## Iteration 160

- When: `2026-06-18 11:19`
- Area: `control-room`
- Title: `home-set-current-system`
- Source: [2026-06-18-11-19_control-room_home-set-current-system.md](iteration-logs/2026-06-18-11-19_control-room_home-set-current-system.md)

# Iteration Log

- Area: `control-room`
- Title: `home-set-current-system`
- Started: `2026-06-18 11:19`

## Summary

- `home set` now uses the current detected ship system when no explicit system name is provided, so commanders can save home with one short command after bootstrap/live sync has populated the current location.

## Changes

- Updated the `home` command parser so both `home set <system>` and bare `home set` share the same config-write path.
- Added a specific operator-facing message for the case where Control Room still does not know the current system, instead of falling back to generic usage text.
- Added dispatch tests for the inferred-current-system path and the unknown-current-system failure path, and refreshed the user-facing docs/help text to mention the shortcut.
- Verified with `uv run python3 -m unittest discover -s tests` (`413` tests, `0.232s`), then ran `UV_CACHE_DIR=/private/tmp/uv-cache uv run python3 tools/report_test_timing.py --top 10 --sort slowest` per repo policy (`0.222s` total in the timing report).

## Follow-ups

- Live-check that `home set` picks the expected system after bootstrap on a real session, especially when Control Room inferred location from `Status.json` or market state rather than a fresh jump/location journal event.

## Iteration 161

- When: `2026-06-18 11:34`
- Area: `docs`
- Title: `test-runtime-threshold-0-3`
- Source: [2026-06-18-11-34_____docs_____test-runtime-threshold-0-3.md](iteration-logs/2026-06-18-11-34_____docs_____test-runtime-threshold-0-3.md)

# Iteration Log

- Area: `docs`
- Title: `test-runtime-threshold-0-3`
- Started: `2026-06-18 11:34`

## Summary

- Raised the repo’s enforced full-suite timing budget from `0.2s` to `0.3s` so the current test count can grow without forcing a timing-report follow-up on otherwise acceptable runs.

## Changes

- Updated the `AGENTS.md` testing rule so `uv run python3 -m unittest discover -s tests` is considered on budget through `0.3s`.
- Updated the docs-process handoff status file to reflect the new timing threshold for future sessions.
- Verified with `uv run python3 -m unittest discover -s tests` (`413` tests, runtime captured in this session below the new `0.3s` budget).

## Follow-ups

- If the suite starts trending toward `0.3s`, revisit consolidation or targeted test-speed cleanup before raising the threshold again.

## Iteration 162

- When: `2026-06-18 12:22`
- Area: `haul`
- Title: `retune-default-market-buy-hold-curve`
- Source: [2026-06-18-12-22_____haul_____retune-default-market-buy-hold-curve.md](iteration-logs/2026-06-18-12-22_____haul_____retune-default-market-buy-hold-curve.md)

# Iteration Log

- Area: `haul`
- Title: `retune-default-market-buy-hold-curve`
- Started: `2026-06-18 12:22`

## Summary

- Retuned the shipped market buy `MAX` defaults around longer stable holds for small and mid-size cargo loads.
- Raised the default buy-hold cap to `20.0s` and re-fit the `301t+` log segment to start at `5.0s` around `301t` and reach about `8.0s` at `800t`.

## Changes

- Updated the default config loader, routine fallback defaults, example config, and operator market-timing doc to use the new hold curve.
- Updated routine and config tests to assert the new shipped defaults and progress output.

## Follow-ups

- Live-validate the new `301t+` curve in Odyssey/CrossOver to confirm the longer default dwell no longer undershoots large buys.
-

## Changes

-

## Follow-ups

-

## Iteration 163

- When: `2026-06-18 12:25`
- Area: `docs`
- Title: `prepare-v1-11-0-release`
- Source: [2026-06-18-12-25_____docs_____prepare-v1-11-0-release.md](iteration-logs/2026-06-18-12-25_____docs_____prepare-v1-11-0-release.md)

# Iteration Log

- Area: `docs`
- Title: `prepare-v1-11-0-release`
- Started: `2026-06-18 12:25`

## Summary

- Prepared `main` for the `v1.11.0` release so the current milestone can be cut before the pending larger merge lands.

## Changes

- Bumped `[project].version` in `pyproject.toml` from `1.10.0` to `1.11.0` for the release-prep commit.
- Updated `docs/status/ci-release.md` to record that `main` now points at the `v1.11.0` release-prep state.

## Follow-ups

- Run `uv sync`, validate the full unittest suite, refresh `docs/iteration-archive.md`, commit the release-prep change, and tag `v1.11.0`.

## Iteration 164

- When: `2026-06-18 12:43`
- Area: `control-room`
- Title: `remote-observer-tui-backend`
- Source: [2026-06-18-12-43_control-room_remote-observer-tui-backend.md](iteration-logs/2026-06-18-12-43_control-room_remote-observer-tui-backend.md)

# Iteration Log

- Area: `control-room`
- Title: `remote-observer-tui-backend`
- Started: `2026-06-18 12:43`

## Summary

- Added live observer snapshot broadcasting and replaced the thin `connect` observer CLI with an app-backed remote observer client that reuses the existing Textual Control Room surface in read-only mode.

## Changes

- Extended `ControlRoomEventSink` with snapshot publication and taught the in-memory observer broker to retain the latest base snapshot, merge connected-client state into it, and fan out `state.snapshot` messages to all observer sessions.
- Seeded the broker with the startup snapshot in `serve`, rebroadcasted snapshots on observer connect/disconnect, and published fresh snapshots from the control-room event path after journal-driven state changes, including moving dock-market reload ahead of snapshot emission so observers see updated market data.
- Added a wire-message parser, a `RemoteObserverBackend`, and an observer-mode `ControlRoomApp` mount path so `connect` now renders the existing status/haul/market/activity surfaces from streamed snapshots and announcement events instead of printing lines to stdout.
- Added regression coverage for broker snapshot fan-out, wire parsing, remote-backend read-only behavior, and app-to-sink snapshot publication, then re-ran compile checks and the full unittest suite.

## Follow-ups

- Remote operator commands, remote replay actions, and broader session ownership still need to move onto the backend seam before the same Textual client can take the active-operator role instead of observer-only mode.

## Iteration 165

- When: `2026-06-18 20:15`
- Area: `control-room`
- Title: `session-command-transport`
- Source: [2026-06-18-20-15_control-room_session-command-transport.md](iteration-logs/2026-06-18-20-15_control-room_session-command-transport.md)

# Iteration Log

- Area: `control-room`
- Title: `session-command-transport`
- Started: `2026-06-18 20:15`

## Summary

- Added bidirectional WebSocket session command handling, wired active-operator submit callbacks into the headless host, and kept observer sessions on explicit correlated protocol errors for operator commands.

## Changes

- Extended the server session loop to receive client envelopes as well as push broker events, and added protocol handling for `command.request_snapshot`, unsupported message errors, and observer rejection for `command.submit_input`.
- Added outbound command queuing and response handling to `RemoteObserverBackend`, so the remote client can issue protocol commands and surface `response.error` or `response.success` messages locally.
- Added a minimal headless command-input stub plus server-side submit callback wiring so active-operator sessions can drive simple remote inputs through the existing command parser and prompt state.
- Personalized `state.snapshot` payloads per session so future active-operator promotion can change `session.client_role` and `active_operator` cleanly without a shared-broadcast mismatch.
- Added focused tests for correlated snapshot responses, observer command rejection, active-operator command acceptance, headless-host remote input, session-personalized snapshots, and remote backend command queue behavior, then re-ran compile checks and the full unittest suite.

## Follow-ups

- The next slice is the actual promotion policy and trigger path for assigning a connected session as `active_operator`, followed by broader validation of routine-heavy remote commands in the headless host.

## Iteration 166

- When: `2026-06-18 22:49`
- Area: `control-room`
- Title: `active-operator-promotion`
- Source: [2026-06-18-22-49_control-room_active-operator-promotion.md](iteration-logs/2026-06-18-22-49_control-room_active-operator-promotion.md)

# Iteration Log

- Area: `control-room`
- Title: `active-operator-promotion`
- Started: `2026-06-18 22:49`

## Summary

- Implemented the first active-operator promotion policy: the first authenticated client becomes the operator automatically, later authenticated clients can claim the role explicitly, and role-aware snapshots now track that assignment end to end.

## Changes

- Updated the observer-session broker to auto-promote the first authenticated client, allow explicit operator claims, and fail over to the next connected client when the current operator disconnects.
- Extended the session protocol with `command.request_active_operator`, updated `connection_ready` and snapshot payloads to reflect the broker-assigned role, and exposed `--claim-operator` on `control_room connect`.
- Added regression coverage for auto-promotion, explicit claim, and role-aware snapshot payloads, then re-ran compile checks and the full unittest suite.

## Follow-ups

- The main remaining work is live validation and broader routine/prompt coverage through the headless host now that role assignment, command transport, and simple command execution are all in place.

## Iteration 167

- When: `2026-06-18 23:25`
- Area: `runtime`
- Title: `status-file-autodock-flags-note`
- Source: [2026-06-18-23-25___runtime____status-file-autodock-flags-note.md](iteration-logs/2026-06-18-23-25___runtime____status-file-autodock-flags-note.md)

# Iteration Log

- Area: `runtime`
- Title: `status-file-autodock-flags-note`
- Started: `2026-06-18 23:25`

## Summary

- Checked the Elite Journal `Status File` reference against the current `edap/status.py` parser to answer whether `Status.json` can reveal auto-docking or auto-launch state.

## Changes

- Confirmed the repo already matches the documented `Flags` table used by `Status.json`.
- Confirmed the documented `Flags2` table adds on-foot, glide, FSD-hyperdrive, SCO, and supercruise-assist state, but no auto-docking or auto-launch bits.
- Updated `docs/status/runtime.md` so the runtime handoff explicitly states that docking-computer state still comes from journal/music cues rather than `Status.json`.

## Follow-ups

- If operator UX needs more status-file visibility later, add `Flags2` parsing for documented fields such as `Supercruise Assist Active`, but do not expect it to answer autodock/autolaunch.

## Iteration 168

- When: `2026-06-18 23:30`
- Area: `control-room`
- Title: `restore-prompt-enter-defaults`
- Source: [2026-06-18-23-30_control-room_restore-prompt-enter-defaults.md](iteration-logs/2026-06-18-23-30_control-room_restore-prompt-enter-defaults.md)

# Iteration Log

- Area: `control-room`
- Title: `restore-prompt-enter-defaults`
- Started: `2026-06-18 23:30`

## Summary

- Restored prompt-default Enter handling for Control Room prompts by catching blank Enter at the key-event layer and routing it through backend prompt submission.
- Verified the fix for both embedded and connected active-operator flows by keeping blank `raw_input` valid over the session transport and covering both paths with focused tests.

## Changes

- Updated `ControlRoomApp.on_key()` to submit empty prompt input on `Enter` during destination/haul prompt flows instead of relying on widget-level submitted events.
- Kept `on_input_submitted()` prompt-aware so non-empty and already-submitted prompt values still route through the backend without normal command-mode stripping.
- Added protocol/UI regression coverage for blank Enter during destination prompts and server-side coverage for active-operator command submission handling.

## Follow-ups

- Live-test connected active-operator prompt flows against a running `serve` instance, especially multi-step haul prompts and other prompt-heavy commands.

## Iteration 169

- When: `2026-06-18 23:36`
- Area: `control-room`
- Title: `push-snapshots-after-remote-input`
- Source: [2026-06-18-23-36_control-room_push-snapshots-after-remote-input.md](iteration-logs/2026-06-18-23-36_control-room_push-snapshots-after-remote-input.md)

# Iteration Log

- Area: `control-room`
- Title: `push-snapshots-after-remote-input`
- Started: `2026-06-18 23:36`

## Summary

- Fixed a remote-only sync bug where the server accepted operator input but did not immediately push a fresh snapshot afterward, leaving connected clients with stale state for prompt and market transitions.

## Changes

- Updated `HeadlessControlRoomHost.handle_remote_input()` to publish a fresh snapshot through the configured protocol sink after backend input handling completes.
- Added server coverage that verifies remote input now produces a new published snapshot reflecting the updated host state.

## Follow-ups

- Live-test `dest`, `haul`, and other prompt-heavy commands over `connect` against a running `serve` instance now that post-input snapshot pushes are explicit.

## Iteration 170

- When: `2026-06-19 11:49`
- Area: `docs`
- Title: `regenerate-iteration-archive-conflicts`
- Source: [2026-06-19-11-49_____docs_____regenerate-iteration-archive-conflicts.md](iteration-logs/2026-06-19-11-49_____docs_____regenerate-iteration-archive-conflicts.md)

# Iteration Log

- Area: `docs`
- Title: `regenerate-iteration-archive-conflicts`
- Started: `2026-06-19 11:49`

## Summary

- Added an explicit repo rule that `docs/iteration-archive.md` must be regenerated, not hand-merged, whenever it conflicts during a merge or rebase.
- Applied that rule while rebasing `codex/control-room-remote-followup` onto the latest `origin/main`, which avoided repeated manual conflict resolution on the generated archive.

## Changes

- Updated `AGENTS.md` to require `uv run python3 tools/iteration_logs.py render-archive` plus staging the regenerated file whenever the archive conflicts.
- Updated `docs/status/docs-process.md` so the current handoff reflects the same generated-file conflict policy for future agents.

## Follow-ups

- Keep using regeneration for future archive conflicts and treat any hand-merged archive content as suspect until re-rendered from `docs/iteration-logs/`.

## Iteration 171

- When: `2026-06-19 11:58`
- Area: `control-room`
- Title: `add-server-session-state-cache`
- Source: [2026-06-19-11-58_control-room_add-server-session-state-cache.md](iteration-logs/2026-06-19-11-58_control-room_add-server-session-state-cache.md)

# Iteration Log

- Area: `control-room`
- Title: `add-server-session-state-cache`
- Started: `2026-06-19 11:58`

## Summary

- Added a thin in-memory `ControlRoomServerState` behind the observer broker so remote sessions get server-owned activity history and retained announcement events instead of depending only on app-private caches.

## Changes

- Added `edap/control_room/server/state.py` with capped activity-log and announcement retention plus snapshot merge support.
- Updated `InMemoryObserverSessionBroker` to record activity/announcement events into server state and to reapply retained activity history whenever it serves or rebroadcasts snapshots.
- Added tests covering new-session snapshot history replay and capped announcement retention.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py`, `uv run python3 -m compileall edap tests`, and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Move replay-browser/session-owned state onto the same server-side seam so connect clients stop relying on app-local replay caches.
- Decide whether retained announcement history should be exposed directly to future web clients or only kept for reconnect/session continuity.

## Iteration 172

- When: `2026-06-19 12:06`
- Area: `control-room`
- Title: `add-remote-replay-command-transport`
- Source: [2026-06-19-12-06_control-room_add-remote-replay-command-transport.md](iteration-logs/2026-06-19-12-06_control-room_add-remote-replay-command-transport.md)

# Iteration Log

- Area: `control-room`
- Title: `add-remote-replay-command-transport`
- Started: `2026-06-19 12:06`

## Summary

- Added real remote replay command transport so active operators in `connect` mode can open/filter/close replay history, replay entries, and toggle default haul through the headless server instead of hitting local “not available yet” shims.

## Changes

- Added an `ObserverSessionCommandHandler` shim for server-side session commands and extended WebSocket command handling to support replay-browser open/close, replay filtering, replay execution/edit, and default-haul toggling.
- Taught `HeadlessControlRoomHost` to stub the replay widgets/styles that the existing replay helpers expect, then publish fresh snapshots after replay-state mutations.
- Updated `RemoteObserverBackend` to send real replay command envelopes and added server/client regression coverage for the new command set.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py tests/test_control_room_client.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Live-validate remote replay flows against real history entries, especially `haul` edit/execute and `dest` edit prompts under the headless host.
- Decide whether replay-browser selection/highlight state should remain a client-local concern or be promoted into the server session model for future web clients.

## Iteration 173

- When: `2026-06-19 12:08`
- Area: `control-room`
- Title: `snapshot-selected-replay-entry`
- Source: [2026-06-19-12-08_control-room_snapshot-selected-replay-entry.md](iteration-logs/2026-06-19-12-08_control-room_snapshot-selected-replay-entry.md)

# Iteration Log

- Area: `control-room`
- Title: `snapshot-selected-replay-entry`
- Started: `2026-06-19 12:08`

## Summary

- Added replay-browser selection/highlight to `state.snapshot` so remote clients and future web clients can see which saved history entry the server-side replay browser currently has selected.

## Changes

- Updated `snapshot_from_app()` to populate `replay_browser.selected_history_entry` from the current replay-list highlight when the replay browser is open.
- Covered the serializer path directly and through the headless-server replay flow so replay snapshots now include the selected saved entry after remote replay-browser actions.
- Verified with `uv run python3 -m unittest tests/test_control_room_protocol.py tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.
- Ran the required timing breakdown after the full suite reported `1.241s`; `tools/report_test_timing.py` showed no single dominant regression, with the slowest test at `0.061s`.

## Follow-ups

- Decide whether replay selection should become broker-owned session state instead of remaining a serialized reflection of the app/headless host state.
- Keep an eye on full-suite timing on the next slices in case the slower wall-clock run reflects environment drift rather than this change.

## Iteration 174

- When: `2026-06-19 12:27`
- Area: `control-room`
- Title: `broker-serve-retained-snapshots`
- Source: [2026-06-19-12-27_control-room_broker-serve-retained-snapshots.md](iteration-logs/2026-06-19-12-27_control-room_broker-serve-retained-snapshots.md)

# Iteration Log

- Area: `control-room`
- Title: `broker-serve-retained-snapshots`
- Started: `2026-06-19 12:27`

## Summary

- Moved `/snapshot`, websocket connection bootstrap, and `command.request_snapshot` onto the broker’s retained latest snapshot path so the session layer serves its current merged view instead of always asking the headless app for a fresh direct snapshot.

## Changes

- Added `InMemoryObserverSessionBroker.current_snapshot()` to return the retained merged snapshot when available and fall back to the runtime snapshot provider only when the broker has not seen state yet.
- Updated the observer HTTP and WebSocket server paths to prefer that retained broker snapshot for health/capabilities/snapshot responses, connection-ready bootstrap, and correlated snapshot requests.
- Added coverage proving `/snapshot` returns the broker-retained snapshot even when the provider would still report an older base view.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Decide whether future web clients should read the retained broker snapshot directly through a thinner API layer instead of going back through the headless host at all.
- Keep moving prompt-flow and the remaining replay/session ownership off the app instance now that the broker has a clearer retained-snapshot seam.

## Iteration 175

- When: `2026-06-19 12:27`
- Area: `control-room`
- Title: `server-mirror-activity-and-disable-local-tts`
- Source: [2026-06-19-12-27_control-room_server-mirror-activity-and-disable-local-tts.md](iteration-logs/2026-06-19-12-27_control-room_server-mirror-activity-and-disable-local-tts.md)

# Iteration Log

- Area: `control-room`
- Title: `server-mirror-activity-and-disable-local-tts`
- Started: `2026-06-19 12:27`

## Summary

- Changed `serve` so the headless server no longer speaks TTS locally, while connected clients still receive announcement events and can speak them client-side; server-side activity log entries are now mirrored into server logs.

## Changes

- Forced `HeadlessControlRoomHost` to build its `TTSAnnouncer` with a `NullSpeechBackend`, which keeps `event.announcement_emitted` intact but suppresses local server speech.
- Added `ServerActivityLogSink` plus a small fan-out sink so `serve` mirrors protocol activity-log entries into server logs alongside the broker session stream.
- Added server tests covering announcement-event emission without local speech and activity-log mirroring into a logger.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Live-check the `serve` console output during real routine runs to make sure the mirrored activity lines are the right signal density for operators.
- If the server needs structured logs later, replace the current plain mirrored message sink with a JSON or field-based logger instead of changing the activity event shape.

## Iteration 176

- When: `2026-06-19 13:12`
- Area: `control-room`
- Title: `split-remote-interrupt-and-exit-controls`
- Source: [2026-06-19-13-12_control-room_split-remote-interrupt-and-exit-controls.md](iteration-logs/2026-06-19-13-12_control-room_split-remote-interrupt-and-exit-controls.md)

# Iteration Log

- Area: `control-room`
- Title: `split-remote-interrupt-and-exit-controls`
- Started: `2026-06-19 13:12`

## Summary

- Split connected-client quit controls so remote `Ctrl-C` requests routine cancellation while `Ctrl-D` becomes a two-step local exit with a remote-routine detach/cancel prompt.

## Changes

- Added backend/server command shims for `command.cancel_active_routine` so remote operators can interrupt server-side work without sending `quit` to the headless host.
- Split `ControlRoomApp` bindings into interrupt vs exit actions, made terminal `SIGINT` follow the interrupt path, and added the local confirmation flow for exiting a connected active-operator client while a remote routine is still running.
- Added regression coverage across app, client, and server tests for remote interrupt transport and the new exit semantics.

## Follow-ups

- Live-validate the new `Ctrl-C`/`Ctrl-D` flow against a real connected client, especially during haul and prompt-heavy routines, before merging another remote-control slice on top.

## Iteration 177

- When: `2026-06-19 13:46`
- Area: `control-room`
- Title: `fix-remote-routine-state-teardown`
- Source: [2026-06-19-13-46_control-room_fix-remote-routine-state-teardown.md](iteration-logs/2026-06-19-13-46_control-room_fix-remote-routine-state-teardown.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-remote-routine-state-teardown`
- Started: `2026-06-19 13:46`

## Summary

- Fixed stale remote active-routine state after routine completion and guarded remote cancel against a missing server-side worker.

## Changes

- Published a fresh protocol snapshot from routine teardown so `serve`/`connect` clients stop seeing completed routines as still active.
- Hardened `_cancel_active_routine()` so stale or already-finished routines log cleanly instead of throwing `'NoneType' object has no attribute 'cancel'`.
- Added regression coverage for stale routine cancellation and teardown snapshot publication, then reran focused control-room tests plus the full suite.

## Follow-ups

- Live-validate the dock/undock and haul completion path over a real remote session to confirm the client prompt state now clears immediately after completion.

## Iteration 178

- When: `2026-06-19 14:10`
- Area: `control-room`
- Title: `remote-prompt-interrupt`
- Source: [2026-06-19-14-10_control-room_remote-prompt-interrupt.md](iteration-logs/2026-06-19-14-10_control-room_remote-prompt-interrupt.md)

# Iteration Log

- Area: `control-room`
- Title: `remote-prompt-interrupt`
- Started: `2026-06-19 14:10`

## Summary

- Fixed the remote `Ctrl-C` gap where active-operator clients could cancel routines but could not back out of prompt flows like haul setup, haul confirm, or destination settle.

## Changes

- Added a shared prompt-cancellation helper in `edap/control_room/prompts.py` that clears prompt state, restores the command placeholder, and logs the cancelled flow.
- Routed both local backend interrupts and headless server-host remote interrupts through the same app-level `_handle_interrupt()` path so prompt cancellation runs before routine cancellation.
- Added regressions covering local prompt `Ctrl-C`, remote-client prompt `Ctrl-C` forwarding, and remote host prompt-state clearing plus snapshot publication.

## Follow-ups

- Live-validate remote active-operator prompt cancellation against real haul and destination flows under `serve` / `connect`.
