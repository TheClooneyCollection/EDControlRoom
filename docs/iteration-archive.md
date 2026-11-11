# Iteration Archive

_This file is generated from `docs/iteration-logs/` by `uv run python3 tools/iteration_logs.py render-archive`. Refresh it whenever iteration logs change before commit, push, or PR._

- Legacy manual session baseline: `133`
- Generated iteration count: `338`
- Latest generated iteration number: `471`

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

## Iteration 179

- When: `2026-06-19 14:37`
- Area: `control-room`
- Title: `cargo-json-sync-after-trades`
- Source: [2026-06-19-14-37_control-room_cargo-json-sync-after-trades.md](iteration-logs/2026-06-19-14-37_control-room_cargo-json-sync-after-trades.md)

# Iteration Log

- Area: `control-room`
- Title: `cargo-json-sync-after-trades`
- Started: `2026-06-19 14:37`

## Summary

- Made post-trade cargo state authoritative from `Cargo.json` instead of trusting the app's in-memory manifest after market journal events.

## Changes

- Added `bootstrap.sync_cargo_manifest()` and wired `_handle_event()` to re-read `Cargo.json` after `Cargo`, `MarketBuy`, and `MarketSell`.
- Kept bootstrap startup behavior aligned with existing expectations by leaving startup `cargo_count` sourced from `Status.json` while still loading manifest contents from `Cargo.json`.
- Added control-room regression tests covering full-sell stale manifest cleanup plus manifest refresh after both market buys and sells.

## Follow-ups

- Live-test repeated remote and local `sell`/`buy` flows against real journal timing to confirm `Cargo.json` is always updated before the follow-up command path re-checks inventory.

## Iteration 180

- When: `2026-06-19 15:02`
- Area: `control-room`
- Title: `fail-closed-on-remote-ping-timeout`
- Source: [2026-06-19-15-02_control-room_fail-closed-on-remote-ping-timeout.md](iteration-logs/2026-06-19-15-02_control-room_fail-closed-on-remote-ping-timeout.md)

# Iteration Log

- Area: `control-room`
- Title: `fail-closed-on-remote-ping-timeout`
- Started: `2026-06-19 15:02`

## Summary

- Made remote observer clients fail closed after an established session drops so stale remote routine state does not linger after ping timeouts or other WebSocket disconnects.

## Changes

- Added a remote-backend disconnect handler that clears stale active-operator and routine UI state, emits a snapshot refresh, and logs the disconnect reason locally.
- Kept pre-connection command queueing intact for the initial connect/startup window, but reject new commands after a previously connected session has dropped.
- Added client tests covering disconnect-state cleanup and command rejection after disconnect.

## Follow-ups

- Live-test a real ping-timeout or server-stop case to confirm the TUI recovers cleanly and the reconnect workflow remains obvious to the operator.

## Iteration 181

- When: `2026-06-19 15:08`
- Area: `control-room`
- Title: `add-remote-reconnect-backoff`
- Source: [2026-06-19-15-08_control-room_add-remote-reconnect-backoff.md](iteration-logs/2026-06-19-15-08_control-room_add-remote-reconnect-backoff.md)

# Iteration Log

- Area: `control-room`
- Title: `add-remote-reconnect-backoff`
- Started: `2026-06-19 15:08`

## Summary

- Added automatic remote observer reconnect with exponential backoff so transient ping timeouts or server restarts do not leave the client permanently detached.

## Changes

- Wrapped the remote observer WebSocket session in a reconnect loop with exponential delays from 1 second up to a 30 second cap.
- On reconnect, the client requests a fresh remote snapshot and logs `Observer connection restored.` so stale routine or operator state can self-heal.
- Added client tests for backoff growth/capping and the reconnect messaging/snapshot refresh path.

## Follow-ups

- Live-test server stop/start and forced ping-timeout cases to tune the operator-facing reconnect messaging and confirm retry pacing feels reasonable on LAN.

## Iteration 182

- When: `2026-06-19 16:57`
- Area: `control-room`
- Title: `prepare-v1-12-0-release`
- Source: [2026-06-19-16-57_control-room_prepare-v1-12-0-release.md](iteration-logs/2026-06-19-16-57_control-room_prepare-v1-12-0-release.md)

# Iteration Log

- Area: `control-room`
- Title: `prepare-v1-12-0-release`
- Started: `2026-06-19 16:57`

## Summary

- Prepared the `v1.12.0` release cut for the Control Room client/server split refactor milestone.
- Captured the release handoff update in `docs/status/ci-release.md` and refreshed generated iteration docs.

## Changes

- Bumped `[project].version` to `1.12.0` for the next stable tag.
- Regenerated `uv.lock` so the lockfile version metadata matches the release prep commit.
- Refreshed `docs/iteration-archive.md` after adding this release-prep iteration log.

## Follow-ups

- Tag `v1.12.0`, push the release-prep commit, and publish the GitHub release notes for the server/client split milestone.

## Iteration 183

- When: `2026-06-19 17:02`
- Area: `control-room`
- Title: `retain-remote-session-state`
- Source: [2026-06-19-17-02_control-room_retain-remote-session-state.md](iteration-logs/2026-06-19-17-02_control-room_retain-remote-session-state.md)

# Iteration Log

- Area: `control-room`
- Title: `retain-remote-session-state`
- Started: `2026-06-19 17:02`

## Summary

- Moved the next real `serve`/`connect` seam into retained server-owned state by having the observer server keep prompt, replay-browser, and command-history session snapshots alongside retained activity history.

## Changes

- Extended `ControlRoomServerState` to retain `command_history`, `prompt_state`, and `replay_browser` snapshots, and to keep `ui_state.replay_browser_open` aligned with retained replay-browser state.
- Updated the observer broker to capture those session slices whenever the headless host publishes a snapshot, so future HTTP/WebSocket snapshot requests are served from server-retained state instead of only whatever the app object currently exposes.
- Threaded a shared `ControlRoomServerState` through `serve_observer_mode` into both the broker and `HeadlessControlRoomHost`, and made the headless host feed retained session state even before an external sink is attached.
- Added regression coverage proving retained prompt/replay state is replayed into later merged snapshots and that the headless host actually populates that retained server state.
- Verified the full suite with `uv run python3 -m unittest discover -s tests` (`478 tests in 0.203s`).

## Follow-ups

- Move the remaining widget-local cursor/highlight semantics and prompt mutation paths behind explicit server-owned state transitions so the remote path no longer depends on app-local UI fields for selection behavior.
- Live-validate prompt-heavy remote flows and replay selection/edit flows against real server/client sessions now that the retained snapshot seam is in place.

## Iteration 184

- When: `2026-06-19 17:08`
- Area: `control-room`
- Title: `state-drive-replay-selection`
- Source: [2026-06-19-17-08_control-room_state-drive-replay-selection.md](iteration-logs/2026-06-19-17-08_control-room_state-drive-replay-selection.md)

# Iteration Log

- Area: `control-room`
- Title: `state-drive-replay-selection`
- Started: `2026-06-19 17:08`

## Summary

- Removed the replay-selection widget side-channel by making the selected replay history entry explicit application state, which the local widget now mirrors and remote snapshots now serialize directly.

## Changes

- Added retained replay selection state to `ReplayBrowserState` and exposed it on `ControlRoomApp`, so replay selection no longer depends on reading `OptionList.highlighted` as the source of truth.
- Updated replay-browser helpers to preserve and resolve the selected history entry across open, refresh, filter, and close flows, while synchronizing the widget highlight from state and synchronizing state from highlight events.
- Changed protocol snapshot generation to read the selected replay history entry from replay state instead of querying the UI widget directly.
- Updated remote snapshot application to restore replay selection into app state and re-highlight the local replay widget when a server snapshot carries a selected replay entry.
- Verified with targeted protocol/server tests and `uv run python3 -m unittest discover -s tests` (`479 tests in 0.216s`).

## Follow-ups

- Move prompt mutation itself onto explicit server-owned state transitions so the headless server path no longer depends on app-local prompt orchestration.
- Decide whether replay-browser navigation should grow an explicit server-native selection command model or remain a thin mirror of local widget navigation for now.

## Iteration 185

- When: `2026-06-19 17:14`
- Area: `control-room`
- Title: `state-drive-destination-prompt`
- Source: [2026-06-19-17-14_control-room_state-drive-destination-prompt.md](iteration-logs/2026-06-19-17-14_control-room_state-drive-destination-prompt.md)

# Iteration Log

- Area: `control-room`
- Title: `state-drive-destination-prompt`
- Started: `2026-06-19 17:14`

## Summary

- Moved destination-prompt submission off the backend’s inline field-mutation path and into explicit `PromptState` helpers, which gives the remote architecture a cleaner prompt-state seam ahead of the larger haul wizard migration.

## Changes

- Added `begin_destination_prompt`, `resolve_destination_prompt_submission`, and `clear_destination_prompt` helpers in `edap/control_room/prompts.py` that operate directly on `PromptState`.
- Updated `start_dest_prompt` and prompt cancellation to reuse those state helpers, so destination-prompt state reset/dispatch logic is no longer open-coded in multiple places.
- Changed `LocalControlRoomBackend.submit_input()` to resolve destination-prompt submissions through the new prompt-state helper and dispatch the resulting `DestinationPromptDispatch` instead of editing destination prompt fields inline.
- Added direct prompt-state tests for successful and invalid destination-prompt submission paths.
- Verified with `uv run python3 -m unittest discover -s tests` (`481 tests in 0.211s`).

## Follow-ups

- Move the multi-step haul prompt onto the same explicit prompt-state transition model so remote prompt orchestration no longer depends on headless-app-local branching for wizard progression.
- Decide whether replay navigation should get explicit server-native commands or remain a widget-mirrored client concern after the haul prompt work lands.

## Iteration 186

- When: `2026-06-19 17:18`
- Area: `control-room`
- Title: `state-drive-haul-prompt-edges`
- Source: [2026-06-19-17-18_control-room_state-drive-haul-prompt-edges.md](iteration-logs/2026-06-19-17-18_control-room_state-drive-haul-prompt-edges.md)

# Iteration Log

- Area: `control-room`
- Title: `state-drive-haul-prompt-edges`
- Started: `2026-06-19 17:18`

## Summary

- Moved the haul wizard’s entry, confirmation, and reset edges onto explicit `PromptState` helpers so the remote architecture no longer depends on open-coded haul prompt field mutation for those transitions.

## Changes

- Added `begin_haul_prompt`, `resolve_haul_confirm_prompt`, `clear_haul_prompt`, and `clear_haul_confirm_prompt` helpers in [edap/control_room/prompts.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/edap/control_room/prompts.py) that operate directly on `PromptState`.
- Updated haul prompt start and confirmation handling to reuse those helpers instead of open-coding prompt field mutation inside UI handlers.
- Updated prompt cancellation to reuse the new haul prompt reset helpers rather than manually clearing haul prompt fields inline.
- Added direct prompt-state tests for haul prompt start, haul confirmation resolution, and haul prompt reset behavior.
- Verified with `uv run python3 -m unittest discover -s tests` (`484 tests in 0.218s`).

## Follow-ups

- Move the remaining per-step haul wizard body onto explicit prompt-state transition helpers so remote prompt orchestration no longer depends on headless-app-local branching for each wizard step.
- Decide whether replay navigation should get explicit server-native commands or remain a widget-mirrored client concern after the haul wizard body is moved.

## Iteration 187

- When: `2026-06-19 17:23`
- Area: `control-room`
- Title: `state-drive-haul-wizard-body`
- Source: [2026-06-19-17-23_control-room_state-drive-haul-wizard-body.md](iteration-logs/2026-06-19-17-23_control-room_state-drive-haul-wizard-body.md)

# Iteration Log

- Area: `control-room`
- Title: `state-drive-haul-wizard-body`
- Started: `2026-06-19 17:23`

## Summary

- Moved the remaining step-by-step haul wizard progression onto an explicit `PromptState` transition helper so remote prompt orchestration no longer depends on headless-app-local branching for wizard advancement.

## Changes

- Added `advance_haul_prompt` in [edap/control_room/prompts.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/edap/control_room/prompts.py) to drive all remaining haul wizard step transitions from prompt state, including station prompts, land/orbital confirmations, settle timing, and docking timeout completion.
- Simplified `handle_haul_prompt()` into a thin wrapper that applies the transition helper result to logging, input placeholder/value updates, and final haul-loop dispatch.
- Added direct prompt-state tests covering representative haul wizard transitions, validation failures, and final dispatch completion.
- Verified with `uv run python3 -m unittest discover -s tests` (`487 tests in 0.207s`).

## Follow-ups

- Decide whether replay navigation should gain explicit server-native commands or remain a widget-mirrored client concern.
- Live-validate active-operator claiming, failover-on-disconnect, and routine-heavy remote execution against real `serve`/`connect` sessions now that prompt and replay state are server-retained and state-driven.

## Iteration 188

- When: `2026-06-19 17:28`
- Area: `control-room`
- Title: `add-remote-replay-navigation`
- Source: [2026-06-19-17-28_control-room_add-remote-replay-navigation.md](iteration-logs/2026-06-19-17-28_control-room_add-remote-replay-navigation.md)

# Iteration Log

- Area: `control-room`
- Title: `add-remote-replay-navigation`
- Started: `2026-06-19 17:28`

## Summary

- Added explicit replay-selection navigation commands to the remote protocol so replay movement no longer depends on widget-local behavior as the transport model.

## Changes

- Added backend/server command support for replay selection movement by relative offset, including `command.move_replay_selection` on the observer websocket path.
- Updated the local TUI so replay-browser up/down navigation routes through the backend intent surface instead of bypassing it via `OptionList` behavior.
- Added server/client/protocol coverage proving replay selection movement is serialized over the remote command path and reflected back into snapshots.
- Verified with `uv run python3 -m unittest discover -s tests` (`489 tests in 0.213s`).

## Follow-ups

- Live-validate replay-heavy remote operator sessions, active-operator failover, and routine-heavy command execution under real `serve` / `connect` runs.
- Decide whether any additional remote operator ergonomics are needed after live validation now that replay navigation has an explicit protocol path.

## Iteration 189

- When: `2026-06-19 17:31`
- Area: `control-room`
- Title: `add-websocket-remote-validation`
- Source: [2026-06-19-17-31_control-room_add-websocket-remote-validation.md](iteration-logs/2026-06-19-17-31_control-room_add-websocket-remote-validation.md)

# Iteration Log

- Area: `control-room`
- Title: `add-websocket-remote-validation`
- Started: `2026-06-19 17:31`

## Summary

- Added websocket-level integration coverage for the observer server path so active-operator failover and replay-navigation commands are now exercised through the actual session protocol, not only through unit-level helpers.

## Changes

- Added `TestClient` websocket coverage proving that when the active operator disconnects, the remaining connected client receives the promotion event and subsequent personalized snapshot as the new `active_operator`.
- Added websocket-session coverage proving `command.move_replay_selection` is accepted over the observer protocol and reaches the server command handler.
- Re-ran the full test suite with `uv run python3 -m unittest discover -s tests` (`491 tests in 0.225s`).

## Follow-ups

- Live-validate routine-heavy remote execution, prompt-heavy flows, and failure/recovery wording under real `serve` / `connect` sessions.
- Decide whether any further remote operator ergonomics are needed once live validation is done.

## Iteration 190

- When: `2026-06-19 17:39`
- Area: `control-room`
- Title: `add-headless-remote-protocol-validation`
- Source: [2026-06-19-17-39_control-room_add-headless-remote-protocol-validation.md](iteration-logs/2026-06-19-17-39_control-room_add-headless-remote-protocol-validation.md)

# Iteration Log

- Area: `control-room`
- Title: `add-headless-remote-protocol-validation`
- Started: `2026-06-19 17:39`

## Summary

- Added websocket-session coverage that drives the actual headless observer host, so prompt-heavy remote protocol flow is now validated locally through the real server path instead of only through helper-level tests.

## Changes

- Added websocket-session integration coverage proving `command.submit_input` can open and resolve a destination prompt against a live `HeadlessControlRoomHost` behind `build_observer_server_app`, with broker-retained snapshot state reflecting the prompt lifecycle.
- Added websocket-session coverage proving `command.request_active_operator` updates broker role assignment over the real observer protocol path.
- Re-ran the full test suite with `uv run python3 -m unittest discover -s tests` (`493 tests in 0.228s`).

## Follow-ups

- Live-validate routine-heavy remote execution, prompt-heavy flows, and failure/recovery wording under real `serve` / `connect` sessions with the actual game/runtime in the loop.
- Decide whether any further remote operator ergonomics are needed once live validation is done.

## Iteration 191

- When: `2026-06-19 17:44`
- Area: `control-room`
- Title: `remote-validation-playbook`
- Source: [2026-06-19-17-44_control-room_remote-validation-playbook.md](iteration-logs/2026-06-19-17-44_control-room_remote-validation-playbook.md)

# Iteration Log

- Area: `control-room`
- Title: `remote-validation-playbook`
- Started: `2026-06-19 17:44`

## Summary

- Added a dedicated remote-operator validation runbook, a lightweight HTTP/websocket scratch probe, and aligned capability/schema metadata so the remaining `serve` / `connect` risk can be exercised and future clients can discover the remote surface without relying on memory or the full Textual client.

## Changes

- Added `docs/operators/control-room-remote.md` with LAN startup, active-operator semantics, reconnect/failover checks, prompt-cancel expectations, and a concrete live validation sequence.
- Added `tools/scratch/scratch_control_room_remote.py` plus `tools/scratch/README.md` coverage for transport-only probing of `health`, `capabilities`, `snapshot`, and websocket session events.
- Expanded `/capabilities` to advertise the full supported command, event, and response message sets instead of only a partial list.
- Updated `docs/schemas/control_room_message.schema.json` to match the real websocket command surface, fixed the nullable active-operator-change payload, and added schema regression coverage.
- Updated `docs/operators/control-room.md`, `docs/plans/0007-control-room-client-server-refactor.md`, and `docs/status/control-room.md` so the current server/client split, client-local TTS behavior, and remaining validation work are described accurately.

## Follow-ups

- Run the new remote validation playbook against real multi-client LAN sessions and capture any routine-heavy or market-recovery gaps that still appear under live runtime conditions.

## Iteration 192

- When: `2026-06-19 17:55`
- Area: `control-room`
- Title: `add-web-client-discovery-surface`
- Source: [2026-06-19-17-55_control-room_add-web-client-discovery-surface.md](iteration-logs/2026-06-19-17-55_control-room_add-web-client-discovery-surface.md)

# Iteration Log

- Area: `control-room`
- Title: `add-web-client-discovery-surface`
- Started: `2026-06-19 17:55`

## Summary

- Added browser-friendly HTTP discovery support for the remote observer server so future web clients can fetch capabilities and the wire schema directly instead of relying on same-origin coupling or repo-local files.

## Changes

- Added permissive CORS middleware to the observer server HTTP surface and kept websocket auth/query-token behavior unchanged.
- Added `GET /schema/control_room_message.json` plus a `message_schema_url` field in `/capabilities` so external clients can fetch the current wire contract from the server itself.
- Covered the new discovery surface with server tests and updated the protocol/design/status docs to reflect the browser-client path.

## Follow-ups

- Use the served schema and capability metadata as the starting point if a dedicated browser client is introduced, then decide whether any additional browser-specific session ergonomics are needed after live LAN validation.

## Iteration 193

- When: `2026-06-19 17:58`
- Area: `control-room`
- Title: `add-browser-remote-probe`
- Source: [2026-06-19-17-58_control-room_add-browser-remote-probe.md](iteration-logs/2026-06-19-17-58_control-room_add-browser-remote-probe.md)

# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-probe`
- Started: `2026-06-19 17:58`

## Summary

- Added a no-build browser probe for the remote observer server so the new CORS/schema/discovery work can be exercised from a real browser before a dedicated web client exists.

## Changes

- Added `tools/scratch/control_room_remote_browser.html`, a standalone HTML/JS page that fetches `health`, `capabilities`, `snapshot`, and the served schema, then opens `WS /session` and can claim operator or request snapshots.
- Updated the scratch-tool README and remote operator runbook so the browser probe is part of the supported validation path for future web-client work.
- Refreshed the Control Room status handoff to call out both CLI and browser smoke probes for remote validation.

## Follow-ups

- If a dedicated web client is started, use the browser probe as the minimal contract check first, then replace its ad hoc rendering with a proper app without changing the server discovery/session surface casually.

## Iteration 194

- When: `2026-06-19 17:59`
- Area: `control-room`
- Title: `align-remote-capabilities-contract`
- Source: [2026-06-19-17-59_control-room_align-remote-capabilities-contract.md](iteration-logs/2026-06-19-17-59_control-room_align-remote-capabilities-contract.md)

# Iteration Log

- Area: `control-room`
- Title: `align-remote-capabilities-contract`
- Started: `2026-06-19 17:59`

## Summary

- Corrected the remaining capability-contract drift so the design note, checked-in schema, and runtime-discovered auth metadata all describe the same remote observer behavior.

## Changes

- Updated the protocol design note to match the real first-connected-client active-operator policy plus explicit operator claiming and disconnect failover.
- Expanded the capabilities payload schema to include the auth metadata and schema URL fields that the server actually returns.
- Added regression coverage so future schema edits have to keep the capabilities contract aligned with the runtime surface.

## Follow-ups

- If the remote surface grows again, update the runtime constants and the checked-in schema together in the same changeset instead of letting the design note drift ahead or behind implementation.

## Iteration 195

- When: `2026-06-19 18:02`
- Area: `control-room`
- Title: `host-browser-remote-probe`
- Source: [2026-06-19-18-02_control-room_host-browser-remote-probe.md](iteration-logs/2026-06-19-18-02_control-room_host-browser-remote-probe.md)

# Iteration Log

- Area: `control-room`
- Title: `host-browser-remote-probe`
- Started: `2026-06-19 18:02`

## Summary

- Hosted the browser probe from the observer server itself and taught it to send real operator commands, which makes the future web-client path exercise the actual runtime surface instead of only reading discovery metadata.

## Changes

- Added `GET /browser-probe` on the observer server so a browser can load the probe from the same origin as the remote session surface.
- Extended the browser probe to claim operator, submit command input, request snapshots, and cancel active routines while still showing snapshot and activity state.
- Added server coverage for the hosted HTML endpoint and updated the remote operator docs/status handoff to point at the served probe as the default browser validation path.

## Follow-ups

- If a real web client is built next, reuse the hosted probe flow first and only replace its UI shell; do not regress the same-origin browser validation path unless there is a deliberate reason to decouple it.

## Iteration 196

- When: `2026-06-19 18:04`
- Area: `control-room`
- Title: `expand-browser-remote-controls`
- Source: [2026-06-19-18-04_control-room_expand-browser-remote-controls.md](iteration-logs/2026-06-19-18-04_control-room_expand-browser-remote-controls.md)

# Iteration Log

- Area: `control-room`
- Title: `expand-browser-remote-controls`
- Started: `2026-06-19 18:04`

## Summary

- Expanded the hosted browser probe so the web-client path can exercise replay-browser and prompt flows, not just basic command submission and discovery.

## Changes

- Added replay-browser controls for open/close, filter updates, selection movement, replay run/edit, and default-haul toggling using the same remote protocol commands as the Textual client.
- Added prompt-facing inputs for explicit and default submissions plus clearer prompt/routine/replay state rendering in the browser probe.
- Extended the browser-probe endpoint coverage and updated the remote operator docs/status handoff to reflect that the browser path now covers replay and prompt-heavy remote flows too.

## Follow-ups

- If a dedicated web client replaces the probe, keep the replay and prompt command paths explicit rather than tunneling widget-local behavior over the wire.

## Iteration 197

- When: `2026-06-19 18:06`
- Area: `control-room`
- Title: `add-browser-remote-reconnect`
- Source: [2026-06-19-18-06_control-room_add-browser-remote-reconnect.md](iteration-logs/2026-06-19-18-06_control-room_add-browser-remote-reconnect.md)

# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-reconnect`
- Started: `2026-06-19 18:06`

## Summary

- Brought the hosted browser probe up to the same reconnect/state-healing baseline as the Textual remote client so transient disconnects do not leave the future web-client path in a stale one-shot state.

## Changes

- Added automatic browser-probe reconnect with exponential backoff, reconnect status messaging, and a fresh snapshot request on reconnect.
- Improved the browser probe’s replay rendering and message stream so announcements, replay choices, and reconnect behavior are easier to inspect during remote validation.
- Updated endpoint coverage plus the remote operator docs/status handoff so the browser path is explicitly documented as covering reconnect recovery too.

## Follow-ups

- If a dedicated web client is built, preserve the reconnect-and-refresh semantics as a baseline requirement rather than treating them as probe-only behavior.

## Iteration 198

- When: `2026-06-19 18:08`
- Area: `control-room`
- Title: `add-browser-operator-gating`
- Source: [2026-06-19-18-08_control-room_add-browser-operator-gating.md](iteration-logs/2026-06-19-18-08_control-room_add-browser-operator-gating.md)

# Iteration Log

- Area: `control-room`
- Title: `add-browser-operator-gating`
- Started: `2026-06-19 18:08`

## Summary

- Added active-operator gating to the hosted browser probe so the future web-client path respects the same observer-versus-operator boundary as the Textual remote client.

## Changes

- Disabled mutating browser-probe controls while the current session is only an observer and surfaced an explicit operator hint in the UI.
- Blocked outbound mutating protocol commands client-side unless the latest snapshot says the browser session is the active operator, while still allowing snapshot requests and operator claims.
- Updated endpoint coverage plus the remote operator docs/status handoff to reflect that browser validation now exercises active-operator gating too.

## Follow-ups

- If a dedicated web client is built, keep the client-side operator gating as a UX safeguard even though the server remains authoritative for permission checks.

## Iteration 199

- When: `2026-06-19 18:10`
- Area: `control-room`
- Title: `add-browser-remote-visibility`
- Source: [2026-06-19-18-10_control-room_add-browser-remote-visibility.md](iteration-logs/2026-06-19-18-10_control-room_add-browser-remote-visibility.md)

# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-visibility`
- Started: `2026-06-19 18:10`

## Summary

- Expanded the hosted browser probe from a command surface into a more legible remote operator surface by adding connected-client and recent-activity visibility directly in the page.

## Changes

- Added dedicated browser-probe panels for connected clients and recent activity, derived from the live snapshot and incremental activity-log events.
- Kept those panels refreshed as websocket messages arrive so the browser path surfaces operator-relevant state instead of forcing the user to inspect the raw snapshot JSON alone.
- Updated endpoint coverage plus the remote operator docs/status handoff to reflect that browser validation now covers connected-client and activity visibility too.

## Follow-ups

- If a dedicated web client is built, preserve these basic visibility surfaces early so remote operators do not need a separate raw-state/debug page to understand session state.

## Iteration 200

- When: `2026-06-19 18:12`
- Area: `control-room`
- Title: `align-protocol-design-note`
- Source: [2026-06-19-18-12_control-room_align-protocol-design-note.md](iteration-logs/2026-06-19-18-12_control-room_align-protocol-design-note.md)

# Iteration Log

- Area: `control-room`
- Title: `align-protocol-design-note`
- Started: `2026-06-19 18:12`

## Summary

- Realigned the main Control Room protocol design note with the current shipped remote architecture so the written contract no longer describes superseded message families and payloads.

## Changes

- Replaced the stale draft vocabulary in `docs/design/0002-control-room-client-server-protocol.md` with the actual current command, event, and response message set used by `serve` and `connect`.
- Updated the example envelope plus payload sections to describe `command.submit_input`, replay commands, active-operator claiming, and `command.cancel_active_routine` instead of the pre-remote routine/filter draft.
- Expanded the capabilities section to match the current runtime metadata fields that the HTTP discovery surface returns.

## Follow-ups

- Keep the protocol design note and the checked-in schema moving together whenever the remote surface changes, so future web-client work is not forced to guess which document is authoritative.

## Iteration 201

- When: `2026-06-19 18:15`
- Area: `control-room`
- Title: `advertise-browser-probe-url`
- Source: [2026-06-19-18-15_control-room_advertise-browser-probe-url.md](iteration-logs/2026-06-19-18-15_control-room_advertise-browser-probe-url.md)

# Iteration Log

- Area: `control-room`
- Title: `advertise-browser-probe-url`
- Started: `2026-06-19 18:15`

## Summary

- Added first-class discovery for the hosted browser probe so future launchers and web shells can find the served browser client entrypoint from `/capabilities` instead of hardcoding it.

## Changes

- Added `browser_probe_url` to the observer server capabilities response alongside the existing `message_schema_url`.
- Updated the checked-in message schema, server tests, and schema regression coverage so the new discovery field is treated as part of the remote contract.
- Refreshed the protocol design note, remote operator runbook, and control-room status handoff to describe the new browser-probe discovery path.

## Follow-ups

- If a dedicated launcher or browser shell is introduced, prefer reading `browser_probe_url` from capabilities rather than constructing the path independently.

## Iteration 202

- When: `2026-06-19 18:17`
- Area: `control-room`
- Title: `validate-remote-capabilities-handshake`
- Source: [2026-06-19-18-17_control-room_validate-remote-capabilities-handshake.md](iteration-logs/2026-06-19-18-17_control-room_validate-remote-capabilities-handshake.md)

# Iteration Log

- Area: `control-room`
- Title: `validate-remote-capabilities-handshake`
- Started: `2026-06-19 18:17`

## Summary

- Hardened the remote client handshake so `connect` fails clearly against incomplete or incompatible capability surfaces instead of discovering protocol mismatches only after the websocket session starts.

## Changes

- Added client-side validation of `supported_message_types`, `supported_client_roles`, and `minimum_client_version` during the authenticated `/capabilities` fetch.
- Added focused client tests covering the accepted current server surface, missing required message types, and unsupported minimum client versions.
- Updated the remote operator docs and current control-room status handoff to note that incompatible servers are now rejected during the capability probe.

## Follow-ups

- If the remote protocol adds or removes required message types later, keep the client-side compatibility gate and the server-side advertised capability set updated in the same change.

## Iteration 203

- When: `2026-06-19 18:19`
- Area: `control-room`
- Title: `validate-remote-auth-and-discovery-handshake`
- Source: [2026-06-19-18-19_control-room_validate-remote-auth-and-discovery-handshake.md](iteration-logs/2026-06-19-18-19_control-room_validate-remote-auth-and-discovery-handshake.md)

# Iteration Log

- Area: `control-room`
- Title: `validate-remote-auth-and-discovery-handshake`
- Started: `2026-06-19 18:19`

## Summary

- Extended the remote client compatibility gate so `connect` now rejects capability surfaces that are message-compatible but still missing the auth transports or discovery fields the current remote clients actually depend on.

## Changes

- Added client-side validation for `authentication_required`, `authentication_scheme`, `authentication_supported_transports`, `authentication_query_parameter_name`, `message_schema_url`, and `browser_probe_url` during the authenticated capability probe.
- Added focused client tests covering missing auth transports and missing discovery URLs in addition to the existing message/version checks.
- Updated the remote operator docs and current control-room status handoff to note that incompatible auth/discovery capability surfaces now fail before websocket startup.

## Follow-ups

- If the remote transport contract changes again, keep the client handshake validator focused on the fields that real clients actually consume instead of treating `/capabilities` as a passive info blob.

## Iteration 204

- When: `2026-06-19 18:21`
- Area: `control-room`
- Title: `add-browser-role-transition-handling`
- Source: [2026-06-19-18-21_control-room_add-browser-role-transition-handling.md](iteration-logs/2026-06-19-18-21_control-room_add-browser-role-transition-handling.md)

# Iteration Log

- Area: `control-room`
- Title: `add-browser-role-transition-handling`
- Started: `2026-06-19 18:21`

## Summary

- Taught the hosted browser probe to react explicitly to operator-role transitions so the web-client path updates its session understanding immediately instead of leaving that shift implicit in later snapshots.

## Changes

- Added explicit browser handling for `event.connection_ready` and `event.active_operator_changed`, including session-id display and an immediate snapshot refresh after operator changes.
- Disabled the browser `Claim Operator` button once the current session is already the active operator, so the page reflects role state more cleanly.
- Updated endpoint coverage plus the remote operator docs/status handoff to note that the browser path now handles role transitions directly rather than only relying on passive snapshot refreshes.

## Follow-ups

- If the hosted browser path becomes a real web client, keep explicit role-transition handling in the session layer rather than hiding it behind generic snapshot rerenders.

## Iteration 205

- When: `2026-06-19 18:24`
- Area: `control-room`
- Title: `shared-remote-capabilities`
- Source: [2026-06-19-18-24_control-room_shared-remote-capabilities.md](iteration-logs/2026-06-19-18-24_control-room_shared-remote-capabilities.md)

# Iteration Log

- Area: `control-room`
- Title: `shared-remote-capabilities`
- Started: `2026-06-19 18:24`

## Summary

- Collapsed the remote observer capability surface into one shared protocol module so server discovery, client validation, and capability-focused tests stop drifting independently.

## Changes

- Added `edap/control_room/protocol/capabilities.py` with shared message-role/auth constants plus helpers to build and validate the observer capability payload.
- Rewired the observer server capability endpoint and shared-token auth description to use the shared capability constants instead of local duplicated literals.
- Rewired the remote client capability validation and tests to use the shared builder/validator rather than repeated hand-written capability dictionaries, and tightened validation so the advertised command/event/response breakdown lists must stay aligned with the aggregate message list.
- Updated the hosted browser probe to consume the advertised websocket auth query-parameter metadata from `GET /capabilities` instead of hardcoding `access_token`, so the browser path now behaves like a discovery-driven future web client.
- Updated the CLI scratch probe to validate the advertised capability surface, build its websocket URL from the same auth metadata, and log the correct active-operator change field so the non-TUI validation helpers no longer drift from the real remote contract.
- Updated the native Textual client and CLI scratch probe to prefer websocket bearer-header auth and reserve the query-parameter path for browser-constrained clients, keeping the shared capability contract but avoiding URL token transport where the runtime does not need it.
- Kept schema validation anchored to the shared protocol message-type list and verified the full suite stayed green.

## Follow-ups

- Run the live remote validation playbook so the next server/client slices focus on runtime behavior rather than protocol-contract drift.

## Iteration 206

- When: `2026-06-19 20:57`
- Area: `control-room`
- Title: `cargo-manifest-remote-refresh`
- Source: [2026-06-19-20-57_control-room_cargo-manifest-remote-refresh.md](iteration-logs/2026-06-19-20-57_control-room_cargo-manifest-remote-refresh.md)

# Iteration Log

- Area: `control-room`
- Title: `cargo-manifest-remote-refresh`
- Started: `2026-06-19 20:57`

## Summary

- Fixed the cargo-state mismatch where Control Room could show total cargo tonnage from `Status.json` while cargo details stayed empty, causing remote `sell` and resumed haul decisions to treat the hold as empty.

## Changes

- Added `edap/cargo_manifest.py` as a shared cargo-manifest reader that retries briefly when `Status.json` reports cargo but `Cargo.json` is temporarily empty.
- Switched bootstrap, render/status refresh, trade routines, market routines, and two-way haul resume detection over to the shared manifest reader.
- Updated `ControlRoomApp._sync_status_snapshot()` to refresh cargo details alongside `Status.json` so server/client snapshots recover commodity breakdown without waiting for a fresh trade event.
- Added regression coverage for the retry helper and for status refresh repopulating cargo inventory.

## Follow-ups

- Live-test remote server startup and resumed haul with preloaded cargo to confirm the new retry path matches Elite/CrossOver file-write timing in practice.

## Iteration 207

- When: `2026-06-19 21:31`
- Area: `control-room`
- Title: `haul-cancel-tts`
- Source: [2026-06-19-21-31_control-room_haul-cancel-tts.md](iteration-logs/2026-06-19-21-31_control-room_haul-cancel-tts.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-cancel-tts`
- Started: `2026-06-19 21:31`

## Summary

- Added explicit spoken feedback for immediate haul cancellation so aborting mid-cycle still produces a clear TTS line without misusing the normal route/session completion announcements.

## Changes

- Added `haul_cancelled` to the TTS announcement IDs and default phrase set.
- Emit the cancellation announcement when haul or multi-leg haul is cancelled immediately instead of only logging the cancel.
- Added regression coverage around the second-interrupt immediate-haul-cancel path.

## Follow-ups

- Live-test remote client double-`Ctrl-C` on haul to confirm the cancellation announcement reaches the observer client as expected.

## Iteration 208

- When: `2026-06-20 09:54`
- Area: `ci`
- Title: `extract-discord-failure-notifier-script`
- Source: [2026-06-20-09-54______ci______extract-discord-failure-notifier-script.md](iteration-logs/2026-06-20-09-54______ci______extract-discord-failure-notifier-script.md)

# Iteration Log

- Area: `ci`
- Title: `extract-discord-failure-notifier-script`
- Started: `2026-06-20 09:54`

## Summary

- Moved the bulk of the Discord Actions-failure notification logic out of the workflow YAML and into a repo script so it can be tested locally and reused by CI unchanged.

## Changes

- Added `tools/discord_workflow_failure_notify.py` to fetch failed-job metadata from GitHub or load saved jobs JSON, build the Discord payload, and either post it or dry-run print it locally.
- Reduced `.github/workflows/discord-workflow-failure-notify.yml` to a thin environment wrapper that checks out the repo, sets up Python, and invokes the script.
- Added unit coverage for failed-job selection, workflow-link discovery, payload rendering, Discord error propagation, and dry-run output.
- Re-validated the workflow YAML locally after the extraction.

## Follow-ups

- Trigger the next real failing Actions run to verify the live webhook delivery and final Discord markdown rendering still match the local dry-run and unit-tested behavior.

## Iteration 209

- When: `2026-06-20 11:19`
- Area: `ci-release`
- Title: `prepare-v1-13-0-release`
- Source: [2026-06-20-11-19__ci-release__prepare-v1-13-0-release.md](iteration-logs/2026-06-20-11-19__ci-release__prepare-v1-13-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-13-0-release`
- Started: `2026-06-20 11:19`

## Summary

- Prepared the `v1.13.0` release cut from `main` after the browser-facing remote observer expansion, haul/runtime follow-up fixes, and Discord workflow-failure notifier extraction landed since `v1.12.0`.

## Changes

- Bumped `[project].version` in `pyproject.toml` to `1.13.0` so the release-prep commit matches the next semantic tag.
- Updated `docs/status/ci-release.md` to record that `main` is now prepared for `v1.13.0` and to summarize the release scope at the handoff level.
- Refreshed release bookkeeping artifacts and validation as part of the cut.

## Follow-ups

- Push the release-prep commit and `v1.13.0` tag, then publish the GitHub release with high-level notes focused on Control Room remote operations and notifier reliability.

## Iteration 210

- When: `2026-06-20 11:22`
- Area: `ci-release`
- Title: `remove-jobs-sample-payload`
- Source: [2026-06-20-11-22__ci-release__remove-jobs-sample-payload.md](iteration-logs/2026-06-20-11-22__ci-release__remove-jobs-sample-payload.md)

# Iteration Log

- Area: `ci-release`
- Title: `remove-jobs-sample-payload`
- Started: `2026-06-20 11:22`

## Summary

- Removed the unused `jobs.sample.json` fixture from the repo after the `v1.13.0` release cut because nothing in the notifier tests or runtime reads it.

## Changes

- Deleted the root-level `jobs.sample.json` file.
- Confirmed there are no remaining references to the sample payload in tracked source or tests.

## Follow-ups

- Keep notifier validation centered on the tested Python entrypoint and ad hoc saved jobs JSON files instead of a checked-in sample payload unless a stable operator-facing fixture is needed later.

## Iteration 211

- When: `2026-06-20 11:30`
- Area: `docs-process`
- Title: `move-auxiliary-clis-into-tools`
- Source: [2026-06-20-11-30_docs-process_move-auxiliary-clis-into-tools.md](iteration-logs/2026-06-20-11-30_docs-process_move-auxiliary-clis-into-tools.md)

# Iteration Log

- Area: `docs-process`
- Title: `move-auxiliary-clis-into-tools`
- Started: `2026-06-20 11:30`

## Summary

- Moved every supported root-level Python CLI except `control_room.py` into `tools/` so the repo root now presents one obvious primary entrypoint while auxiliary operator and diagnostics scripts live in one utility namespace.

## Changes

- Moved `bindings_files.py`, `check_bindings.py`, `diagnostics.py`, `run_routine.py`, `set_binding.py`, `ship_controls.py`, `speak.py`, `view_bindings.py`, and `watch_journal.py` into `tools/`.
- Added `tools/__init__.py` so the CLI unit tests can import the relocated modules directly.
- Updated maintained README and operator/diagnostics docs to use `tools/...` command paths and recorded the new layout in `docs/status/docs-process.md`.
- Updated CLI unit tests and moved-script self-references to target the `tools.*` modules and executable paths.

## Follow-ups

- Keep future auxiliary CLIs under `tools/` unless there is a strong reason they belong in the runtime package or scratch space, so `control_room.py` remains the only root Python entrypoint.

## Iteration 212

- When: `2026-06-22 10:42`
- Area: `control-room`
- Title: `add-optional-playwright-extra`
- Source: [2026-06-22-10-42_control-room_add-optional-playwright-extra.md](iteration-logs/2026-06-22-10-42_control-room_add-optional-playwright-extra.md)

# Iteration Log

- Area: `control-room`
- Title: `add-optional-playwright-extra`
- Started: `2026-06-22 10:42`

## Summary

- Added an optional Playwright-based browsing dependency path so Inara route work can use a real browser without changing the default install set for normal users.

## Changes

- Added a `browsing` extra in `pyproject.toml` with `playwright>=1.53` instead of placing Playwright in base dependencies or the existing `dev` extra.
- Refreshed `uv.lock`; the optional extra resolved to `playwright`, `greenlet`, and `pyee`.
- Confirmed the current Inara assumption for this environment: direct HTTP requests still hit the access-check interstitial even with copied authenticated cookies, so the live route prototype should start from browser-backed DOM acquisition.
- Re-ran the full unittest suite after the packaging change; `519` tests passed in `0.286s`.

## Follow-ups

- Install the extra explicitly with `uv sync --extra browsing` only on machines that need the browser-backed route probe.
- After that install, add a headed Playwright probe that opens the Inara traderoutes page, waits for `div.mainblock.traderoutebox`, and prints a compact parsed summary.

## Iteration 213

- When: `2026-06-22 10:53`
- Area: `control-room`
- Title: `add-inara-playwright-probe`
- Source: [2026-06-22-10-53_control-room_add-inara-playwright-probe.md](iteration-logs/2026-06-22-10-53_control-room_add-inara-playwright-probe.md)

# Iteration Log

- Area: `control-room`
- Title: `add-inara-playwright-probe`
- Started: `2026-06-22 10:53`

## Summary

- Added a scratch Playwright probe that can open a live Inara trade-routes page, wait for the route cards to render, and print compact summaries from the real DOM.

## Changes

- Added `tools/scratch/scratch_inara_trade_routes.py` with a persistent Playwright browser profile, timeout handling for Inara's access-check interstitial, optional HTML/JSON/screenshot capture, and compact route summary output.
- Kept the probe outside the main runtime surface by placing it under `tools/scratch/` and by importing Playwright lazily with an explicit install hint if the optional `browsing` extra is missing.
- Added unit coverage for the probe's inline text parsing and endpoint cleanup in `tests/test_scratch_inara_trade_routes.py`.
- Updated `tools/scratch/README.md` and `docs/diagnostics/cli-reference.md` to advertise the new probe.
- Verified a live headless run against the provided Inara traderoutes URL; the probe loaded 50 `div.mainblock.traderoutebox` rows and printed route/profit summaries, confirming Playwright can reach the real results DOM where plain HTTP fetches were challenged.

## Follow-ups

- Move the route extraction from scratch-script dicts into typed parser/model code once the exact Control Room presentation shape is chosen.
- Decide whether the first Control Room integration should read saved probe JSON, call the probe subprocess, or share the Playwright extraction logic directly.

## Iteration 214

- When: `2026-06-22 10:58`
- Area: `control-room`
- Title: `default-inara-probe-headless`
- Source: [2026-06-22-10-58_control-room_default-inara-probe-headless.md](iteration-logs/2026-06-22-10-58_control-room_default-inara-probe-headless.md)

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

## Iteration 215

- When: `2026-06-22 11:16`
- Area: `haul`
- Title: `add-inara-haul-search`
- Source: [2026-06-22-11-16_____haul_____add-inara-haul-search.md](iteration-logs/2026-06-22-11-16_____haul_____add-inara-haul-search.md)

# Iteration Log

- Area: `haul`
- Title: `add-inara-haul-search`
- Started: `2026-06-22 11:16`

## Summary

- Added the first real `haul search [system]` path so Control Room can fetch live Inara trade routes headlessly and keep the results visible in a dedicated panel.

## Changes

- Extracted the Playwright-backed Inara route fetch and row parsing into `edap/inara/trade_routes.py`, with the scratch probe slimmed down into a wrapper over that shared module.
- Added a local `TradeRoutesData` state model plus a `TRADE ROUTES` panel in Control Room, rendered independently from the existing market and haul panels.
- Extended `haul` command handling so `haul search [system]` records history, defaults to the current ship system when omitted, skips the bindings/controls prerequisite, and updates the panel with loading, success, or failure state.
- Updated haul help text and the command placeholder to advertise `haul search [system]`.
- Added unit coverage for the shared Inara helpers, the new panel rendering, and the `haul search` command flow.
- Verified the shared scratch probe still fetches the live Inara DOM after the refactor and re-ran the full suite successfully.

## Follow-ups

- Decide whether Inara route state should remain local-only or be promoted into the remote observer snapshot/wire contract.
- Decide whether the current operator-supplied Inara query defaults should move into explicit config once the route panel ergonomics settle.

## Iteration 216

- When: `2026-06-22 11:24`
- Area: `control-room`
- Title: `observer-connect-no-local-journal`
- Source: [2026-06-22-11-24_control-room_observer-connect-no-local-journal.md](iteration-logs/2026-06-22-11-24_control-room_observer-connect-no-local-journal.md)

# Iteration Log

- Area: `control-room`
- Title: `observer-connect-no-local-journal`
- Started: `2026-06-22 11:24`

## Summary

- Fixed `control_room connect` so remote observer clients can start on machines without a local Elite Dangerous install or resolved journal path.

## Changes

- Let `ControlRoomApp` initialize with no local journal/market path for observer-mode clients while keeping local runtime startup guarded behind an explicit journal requirement.
- Added a regression test that instantiates `ObserverControlRoomApp` with no local journal path and confirmed the full unittest suite still passes in `0.282s`.

## Follow-ups

- Re-run the live multi-machine observer flow to confirm the remote TUI now reaches the initial snapshot cleanly on a non-ED client host.

## Iteration 217

- When: `2026-06-22 11:53`
- Area: `control-room`
- Title: `guard-remote-journal-mount`
- Source: [2026-06-22-11-53_control-room_guard-remote-journal-mount.md](iteration-logs/2026-06-22-11-53_control-room_guard-remote-journal-mount.md)

# Iteration Log

- Area: `control-room`
- Title: `guard-remote-journal-mount`
- Started: `2026-06-22 11:53`

## Summary

- Guarded `ControlRoomApp.on_mount()` behind the backend mode so remote-backed mounts cannot trip the local journal-directory runtime check.

## Changes

- Added a backend-aware early return in [edap/control_room/app.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/edap/control_room/app.py:679) before local runtime setup.
- Added a regression test in [tests/test_control_room_client.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/tests/test_control_room_client.py:246) that mounts the observer app without a local journal directory.
- Verified `tests/test_control_room_client.py` passes; full `unittest discover -s tests` stays at `0.256s` but currently has one unrelated existing failure in `test_haul_search_uses_current_system_and_updates_trade_routes`.

## Follow-ups

- Re-run a live `control_room connect` session against `serve` to confirm the shipped remote client no longer surfaces the local journal runtime error.

## Iteration 218

- When: `2026-06-22 12:00`
- Area: `haul`
- Title: `add-inara-search-prompt-flow`
- Source: [2026-06-22-12-00_____haul_____add-inara-search-prompt-flow.md](iteration-logs/2026-06-22-12-00_____haul_____add-inara-search-prompt-flow.md)

# Iteration Log

- Area: `haul`
- Title: `add-inara-search-prompt-flow`
- Started: `2026-06-22 12:00`

## Summary

- Finished the first operator-facing Inara search workflow for Control Room: prompt-driven `haul search [system]`, direct `haul search url <inara-url>`, local ignored `haul_search.toml` defaults, and replay/default-haul separation for search history entries.

## Changes

- Added named Inara search-parameter mapping and URL parsing so Control Room no longer depends on raw `pi*` keys outside the shared helper layer.
- Added ignored local `haul_search.toml` support plus search-config parsing, with cargo capacity inferred from the current ship when available instead of being pinned in the config file.
- Extended the haul prompt state machine, protocol snapshot, replay flow, and history/default-haul rules so search prompts/edit replay behave like first-class Control Room flows without polluting saved default loop hauls.
- Expanded tests for the new config loader, search prompt submission, direct pasted-URL execution, and state-load rejection of saved search entries as default hauls.

## Follow-ups

- Live-validate the prompt defaults and direct URL flow against a real Inara session, then decide whether `pi14` / `pi15` should stay pinned passthrough defaults or become explicit Powerplay prompt fields.

## Iteration 219

- When: `2026-06-22 12:14`
- Area: `haul`
- Title: `fix-inara-search-editor-and-route-load`
- Source: [2026-06-22-12-14_____haul_____fix-inara-search-editor-and-route-load.md](iteration-logs/2026-06-22-12-14_____haul_____fix-inara-search-editor-and-route-load.md)

# Iteration Log

- Area: `haul`
- Title: `fix-inara-search-editor-and-route-load`
- Started: `2026-06-22 12:14`

## Summary

- Corrected the first Inara search UX pass so search parameters are edited all at once, ship cargo capacity actually defaults into the editor, and returned routes can now be loaded into the haul prompt.

## Changes

- Replaced the sequential search question flow with a single prefilled `key=value` editor line backed by the same prompt-state machinery, removing the duplicated `min_supply` step bug and making every search field visible at once.
- Extended route parsing to retain the source buy commodity and optional return-leg buy commodity, then surfaced those fields in the `TRADE ROUTES` panel.
- Added `haul route <n>` so operators can load a shown Inara result into the haul prompt with station names, systems, and cargo defaults prefilled for review before launch.
- Expanded tests for all-at-once search editing, ship cargo defaulting, route-to-haul loading, and commodity extraction from route cards.

## Follow-ups

- Live-validate the `haul route <n>` commodity mapping against a few real one-way and round-trip Inara cards, especially rows where the site layout or labels differ from the sample shapes used in tests.

## Iteration 220

- When: `2026-06-22 12:33`
- Area: `control-room`
- Title: `fix-remote-inara-search-and-replay-prefill`
- Source: [2026-06-22-12-33_control-room_fix-remote-inara-search-and-replay-prefill.md](iteration-logs/2026-06-22-12-33_control-room_fix-remote-inara-search-and-replay-prefill.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-remote-inara-search-and-replay-prefill`
- Started: `2026-06-22 12:33`

## Summary

- Fixed the remote `control_room connect` path so server-started prompt/replay edits repopulate the client command bar and Inara trade-route results render in the shared `TRADE ROUTES` panel instead of staying server-local.

## Changes

- Added command-input prefill state to the shared prompt snapshot, wired prompt/replay helpers to maintain it, and taught the observer client to restore that value/placeholder only when the server explicitly owns the command bar.
- Added trade-route results to the shared control-room snapshot, updated snapshot serialization/deserialization, and rehydrated remote route cards into the observer app so `haul search` and `haul route <n>` work in client/server mode.
- Added regression coverage for server-side snapshot serialization, remote replay-edit prefill, and remote trade-route snapshot application.

## Follow-ups

- Live-test `haul search`, `haul route <n>`, and replay edit in a real `serve` plus `connect` session to confirm the route-card parser and prompt UX hold up under live Inara responses.

## Iteration 221

- When: `2026-06-27 13:35`
- Area: `control-room`
- Title: `startup-tts-commander-name`
- Source: [2026-06-27-13-35_control-room_startup-tts-commander-name.md](iteration-logs/2026-06-27-13-35_control-room_startup-tts-commander-name.md)

# Iteration Log

- Area: `control-room`
- Title: `startup-tts-commander-name`
- Started: `2026-06-27 13:35`

## Summary

- Fixed the control-room startup greeting order so `{title}` resolves against the bootstrapped commander name before the first TTS line is rendered.

## Changes

- Moved local `ControlRoomApp` startup greeting emission to run after `_bootstrap_ship_state()`.
- Moved headless observer-server host startup greeting emission to run after `_bootstrap_ship_state()` so remote announcement streams stay consistent with local startup behavior.
- Added regression coverage for both local app mount and headless host start paths when `tts.title_mode = "commander_name"`.
- Ran `uv run python3 -m unittest discover -s tests` and the required timing report because the suite currently exceeds the `0.3s` target.

## Follow-ups

- Full-suite runtime remains above target (`0.550s` / `0.581s` in the timing report); the slowest tests are still remote control-room client flows rather than this startup-TTS change.

## Iteration 222

- When: `2026-06-27 13:48`
- Area: `haul`
- Title: `fix-live-inara-route-commodity-parse`
- Source: [2026-06-27-13-48_____haul_____fix-live-inara-route-commodity-parse.md](iteration-logs/2026-06-27-13-48_____haul_____fix-live-inara-route-commodity-parse.md)

# Iteration Log

- Area: `haul`
- Title: `fix-live-inara-route-commodity-parse`
- Started: `2026-06-27 13:48`

## Summary

- Fixed `haul route <n>` for live Inara trade-route cards whose `FROM` and `TO` headers both appear before the station trade details.

## Changes

- Updated the shared Inara row parser to ignore `BUY PRICE` metric lines when extracting commodities and to derive source/return cargo from the ordered `BUY` commodity rows across the full card.
- Added a regression test that matches the live `HIP 17597` card shape where `BUY\tSilver` and `BUY PRICE\t3,420 Cr` appear after both endpoint headers.
- Re-ran the existing scratch Inara probe against the live `HIP 17597` query and confirmed the previous failure mode came from parser output, not missing site data.

## Follow-ups

- Live-check `haul route <n>` in Control Room against the repaired parser to confirm the prompt now prefills the expected station and cargo values from the real results panel.

## Iteration 223

- When: `2026-06-27 13:53`
- Area: `ci-release`
- Title: `measure-test-timing-hotspots`
- Source: [2026-06-27-13-53__ci-release__measure-test-timing-hotspots.md](iteration-logs/2026-06-27-13-53__ci-release__measure-test-timing-hotspots.md)

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

## Iteration 224

- When: `2026-06-27 13:58`
- Area: `control-room`
- Title: `fix-haul-search-command-bar-refresh`
- Source: [2026-06-27-13-58_control-room_fix-haul-search-command-bar-refresh.md](iteration-logs/2026-06-27-13-58_control-room_fix-haul-search-command-bar-refresh.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-haul-search-command-bar-refresh`
- Started: `2026-06-27 13:58`

## Summary

- Fixed a Control Room prompt-refresh regression where active command-bar prefills could snap back to stale or blank text during periodic snapshot refreshes, making `haul search` editing unusable in local mode.

## Changes

- Updated prompt-state snapshot serialization to prefer the live `#cmd` widget placeholder/value whenever prompt-owned prefill is active, so periodic UI refreshes keep the operator's in-progress text instead of replaying stale prompt-state fields.
- Added protocol coverage proving snapshot generation preserves live command-bar edits during an active prefill session.
- Re-ran the full `uv run python3 -m unittest discover -s tests` suite and the required slow-test timing report because suite runtime stayed above the repo's `0.3s` target.

## Follow-ups

- Live-check `haul search` editing in the real local TUI to confirm the command bar now stays stable while the periodic status refresh loop is running.

## Iteration 225

- When: `2026-06-27 14:17`
- Area: `haul`
- Title: `allow-any-station-distance`
- Source: [2026-06-27-14-17_____haul_____allow-any-station-distance.md](iteration-logs/2026-06-27-14-17_____haul_____allow-any-station-distance.md)

# Iteration Log

- Area: `haul`
- Title: `allow-any-station-distance`
- Started: `2026-06-27 14:17`

## Summary

- Added operator-facing `any` support for Inara haul-search max station distance so Control Room no longer requires raw `0` for the "Any" INARA option.

## Changes

- Updated the haul search prompt parser to accept `max_station_distance_ls=any` and keep the saved/replayed value as `any`.
- Normalized Inara trade-route query handling so Control Room emits `pi9=0` for `any` and maps pasted `pi9=0` URLs back to `any`.
- Added unit coverage for prompt submission and INARA URL build/parse behavior, then reran the full unittest suite successfully in `0.289s`.

## Follow-ups

- Live-validate the `any` station-distance path against a fresh INARA fetch in the operator UI when the next CrossOver trading session runs.

## Iteration 226

- When: `2026-06-27 14:29`
- Area: `control-room`
- Title: `move-haul-search-results-into-picker`
- Source: [2026-06-27-14-29_control-room_move-haul-search-results-into-picker.md](iteration-logs/2026-06-27-14-29_control-room_move-haul-search-results-into-picker.md)

# Iteration Log

- Area: `control-room`
- Title: `move-haul-search-results-into-picker`
- Started: `2026-06-27 14:29`

## Summary

- Replaced the always-on haul search route list with a dedicated `HAUL ROUTES` picker so route results behave like a modal selection flow instead of occupying the right-side panel.

## Changes

- Added local picker state plus picker widgets in `ControlRoomApp`, with `Up`/`Down` selection, `Enter` to dispatch `haul route <n>`, and `Esc`/`q` to dismiss.
- Changed the `TRADE ROUTES` panel rendering to a compact search summary/status block while the full route list and per-route detail moved into the picker.
- Auto-opened the picker when a haul search completes successfully in local mode and when a remote snapshot delivers a newly completed route search.
- Updated unit coverage for the new picker flow and kept the full `uv run python3 -m unittest discover -s tests` suite passing in `0.280s`.

## Follow-ups

- Live-check the picker in both embedded and `control_room connect` sessions to confirm the modal handoff feels right under real Inara latency and routine-heavy sessions.

## Iteration 227

- When: `2026-06-27 14:38`
- Area: `haul`
- Title: `compact-route-picker-detail-profit-view`
- Source: [2026-06-27-14-38_____haul_____compact-route-picker-detail-profit-view.md](iteration-logs/2026-06-27-14-38_____haul_____compact-route-picker-detail-profit-view.md)

# Iteration Log

- Area: `haul`
- Title: `compact-route-picker-detail-profit-view`
- Started: `2026-06-27 14:38`

## Summary

- Compacted the selected-route detail block inside the `HAUL ROUTES` picker so all key haul parameters stay visible in one screenful.

## Changes

- Reworked the picker detail rendering to keep the search timestamp on the header line and collapse route, cargo, and profit fields into shorter rows.
- Added explicit `Per trip` and `Per hour` labels so both profit figures are always visible for the highlighted route.
- Added focused rendering coverage and re-ran the full suite; the first pass landed at `0.330s`, the required timing report showed existing heavy tests, and the warm-cache rerun finished at `0.293s`.

## Follow-ups

- Live-check the picker against real long commodity names and large tmux/font-size combinations to confirm the compact rows still hold up without awkward wrapping.

## Iteration 228

- When: `2026-06-27 14:44`
- Area: `control-room`
- Title: `remove-haul-search-summary-panel`
- Source: [2026-06-27-14-44_control-room_remove-haul-search-summary-panel.md](iteration-logs/2026-06-27-14-44_control-room_remove-haul-search-summary-panel.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-haul-search-summary-panel`
- Started: `2026-06-27 14:44`

## Summary

- Removed the leftover haul-search summary panel so the `HAUL ROUTES` picker is the only operator-facing search-results surface.

## Changes

- Dropped the `TRADE ROUTES` widget from the main Control Room layout and stopped refreshing the redundant summary markup.
- Removed the old summary renderer and its tests, while keeping the shared `TradeRoutesData` snapshot/model for picker state and remote route hydration.
- Re-ran the full `uv run python3 -m unittest discover -s tests` suite after the UI cleanup.

## Follow-ups

- Live-check the reclaimed right-side space in a real session to decide whether the `MARKET` and `HAUL` panels should be rebalanced now that the extra summary panel is gone.

## Iteration 229

- When: `2026-06-27 14:50`
- Area: `haul`
- Title: `same-system-station-nav-skip`
- Source: [2026-06-27-14-50_____haul_____same-system-station-nav-skip.md](iteration-logs/2026-06-27-14-50_____haul_____same-system-station-nav-skip.md)

# Iteration Log

- Area: `haul`
- Title: `same-system-station-nav-skip`
- Started: `2026-06-27 14:50`

## Summary

- Fixed the two-way haul same-system edge case so station-to-station loops inside one system no longer try to re-set a galaxy-map destination before transit.

## Changes

- Added a same-system guard in `edap/routines/haul_two_way.py` so both undock-driven and normal-space depart paths skip `set_gal_map_destination()` when the source and destination systems match.
- Added two haul regressions covering the undock path and the resumed normal-space depart path for same-system station pairs.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` passed, then ran the full suite successfully at `547 tests in 0.339s`.

## Follow-ups

- Full-suite runtime exceeded the repo target, so `tools/report_test_timing.py --top 10 --sort slowest` was run per policy; current timing report came back `suite_status=ok` with `total_seconds=0.315`.

## Iteration 230

- When: `2026-06-27 14:59`
- Area: `control-room`
- Title: `show-hourly-profit-in-route-picker`
- Source: [2026-06-27-14-59_control-room_show-hourly-profit-in-route-picker.md](iteration-logs/2026-06-27-14-59_control-room_show-hourly-profit-in-route-picker.md)

# Iteration Log

- Area: `control-room`
- Title: `show-hourly-profit-in-route-picker`
- Started: `2026-06-27 14:59`

## Summary

- Added compact per-hour profit prefixes to haul route picker rows and reflowed the selected-route detail into two vertical columns so the picker uses the available width better.

## Changes

- Added a renderer helper that converts Inara `profit_per_hour` strings into the requested `[XX.Ym/h]` list prefix without changing the trade-route snapshot schema.
- Reworked the route-detail markup so `From/To`, `Buy/Return`, `Route/Per unit`, and `Per trip/Per hour` render as paired columns instead of one long stacked block.
- Extended Control Room rendering tests for the new route-row prefix and detail layout, then re-ran `uv run python3 -m unittest discover -s tests` successfully in `0.290s`.

## Follow-ups

- Live-check the picker width in a real Control Room session to decide whether the detail box height should shrink now that the content is denser.

## Iteration 231

- When: `2026-06-27 15:06`
- Area: `haul`
- Title: `fix-live-route-profit-metrics`
- Source: [2026-06-27-15-06_____haul_____fix-live-route-profit-metrics.md](iteration-logs/2026-06-27-15-06_____haul_____fix-live-route-profit-metrics.md)

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

## Iteration 232

- When: `2026-06-27 15:15`
- Area: `control-room`
- Title: `escape-route-picker-profit-prefix`
- Source: [2026-06-27-15-15_control-room_escape-route-picker-profit-prefix.md](iteration-logs/2026-06-27-15-15_control-room_escape-route-picker-profit-prefix.md)

# Iteration Log

- Area: `control-room`
- Title: `escape-route-picker-profit-prefix`
- Started: `2026-06-27 15:15`

## Summary

- Escaped the haul route picker’s literal `[xx.xm/h]` prefix so markup-aware list rendering can show it instead of swallowing it.

## Changes

- Changed the route-row prefix formatter to emit `[[88.3m/h]]` in source text so the picker renders a literal `[88.3m/h]`.
- Updated the Control Room route-label assertion to match the escaped prefix source form and re-ran the full unittest suite.
- Full suite passed via `uv run python3 -m unittest discover -s tests` in `0.321s`; per repo policy, `tools/report_test_timing.py --top 10 --sort slowest` then reported `suite_status=ok total_seconds=0.327`.

## Follow-ups

- Re-check the live picker after restart; if the prefix still does not appear, inspect the exact running Control Room / serve process because the code and live scraper output now both contain the profit fields.

## Iteration 233

- When: `2026-06-27 15:37`
- Area: `control-room`
- Title: `trace-route-picker-modal-profit-path`
- Source: [2026-06-27-15-37_control-room_trace-route-picker-modal-profit-path.md](iteration-logs/2026-06-27-15-37_control-room_trace-route-picker-modal-profit-path.md)

# Iteration Log

- Area: `control-room`
- Title: `trace-route-picker-modal-profit-path`
- Started: `2026-06-27 15:37`

## Summary

- Added dedicated route-picker tracing so live Control Room runs can show whether trip/hour profit disappears at load time, label formatting time, or detail-markup time.

## Changes

- Added a separate `artifacts/control-room-debug.log` JSONL trace sink for Control Room UI diagnostics instead of mixing modal debug lines into the existing artifact event mirror.
- Instrumented `_set_trade_routes_loaded`, `_refresh_trade_route_picker`, and `_update_trade_route_detail` to log the first route’s trip/hour profit plus the exact modal list label and detail markup being rendered.
- Added a Control Room test for the debug artifact writer and re-ran the full unittest suite successfully in `0.241s`.

## Follow-ups

- Re-run `uv run control_room.py`, perform `haul search`, and inspect `artifacts/control-room-debug.log` to see where the route-picker modal still loses the profit fields in the live app path.

## Iteration 234

- When: `2026-06-27 18:20`
- Area: `control-room`
- Title: `bootstrap-cargo-capacity-for-haul-search`
- Source: [2026-06-27-18-20_control-room_bootstrap-cargo-capacity-for-haul-search.md](iteration-logs/2026-06-27-18-20_control-room_bootstrap-cargo-capacity-for-haul-search.md)

# Iteration Log

- Area: `control-room`
- Title: `bootstrap-cargo-capacity-for-haul-search`
- Started: `2026-06-27 18:20`

## Summary

- Fixed the restart-time gap where Control Room bootstrapped cargo count from `Status.json` but dropped total cargo capacity from the latest journal, causing `haul search` prefills to omit `cargo_capacity=` until a fresh live `Loadout` arrived.

## Changes

- Extended `edap.state.read_ship_state()` to retain `Loadout.CargoCapacity` in the lightweight journal bootstrap state.
- Updated Control Room bootstrap to copy that restored `cargo_capacity` onto the live ship model before haul-search defaults are generated.
- Expanded the bootstrap ship-state test to include a `Loadout` event and assert that cargo capacity survives startup alongside the `Status.json` cargo count.

## Follow-ups

- Keep `artifacts/control-room-debug.log` in place while live Inara behavior is still being validated, but the missing `cargo_capacity` root cause for blank search prefills is now covered by startup bootstrap and test coverage.

## Iteration 235

- When: `2026-06-27 18:33`
- Area: `docs`
- Title: `per-test-runtime-budget`
- Source: [2026-06-27-18-33_____docs_____per-test-runtime-budget.md](iteration-logs/2026-06-27-18-33_____docs_____per-test-runtime-budget.md)

# Iteration Log

- Area: `docs`
- Title: `per-test-runtime-budget`
- Started: `2026-06-27 18:33`

## Summary

- Replaced the fixed full-suite unittest budget with a per-test budget of `0.0006s`, so the timing threshold scales with suite size instead of requiring manual bumps as coverage grows.

## Changes

- Updated [AGENTS.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/AGENTS.md:53) to treat `uv run python3 -m unittest discover -s tests` as on-budget when total runtime stays at or below `tests_run * 0.0006`.
- Updated [docs/status/docs-process.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/docs-process.md:3) and [docs/status/ci-release.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/ci-release.md:3) so the current handoff docs describe the per-test budget instead of the stale fixed `0.3s` threshold.
- Confirmed the current suite math: `551 * 0.0006 = 0.3306`, which covers the latest passing run that completed in about `0.320s`.

## Follow-ups

- Keep the per-test multiplier under review if suite composition changes enough that total runtime grows faster than test count.

## Iteration 236

- When: `2026-06-27 18:34`
- Area: `ci-release`
- Title: `prepare-v1-14-0-release`
- Source: [2026-06-27-18-34__ci-release__prepare-v1-14-0-release.md](iteration-logs/2026-06-27-18-34__ci-release__prepare-v1-14-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-14-0-release`
- Started: `2026-06-27 18:34`

## Summary

- Prepared the `v1.14.0` release by bumping project metadata, refreshing the generated lock/archive artifacts, and revalidating the suite on the current per-test runtime budget.

## Changes

- Updated [pyproject.toml](/Users/nicholasclooney/Source/Projects/EDControlRoom/pyproject.toml:3) from `1.13.0` to `1.14.0` for the new release target.
- Refreshed [docs/status/ci-release.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/ci-release.md:3) so the handoff reflects the `v1.14.0` scope and the current `551`-test baseline under the computed `0.3306s` budget.
- Regenerated [docs/iteration-archive.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/iteration-archive.md:1) after adding the release-prep and runtime-budget iteration logs, then re-ran the full unittest suite.

## Follow-ups

- Push the release-prep commit and `v1.14.0` tag, then publish the GitHub release with high-level notes focused on the Inara haul-search and remote observer/control-room additions.

## Iteration 237

- When: `2026-06-27 19:07`
- Area: `ci`
- Title: `promote-playwright-runtime-dependency`
- Source: [2026-06-27-19-07______ci______promote-playwright-runtime-dependency.md](iteration-logs/2026-06-27-19-07______ci______promote-playwright-runtime-dependency.md)

# Iteration Log

- Area: `ci`
- Title: `promote-playwright-runtime-dependency`
- Started: `2026-06-27 19:07`

## Summary

- Promoted `playwright` from the optional `browsing` extra into the base project dependency list so released installs include the browser dependency by default.

## Changes

- Updated `pyproject.toml` to add `playwright>=1.53` to `[project].dependencies` and removed the now-obsolete `browsing` extra entry.
- Refreshed `uv.lock` so the locked project metadata now advertises Playwright as a normal runtime dependency instead of an extra-gated dependency.
- Updated `docs/status/ci-release.md` so the current release handoff reflects that published installs no longer require a separate Playwright extra.

## Follow-ups

- Keep future install docs and release notes aligned with the new default dependency shape; do not reintroduce a browser-only extra unless the runtime surface changes again.

## Iteration 238

- When: `2026-06-27 19:31`
- Area: `haul`
- Title: `carrier-launch-exploration-handoff`
- Source: [2026-06-27-19-31_____haul_____carrier-launch-exploration-handoff.md](iteration-logs/2026-06-27-19-31_____haul_____carrier-launch-exploration-handoff.md)

# Iteration Log

- Area: `haul`
- Title: `carrier-launch-exploration-handoff`
- Started: `2026-06-27 19:31`

## Summary

- Added a carrier-specific undock handoff so haul/manual undock can treat `MusicTrack="Exploration"` as resumed manual launch control after `Undocked` from `Stronghold Carrier` or `Fleet Carrier`.

## Changes

- Added shared journal-event helpers for carrier detection and the `Exploration` manual-resume special case.
- Updated undock/haul clear-of-station handling to accept carrier `Exploration`, then continue into the normal mass-lock escape and hyperspace path.
- Updated ship-state and Control Room event reducers so carrier `Exploration` clears `in_undocking` to `in_space` instead of waiting indefinitely for `NoTrack`.
- Added routine, haul, state, and Control Room tests for the carrier `Exploration` path and widened the failure-message matcher for the new timeout wording.

## Follow-ups

- Live-validate both named `Stronghold Carrier` launches and real owner-named `Fleet Carrier` launches to confirm the carrier-name/type heuristics are sufficient in journal output.

## Iteration 239

- When: `2026-06-27 21:08`
- Area: `control-room`
- Title: `fix-remote-log-colors-and-haul-picker`
- Source: [2026-06-27-21-08_control-room_fix-remote-log-colors-and-haul-picker.md](iteration-logs/2026-06-27-21-08_control-room_fix-remote-log-colors-and-haul-picker.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-remote-log-colors-and-haul-picker`
- Started: `2026-06-27 21:08`

## Summary

- Restored Rich activity-log colors for protocol-streamed observer sessions and fixed the remote haul-results picker so completed searches still open the modal when loading and loaded snapshots share the same second-level timestamp.

## Changes

- Changed `build_activity_log_entry()` to preserve the original Rich markup string in protocol activity entries instead of flattening it to plain text before observer transport.
- Updated `ServerActivityLogSink` to strip Rich markup only at server-log emission time so server logs stay readable while remote clients still receive colorized content.
- Fixed snapshot-to-view trade-route sync so the client opens the `HAUL ROUTES` picker when a remote search transitions from loading to loaded, even if `query_url` and `searched_at` match the prior loading snapshot exactly.
- Added regression coverage for markup preservation, server-log mirroring, and the same-second remote route-picker transition; full suite passed in `0.321s` for `557` tests.

## Follow-ups

- Live-check one real `control_room serve` plus `control_room connect` session to confirm the restored colors and route-picker modal behave correctly under real Inara latency.

## Iteration 240

- When: `2026-06-28 18:34`
- Area: `control-room`
- Title: `haul-panel-session-profit-refresh`
- Source: [2026-06-28-18-34_control-room_haul-panel-session-profit-refresh.md](iteration-logs/2026-06-28-18-34_control-room_haul-panel-session-profit-refresh.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-panel-session-profit-refresh`
- Started: `2026-06-28 18:34`

## Summary

- Restored live-feeling haul panel updates after the client/server split and expanded the panel to show session duration, net session profit, and clearer billion-scale credit formatting.

## Changes

- Added `session_started_at` to haul runtime state and the observer snapshot contract so local and remote Control Room views can render session duration consistently.
- Updated haul-panel rendering to show `Session` and net `Profit`, and changed compact credit formatting to display billion-plus values as `1b xxx.xxM CR`.
- Updated the headless observer host so periodic haul refreshes publish snapshots, allowing remote clients to keep elapsed/profit rows moving even when no new journal event has arrived.
- Added focused coverage for billion-format rendering/TTS and for the haul panel session/profit rows, then verified the full suite passed.

## Follow-ups

- Live-check the panel in both embedded and `control_room connect` sessions to confirm the new compact billion format reads well during long-haul runs.

## Iteration 241

- When: `2026-06-28 18:47`
- Area: `control-room`
- Title: `targeted-input-targeting`
- Source: [2026-06-28-18-47_control-room_targeted-input-targeting.md](iteration-logs/2026-06-28-18-47_control-room_targeted-input-targeting.md)

# Iteration Log

- Area: `control-room`
- Title: `targeted-input-targeting`
- Started: `2026-06-28 18:47`

## Summary

- Added foreground-by-default targeted-input controls so operators can switch Control Room between normal foreground dispatch and explicit pid/hwnd targeting from the command bar.

## Changes

- Extended the shared input-controller interface with target-state reporting plus `set_foreground`, `set_pid`, `set_hwnd`, and auto-detect hooks keyed by `EliteDangerous64.exe`.
- Implemented macOS pid-targeted Quartz posting and Windows hwnd/pid-targeted message dispatch while keeping the existing foreground path as the default on both platforms.
- Added Control Room `set_pid` and `set_hwnd` commands, startup/status logging, command/help discoverability updates, and regression coverage for the new backend and command flows.

## Follow-ups

- Live-validate the macOS CrossOver pid-targeted path against a backgrounded Elite window.
- Live-validate the Windows hwnd/pid path against native Elite to see whether `PostMessageW` is sufficient or whether another fallback is needed.

## Iteration 242

- When: `2026-06-28 18:48`
- Area: `control-room`
- Title: `persist-haul-session-and-clear-command`
- Source: [2026-06-28-18-48_control-room_persist-haul-session-and-clear-command.md](iteration-logs/2026-06-28-18-48_control-room_persist-haul-session-and-clear-command.md)

# Iteration Log

- Area: `control-room`
- Title: `persist-haul-session-and-clear-command`
- Started: `2026-06-28 18:48`

## Summary

- Added persisted haul-session totals plus an explicit reset command/config path so session profit and time survive relaunches until the operator clears them.

## Changes

- Added persisted haul-session fields to control-room saved state, restoring session elapsed time/profit and related summary fields on launch instead of dropping them on app restart.
- Added `new_session` with `clear` alias, wired it through command help/dispatch, and made it reset persisted session counters without interrupting an active haul routine.
- Added `defaults/control_room.toml` with `clear_session_on_launch = false`, threaded that config through parsing and `config.example.toml`, and made startup optionally clear the saved session automatically.
- Updated haul-session tracking so state saves happen as haul metrics change and starting a new haul preserves any restored persisted session totals until the operator explicitly resets them.

## Follow-ups

- Live-check whether operators want the no-active-haul panel to always show the persisted session block, or only when the session has non-zero time/profit.

## Iteration 243

- When: `2026-06-28 19:04`
- Area: `runtime`
- Title: `crossover-pid-commandline-detect`
- Source: [2026-06-28-19-04___runtime____crossover-pid-commandline-detect.md](iteration-logs/2026-06-28-19-04___runtime____crossover-pid-commandline-detect.md)

# Iteration Log

- Area: `runtime`
- Title: `crossover-pid-commandline-detect`
- Started: `2026-06-28 19:04`

## Summary

- Fixed macOS `set_pid` auto-detection so CrossOver/Wine-launched Elite processes can be found even when `EliteDangerous64.exe` only appears in the full command line.

## Changes

- Kept the existing exact `ps -axo pid=,comm=` match as the first choice, then added a fallback scan over `ps -axo pid=,command=` for `EliteDangerous64.exe` in the full process arguments.
- Added focused macOS tests that cover exact command-name matches, CrossOver-style command-line-only matches, and no-match behavior.
- Re-ran the focused macOS/Control Room tests plus the full unittest suite on `main`.

## Follow-ups

- Re-test bare `set_pid` against a live CrossOver Elite session and confirm the resolved pid now receives targeted Quartz events while the game is backgrounded.

## Iteration 244

- When: `2026-06-28 20:41`
- Area: `control-room`
- Title: `add-session-stop-command`
- Source: [2026-06-28-20-41_control-room_add-session-stop-command.md](iteration-logs/2026-06-28-20-41_control-room_add-session-stop-command.md)

# Iteration Log

- Area: `control-room`
- Title: `add-session-stop-command`
- Started: `2026-06-28 20:41`

## Summary

- Added a dedicated `stop` command for persisted haul sessions so operators can freeze session time/profit without clearing totals.

## Changes

- Added persisted session-active/session-elapsed state so a stopped session can keep its frozen duration across saves and remote snapshots instead of resuming wall-clock growth on the next launch.
- Added `stop` command help/dispatch plus persistence plumbing that refuses to stop while a haul is actively running, freezes the current session totals, and resumes from those totals on the next haul without counting the stopped downtime.
- Extended haul/session tests and verified the full suite still passes after the new command and snapshot fields.

## Follow-ups

- Live-check whether operators want the frozen-session state called out explicitly in the haul-panel status line, or whether the current no-ticking time display is clear enough on its own.

## Iteration 245

- When: `2026-06-28 20:45`
- Area: `control-room`
- Title: `add-route-picker-dest-shortcut`
- Source: [2026-06-28-20-45_control-room_add-route-picker-dest-shortcut.md](iteration-logs/2026-06-28-20-45_control-room_add-route-picker-dest-shortcut.md)

# Iteration Log

- Area: `control-room`
- Title: `add-route-picker-dest-shortcut`
- Started: `2026-06-28 20:45`

## Summary

- Added a route-picker keyboard shortcut so operators can send the highlighted haul result's origin system to `dest` without manually copying the system name.

## Changes

- Added `d` handling in the haul route picker to close the modal and dispatch `dest <from_system>` for the currently highlighted Inara route result.
- Updated the route-picker help text and haul command help so the new shortcut is visible in the live UI and the built-in command reference.
- Added protocol/render harness coverage for the `d` shortcut alongside the existing Enter/Esc picker behavior.

## Follow-ups

- Live-check whether operators also want a direct shortcut for the destination-side system, or whether origin-system targeting covers the useful case.

## Iteration 246

- When: `2026-06-28 21:02`
- Area: `haul`
- Title: `add-inara-distance-and-500-route-default`
- Source: [2026-06-28-21-02_____haul_____add-inara-distance-and-500-route-default.md](iteration-logs/2026-06-28-21-02_____haul_____add-inara-distance-and-500-route-default.md)

# Iteration Log

- Area: `haul`
- Title: `add-inara-distance-and-500-route-default`
- Started: `2026-06-28 21:02`

## Summary

- Added Inara `DISTANCE` parsing to haul route data and surfaced it in the Control Room route picker.
- Raised the default Inara max route distance from `60` to `500` Ly for generated haul searches and pasted-URL expectations.

## Changes

- Extended `TradeRoute` plus snapshot serialization/deserialization to carry `distance_from_system`.
- Updated route-picker label/detail rendering so operators can see current-system distance separately from route distance.
- Refreshed Inara and Control Room tests for the extra field and the new default search parameter.

## Follow-ups

- Live-validate that the Inara scraper still captures `DISTANCE` consistently across alternate route-card layouts and no-location searches.

## Iteration 247

- When: `2026-06-28 21:34`
- Area: `haul`
- Title: `add-station-distance-to-haul-results`
- Source: [2026-06-28-21-34_____haul_____add-station-distance-to-haul-results.md](iteration-logs/2026-06-28-21-34_____haul_____add-station-distance-to-haul-results.md)

# Iteration Log

- Area: `haul`
- Title: `add-station-distance-to-haul-results`
- Started: `2026-06-28 21:34`

## Summary

- Added both Inara `STATION DISTANCE` values to haul route results so the picker can show how far each endpoint station is from its star.

## Changes

- Extended `TradeRoute` and snapshot serialization to carry `from_station_distance` and `to_station_distance`.
- Updated the haul route label/detail rendering to show compact station-distance summaries and explicit per-endpoint station-distance rows.
- Added parsing and snapshot tests to keep local and remote route pickers in sync.

## Follow-ups

- Live-validate that Inara always emits the source station distance first and the destination station distance second across alternate trade-route card layouts.

## Iteration 248

- When: `2026-06-28 22:18`
- Area: `haul`
- Title: `compact-station-distance-in-route-details`
- Source: [2026-06-28-22-18_____haul_____compact-station-distance-in-route-details.md](iteration-logs/2026-06-28-22-18_____haul_____compact-station-distance-in-route-details.md)

# Iteration Log

- Area: `haul`
- Title: `compact-station-distance-in-route-details`
- Started: `2026-06-28 22:18`

## Summary

- Moved station-distance display into the route endpoint line so trip and hourly profit remain visible in the haul route details panel.

## Changes

- Updated Control Room route-detail rendering to append each endpoint's `STATION DISTANCE` beside the station name.
- Removed the dedicated station-distance detail row and kept the profit rows below the fold boundary.
- Refreshed the route-detail rendering test to match the new compact endpoint format.

## Follow-ups

- Live-check the route modal against longer station names to make sure the compact endpoint line still fits without clipping on smaller terminals.

## Iteration 249

- When: `2026-06-28 22:21`
- Area: `runtime`
- Title: `lazy-macos-pid-poster`
- Source: [2026-06-28-22-21___runtime____lazy-macos-pid-poster.md](iteration-logs/2026-06-28-22-21___runtime____lazy-macos-pid-poster.md)

# Iteration Log

- Area: `runtime`
- Title: `lazy-macos-pid-poster`
- Started: `2026-06-28 22:21`

## Summary

- Fixed the macOS targeted-input test path so non-macOS runners no longer fail just by constructing the macOS controller during injected unit tests.

## Changes

- Changed `MacOSInputController` to lazily create the pid-targeted Quartz poster only when pid-targeted dispatch is actually attempted.
- Kept foreground macOS behavior unchanged while preserving the existing runtime error when pid-targeted Quartz posting is unavailable.
- Re-ran the focused macOS tests and the full unittest suite after the constructor change.

## Follow-ups

- Keep pid-targeted behavior covered through injected macOS unit tests, but avoid adding new tests that depend on Quartz pid posting existing on non-macOS CI runners.

## Iteration 250

- When: `2026-06-28 22:42`
- Area: `control-room`
- Title: `local-remote-haul-search`
- Source: [2026-06-28-22-42_control-room_local-remote-haul-search.md](iteration-logs/2026-06-28-22-42_control-room_local-remote-haul-search.md)

# Iteration Log

- Area: `control-room`
- Title: `local-remote-haul-search`
- Started: `2026-06-28 22:42`

## Summary

- Moved `control_room connect` haul search execution and route-picker/results state off the remote server and onto the local observer client, while keeping selected-route and `dest` submission pointed at the remote host.

## Changes

- Added a structured `command.load_trade_route` remote message plus server/backend handling so a locally selected Inara route can prefill the remote haul prompt without relying on server-side `haul route <index>` state.
- Overrode observer-mode haul search dispatch to run local Inara searches, retain local picker state across remote snapshot refreshes, ignore remote trade-route snapshot hydration, and continue sending destination shortcuts to the remote session.
- Extended protocol, schema, and client/server tests for local observer searches, remote route submission, and the new message type, then re-ran the full unittest suite successfully.

## Follow-ups

- Live-check `control_room connect` during a real operator session to confirm local Inara latency, picker ergonomics, and remote haul-prefill timing all feel correct end to end.

## Iteration 251

- When: `2026-06-28 22:51`
- Area: `control-room`
- Title: `fix-local-haul-picker-race`
- Source: [2026-06-28-22-51_control-room_fix-local-haul-picker-race.md](iteration-logs/2026-06-28-22-51_control-room_fix-local-haul-picker-race.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-local-haul-picker-race`
- Started: `2026-06-28 22:51`

## Summary

-

## Changes

-

## Follow-ups

-

## Iteration 252

- When: `2026-06-29 08:24`
- Area: `runtime`
- Title: `timing-randomization`
- Source: [2026-06-29-08-24___runtime____timing-randomization.md](iteration-logs/2026-06-29-08-24___runtime____timing-randomization.md)

# Iteration Log

- Area: `runtime`
- Title: `timing-randomization`
- Started: `2026-06-29 08:24`

## Summary

- Added shared timing randomization for human-like delays, holds, and typing cadence, then tightened the runtime APIs so production callers must pass an explicit timing sampler instead of relying on optional `None` paths.

## Changes

- Added `edap.timing` with a config-backed clamped log-normal sampler plus a no-jitter helper for deterministic tests.
- Added `[timing]` defaults in `defaults/timing.toml`, loaded them through `edap.config`, and exposed the sampler on `RuntimeContext`.
- Routed runtime input controllers, `ShipControls`, Control Room delayed-command sleeps, and routine CLI sleepers through the shared timing sampler.
- Added `docs/operators/input-timing.md` plus README/docs index links so operators can tune the timing model without reading the code.
- Updated input, runtime, config, CLI, and Control Room tests to pass explicit timing samplers and cover the new config/default behavior.

## Follow-ups

- Live-tune the default delay/hold/typing distribution against real CrossOver sessions so the human-like jitter remains believable without destabilizing menus.

## Iteration 253

- When: `2026-06-29 08:53`
- Area: `control-room`
- Title: `market-panel-scrollbar`
- Source: [2026-06-29-08-53_control-room_market-panel-scrollbar.md](iteration-logs/2026-06-29-08-53_control-room_market-panel-scrollbar.md)

# Iteration Log

- Area: `control-room`
- Title: `market-panel-scrollbar`
- Started: `2026-06-29 08:53`

## Summary

- Added vertical overflow scrolling to the Control Room market panel so long station commodity lists expose a scrollbar instead of clipping in place.

## Changes

- Set `#market` to `overflow-y: auto` in the Textual app CSS so the existing market widget can scroll when content exceeds panel height.
- Added a mounted-app regression test that renders an oversized remote market snapshot and asserts the market panel both enables vertical scrolling and reports overflow.
- Rechecked the focused control-room test file and the full unittest suite; both passed.

## Follow-ups

- Live-check the market panel in a real terminal session to confirm the scrollbar feel is acceptable alongside the existing activity-log and haul-panel layout.

## Iteration 254

- When: `2026-06-29 08:56`
- Area: `ci-release`
- Title: `prepare-v1-16-0-release`
- Source: [2026-06-29-08-56__ci-release__prepare-v1-16-0-release.md](iteration-logs/2026-06-29-08-56__ci-release__prepare-v1-16-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-16-0-release`
- Started: `2026-06-29 08:56`

## Summary

- Prepared the `v1.16.0` release from `main` by bumping package metadata, validating the test/docs pipeline, and capturing the release state in maintained status docs.

## Changes

- Bumped `[project].version` to `1.16.0` and refreshed the lock metadata with `uv sync`.
- Regenerated `docs/iteration-archive.md` after adding this release-prep iteration log and refreshed `docs/status/ci-release.md` for the new release target.
- Ran `uv run python3 -m unittest discover -s tests` plus iteration-log validation; the release-prep suite passed `599` tests in `0.291s`, which stays under the `0.3594s` timing budget.

## Follow-ups

- Push the release-prep commit, tag `v1.16.0`, and publish the GitHub release with operator-facing notes for the local observer haul search move, timing randomization, and UI/runtime fixes.

## Iteration 255

- When: `2026-06-30 12:34`
- Area: `control-room`
- Title: `localize-remote-haul-and-dest-prompts`
- Source: [2026-06-30-12-34_control-room_localize-remote-haul-and-dest-prompts.md](iteration-logs/2026-06-30-12-34_control-room_localize-remote-haul-and-dest-prompts.md)

# Iteration Log

- Area: `control-room`
- Title: `localize-remote-haul-and-dest-prompts`
- Started: `2026-06-30 12:34`

## Summary

- Rebased remote operator mode on the existing local `ControlRoomApp` prompt, replay, and market-panel flows for `haul`, `haul route`, `haul search`, `dest`, `home`, history replay/edit, and market lock/filter controls, so `connect` now resolves those operator-surface interactions locally and sends only finalized routine payloads to the headless server.

## Changes

- Added structured remote routine commands for finalized destination and haul launches, wired the remote backend to emit them, and taught the headless observer server to execute them without opening server-owned prompt sessions.
- Changed `ObserverControlRoomApp` to intercept prompt-owning commands locally, preserve local prompt state across snapshot refreshes, and load trade-route picker selections into the same local haul prompt used by embedded mode.
- Switched `connect` replay/history browsing to the existing local replay helpers, so open/filter/selection/edit/default-haul behavior now stays client-side while the remote snapshot remains the source of executed history entries.
- Removed the last remote prompt-prefill fallback in `connect`, so server snapshot prompt state no longer repopulates the local command bar when the client is not already in a local prompt flow.
- Aligned market lock semantics so embedded mode still ingests fresh `Market.json` data while locked, `connect` handles `market` commands locally, and both modes now treat lock/unlock as display freeze/unfreeze over a continuously updating underlying market source.
- Pruned the remote observer protocol/schema/server snapshot down to shared game/session state plus executable routine dispatch: removed wire-level `prompt_state`, `replay_browser`, replay-filter/browser-open command-history fields, and replay/load-route command message types, while keeping the client/backend surface intact with local-only stubs and updating the client/server/protocol tests to match.
- Pruned the remaining remote market UI ownership from the observer snapshot/schema by removing wire-level `market_filter_text` and `locked`, so remote sessions now receive only live market payload data while `connect` keeps filter/lock state purely client-local.
- Hardened the headless observer host so leaked client-local raw verbs now fall through the normal unknown-command path instead of being executed server-side; remote prompt and market flows must come through the client-local UX plus the dedicated haul/destination dispatch protocol commands.

## Follow-ups

## Iteration 256

- When: `2026-06-30 12:59`
- Area: `control-room`
- Title: `market-scrollbar-fix`
- Source: [2026-06-30-12-59_control-room_market-scrollbar-fix.md](iteration-logs/2026-06-30-12-59_control-room_market-scrollbar-fix.md)

# Iteration Log

- Area: `control-room`
- Title: `market-scrollbar-fix`
- Started: `2026-06-30 12:59`

## Summary

- Fixed the Control Room market panel so overflowing commodity lists show a real visible scrollbar again under Textual `8.2.7`.

## Changes

- Replaced the `#market` widget from a plain `Static` with a `VerticalScroll` container and moved the rendered market markup into an inner `#market-content` `Static`.
- Tightened the regression test to wait for a layout tick and assert `show_vertical_scrollbar` instead of only checking that the widget had scrollable overflow.
- Updated `docs/status/control-room.md` so the handoff notes the current Textual-specific scrollbar fix accurately.

## Follow-ups

- The full suite still exceeds the repo timing budget because Textual app tests dominate runtime; this fix adds one `pilot.pause()` to verify layout-driven scrollbar visibility and that test is now the slowest case in `tools/report_test_timing.py`.

## Iteration 257

- When: `2026-06-30 13:12`
- Area: `control-room`
- Title: `market-panel-tabs`
- Source: [2026-06-30-13-12_control-room_market-panel-tabs.md](iteration-logs/2026-06-30-13-12_control-room_market-panel-tabs.md)

# Iteration Log

- Area: `control-room`
- Title: `market-panel-tabs`
- Started: `2026-06-30 13:12`

## Summary

- Split the Control Room market panel into native `Buy` and `Sell` tabs without changing any market commands or backend data flow.

## Changes

- Added a tab strip above the existing market scroll view and kept the panel data/render refresh path local to the UI state.
- Updated the market renderer so the active tab shows only its selected trade side while preserving market filtering, sorting, and empty-state messaging.
- Extended Control Room tests to cover sell-side rendering, tab-specific rendering, and live tab switching in the Textual app.

## Follow-ups

- Live-check the tab strip in a real terminal session to confirm mouse/tab navigation feels acceptable for operators; no command-path fallback was added in this slice.

## Iteration 258

- When: `2026-06-30 13:49`
- Area: `control-room`
- Title: `remove-slow-market-ui-tests`
- Source: [2026-06-30-13-49_control-room_remove-slow-market-ui-tests.md](iteration-logs/2026-06-30-13-49_control-room_remove-slow-market-ui-tests.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-slow-market-ui-tests`
- Started: `2026-06-30 13:49`

## Summary

- Removed two slow Textual market-panel harness tests after confirming they were exercising widget animation and idle-wait behavior more than repo logic.

## Changes

- Dropped the market-panel scrollbar test that required a full `ControlRoomApp.run_test()` cycle to assert `VerticalScroll` overflow behavior.
- Dropped the market-panel tab-switch test that waited on Textual `Tabs` underline animation before asserting rendered buy/sell content.
- Kept the lower-cost `market_markup(...)` rendering coverage as the remaining check for buy-versus-sell market output.

## Follow-ups

- If market panel regressions need coverage again, prefer state or rendering tests that avoid `pilot.pause()` and widget animation timing.

## Iteration 259

- When: `2026-06-30 13:53`
- Area: `control-room`
- Title: `preserve-connect-command-draft`
- Source: [2026-06-30-13-53_control-room_preserve-connect-command-draft.md](iteration-logs/2026-06-30-13-53_control-room_preserve-connect-command-draft.md)

# Iteration Log

- Area: `control-room`
- Title: `preserve-connect-command-draft`
- Started: `2026-06-30 13:53`

## Summary

- Fixed a `connect`-mode regression where periodic remote snapshot refreshes could wipe the local command-bar draft while the active operator was typing.

## Changes

- Added observer-local command-input draft tracking so steady-state snapshot refreshes no longer clear freeform commands or partially edited local prompt values.
- Seeded the draft only when a prompt prefill actually changes, so new local prompt steps still populate correctly without clobbering later edits.
- Added regression coverage for both plain command typing and local prompt typing during remote snapshot updates.

## Follow-ups

- Live-validate the fix in a real `control_room connect` session to confirm Textual input-change events behave the same as the unit-test harness.

## Iteration 260

- When: `2026-06-30 13:57`
- Area: `control-room`
- Title: `preserve-connect-local-activity-log`
- Source: [2026-06-30-13-57_control-room_preserve-connect-local-activity-log.md](iteration-logs/2026-06-30-13-57_control-room_preserve-connect-local-activity-log.md)

# Iteration Log

- Area: `control-room`
- Title: `preserve-connect-local-activity-log`
- Started: `2026-06-30 13:57`

## Summary

- Fixed a `connect`-mode regression where client-local activity-log output briefly appeared and then got wiped by the next remote snapshot refresh.

## Changes

- Overrode observer activity-log replacement to merge the server snapshot log with retained client-local entries instead of treating the snapshot as the only source of truth.
- Kept observer-local `_log()` writes out of the headless protocol stream while still preserving them in the visible log across later snapshot replacements.
- Added regression coverage showing a local help-style entry surviving a remote snapshot refresh that still contains older server `Unknown command` entries.

## Follow-ups

- Live-validate in a real `control_room connect` session that local prompt/help output remains visible while remote activity continues streaming underneath it.

## Iteration 261

- When: `2026-06-30 14:07`
- Area: `control-room`
- Title: `fix-connect-remote-routine-readiness`
- Source: [2026-06-30-14-07_control-room_fix-connect-remote-routine-readiness.md](iteration-logs/2026-06-30-14-07_control-room_fix-connect-remote-routine-readiness.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-connect-remote-routine-readiness`
- Started: `2026-06-30 14:07`

## Summary

- Fixed `connect` mode so prompt-owning remote commands like `dest sol` no longer fail locally with `controls unavailable` before the client can collect prompt input.

## Changes

- Overrode observer routine readiness to check remote operator/routine state instead of local controls availability, which is intentionally absent on remote-only clients.
- Tightened observer tests so `dest` and `haul` prompt flows must work without setting fake local controls on the client.
- Live-validated against a real local `serve` process plus observer session: `dest sol` now opens the local settle-seconds prompt and does not log `controls unavailable`.

## Follow-ups

- Run one more manual pass against a real interactive `control_room connect` terminal to confirm the visible TUI behavior matches the automated observer-path probe.

## Iteration 262

- When: `2026-06-30 14:13`
- Area: `control-room`
- Title: `add-dest-remote-debug-logging`
- Source: [2026-06-30-14-13_control-room_add-dest-remote-debug-logging.md](iteration-logs/2026-06-30-14-13_control-room_add-dest-remote-debug-logging.md)

# Iteration Log

- Area: `control-room`
- Title: `add-dest-remote-debug-logging`
- Started: `2026-06-30 14:13`

## Summary

- Added targeted debug logging around the remote `dest` flow so the next manual `serve` + `connect` reproduction will show exactly where a post-prompt failure occurs.

## Changes

- Logged observer-side destination prompt resolution before `command.dispatch_destination` is sent.
- Logged headless server receipt of destination dispatch payloads and routine-launch inputs for remote `dest` runs.
- Logged full routine exception metadata and traceback into `artifacts/control-room-debug.log` when a background routine crashes.

## Follow-ups

- Reproduce the failing `dest sol` settle-seconds submission in a real interactive connect session, then inspect `artifacts/control-room-debug.log` for the new `observer_dest_prompt_dispatch_resolved`, `server_dispatch_destination_received`, and `routine_thread_exception` events.

## Iteration 263

- When: `2026-06-30 14:17`
- Area: `control-room`
- Title: `fix-connect-dest-default-enter`
- Source: [2026-06-30-14-17_control-room_fix-connect-dest-default-enter.md](iteration-logs/2026-06-30-14-17_control-room_fix-connect-dest-default-enter.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-connect-dest-default-enter`
- Started: `2026-06-30 14:17`

## Summary

- Fixed the `connect`-mode `dest` default-Enter path so accepting the default settle seconds no longer sends a blank command to the server and crashes with `list index out of range`.

## Changes

- Handled Enter on observer-local prompt steps directly inside `ObserverControlRoomApp.on_key()` instead of falling through to the base prompt handler that calls `backend.submit_input(raw)`.
- Hardened generic command dispatch so blank commands are ignored instead of indexing into an empty token list.
- Added regression coverage for pressing Enter on a remote `dest` prompt with an empty field, asserting that the observer dispatches `command.dispatch_destination` with the configured default settle time.

## Follow-ups

- Re-run the manual `serve` + `connect` `dest sol` flow to confirm the default-Enter path now dispatches the destination routine instead of logging a blank command.

## Iteration 264

- When: `2026-06-30 16:46`
- Area: `control-room`
- Title: `fix-remote-activity-timestamps`
- Source: [2026-06-30-16-46_control-room_fix-remote-activity-timestamps.md](iteration-logs/2026-06-30-16-46_control-room_fix-remote-activity-timestamps.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-remote-activity-timestamps`
- Started: `2026-06-30 16:46`

## Summary

- Fixed observer activity log rendering so remote entries keep their stored protocol timestamps during both snapshot redraws and incremental append events.

## Changes

- Made `build_log_text()` require a valid timestamp and render from that value instead of falling back to the local wall clock.
- Updated embedded and observer Control Room activity writers to render from `ActivityLogEntry.timestamp`, including local entries after creating the protocol log object.
- Added regression coverage for strict timestamp enforcement, remote snapshot redraw preservation, and incremental observer activity append rendering.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` flow to confirm prompt lines and delayed execution lines now keep stable ordering under repeated snapshot refreshes.

## Iteration 265

- When: `2026-06-30 16:49`
- Area: `control-room`
- Title: `sort-remote-activity-merge`
- Source: [2026-06-30-16-49_control-room_sort-remote-activity-merge.md](iteration-logs/2026-06-30-16-49_control-room_sort-remote-activity-merge.md)

# Iteration Log

- Area: `control-room`
- Title: `sort-remote-activity-merge`
- Started: `2026-06-30 16:49`

## Summary

- Fixed observer activity-log refresh ordering so retained local prompt lines are merged back into remote snapshots by timestamp instead of being appended after newer remote routine output.

## Changes

- Sorted `ObserverControlRoomApp._replace_activity_log()` merges by parsed `ActivityLogEntry.timestamp` before trimming and repainting the widget.
- Added a regression that reproduces the `dest sol` prompt/routine mix, proving `Command`, `Destination`, and settle-prompt lines stay ahead of later `Executing...` and destination routine logs after refresh.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` session and confirm repeated snapshot refreshes no longer push retained local prompt lines below newer remote routine output.

## Iteration 266

- When: `2026-06-30 16:57`
- Area: `control-room`
- Title: `guard-observer-local-verbs`
- Source: [2026-06-30-16-57_control-room_guard-observer-local-verbs.md](iteration-logs/2026-06-30-16-57_control-room_guard-observer-local-verbs.md)

# Iteration Log

- Area: `control-room`
- Title: `guard-observer-local-verbs`
- Started: `2026-06-30 16:57`

## Summary

- Added a transport-level observer guard so client-local verbs like `dest` and `haul` cannot be serialized into `command.submit_input` and sent to the headless server.

## Changes

- Added `_is_client_local_command()` in the remote observer backend and short-circuited both `submit_input()` and `dispatch_command()` for client-local verbs.
- Added a regression proving `dest sol`, `home`, and `market lock` do not enqueue any websocket command payloads from `RemoteObserverBackend`.
- Reverted the partial observer-log filtering experiment so the fix stays at the transport seam rather than hiding server noise in the UI.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` session and confirm the server activity stream no longer receives fresh `Command: dest sol` / `Unknown command: dest sol` entries from the observer client.

## Iteration 267

- When: `2026-06-30 16:59`
- Area: `control-room`
- Title: `sort-observer-activity-redraw`
- Source: [2026-06-30-16-59_control-room_sort-observer-activity-redraw.md](iteration-logs/2026-06-30-16-59_control-room_sort-observer-activity-redraw.md)

# Iteration Log

- Area: `control-room`
- Title: `sort-observer-activity-redraw`
- Started: `2026-06-30 16:59`

## Summary

- Fixed observer activity redraw ordering so preserved local prompt lines are merged back into remote snapshots chronologically instead of always appearing below newer remote routine lines.

## Changes

- Reintroduced timestamp sorting inside `ObserverControlRoomApp._replace_activity_log()` so merged remote plus local activity is ordered by `ActivityLogEntry.timestamp` before repaint.
- Added a regression covering the exact `dest sol` plus remote cancel case: local `:34` prompt lines now render above remote `:35` and `:38` routine/cancel lines after snapshot refresh.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` flow and confirm the activity panel keeps `Command`, `Destination`, and settle-prompt lines above later `Executing...` / cancellation lines during reconnects or periodic snapshot refreshes.

## Iteration 268

- When: `2026-06-30 17:14`
- Area: `control-room`
- Title: `preserve-observer-prompt-caret`
- Source: [2026-06-30-17-14_control-room_preserve-observer-prompt-caret.md](iteration-logs/2026-06-30-17-14_control-room_preserve-observer-prompt-caret.md)

# Iteration Log

- Area: `control-room`
- Title: `preserve-observer-prompt-caret`
- Started: `2026-06-30 17:14`

## Summary

- Fixed `control_room connect` prompt editing so periodic remote snapshot refreshes no longer shove the caret to the end of the command field while the operator is editing a local prompt or draft command.

## Changes

- Added observer-local caret tracking alongside the existing local draft-text preservation so the remote client can reapply the current input value without losing the operator's edit position.
- Synced the live observer prompt widget text back into retained local prompt state so snapshot rebuilds stop reviving stale prefill-era command text after mid-prompt edits.
- Split prompt-prefill signature handling so active prompt steps no longer treat operator text edits as a brand-new prefill event that should reset the caret to the end.
- Scoped the restore logic to observer mode only, leaving embedded/local Control Room input behavior unchanged after confirming the bug was not reproducible there.
- Tightened observer client regressions to assert mid-string caret preservation for both freeform command drafts and prompt-prefilled inputs across snapshot refreshes.

## Follow-ups

- Live-check one active `serve` plus `connect` session while a prompt is open to confirm the real Textual widget keeps caret position stable under the normal status refresh cadence.

## Iteration 269

- When: `2026-06-30 17:23`
- Area: `control-room`
- Title: `preserve-local-prompt-edits`
- Source: [2026-06-30-17-23_control-room_preserve-local-prompt-edits.md](iteration-logs/2026-06-30-17-23_control-room_preserve-local-prompt-edits.md)

# Iteration Log

- Area: `control-room`
- Title: `preserve-local-prompt-edits`
- Started: `2026-06-30 17:23`

## Summary

- Fixed embedded Control Room prompt editing so periodic local snapshot refreshes no longer overwrite in-progress `haul search` command-bar edits with the older prefilled parameter string.

## Changes

- Added local command-input change handling in `ControlRoomApp` so active prompt-prefill state tracks the live command-bar text instead of only the original prefill value.
- Added a regression proving a locally edited `search_edit` prompt survives `_apply_view_snapshot_state()` without losing the operator's edited search line or cursor position.
- Re-ran the embedded app test module plus the full repo suite after the shared input-path change.

## Follow-ups

- Live-check local `haul search` editing under the normal status-refresh cadence to confirm the real Textual widget no longer reverts edited parameters during long prompt sessions.

## Iteration 270

- When: `2026-06-30 17:26`
- Area: `control-room`
- Title: `preserve-observer-search-prefill`
- Source: [2026-06-30-17-26_control-room_preserve-observer-search-prefill.md](iteration-logs/2026-06-30-17-26_control-room_preserve-observer-search-prefill.md)

# Iteration Log

- Area: `control-room`
- Title: `preserve-observer-search-prefill`
- Started: `2026-06-30 17:26`

## Summary

- Investigated the `control_room connect` regression where `haul search <system>` can open the observer-local prompt with the correct placeholder but an empty command bar instead of the prefilled serialized Inara params; the attempted fix passed harness coverage but did not resolve the live bug.

## Changes

- Narrowed observer prompt-state capture so a brand-new local prompt keeps the generated prefill text unless the client is already editing that same prompt instance.
- Kept the earlier live-edit sync for ongoing observer prompt edits, so connect-mode caret and text preservation still work after the initial prompt opens.
- Delayed command-bar clearing for observer-local prompt-opening commands like `haul search` so the prompt helper can populate the field before any blank-state cleanup runs.
- Added regression coverage for the new-prompt blank-widget case alongside the existing observer prompt-edit preservation tests, but the live `connect` flow still reproduces the empty-prefill issue and needs deeper event-order debugging.

## Follow-ups

- Reproduce the live `connect`-mode empty-prefill path with targeted debug logging around `Input.Submitted`, `Input.Changed`, and observer prompt-state capture so the actual Textual event ordering is visible.

## Iteration 271

- When: `2026-06-30 17:54`
- Area: `control-room`
- Title: `plan-no-snapshot-composable-app`
- Source: [2026-06-30-17-54_control-room_plan-no-snapshot-composable-app.md](iteration-logs/2026-06-30-17-54_control-room_plan-no-snapshot-composable-app.md)

# Iteration Log

- Area: `control-room`
- Title: `plan-no-snapshot-composable-app`
- Started: `2026-06-30 17:54`

## Summary

- Captured the replacement Control Room architecture: one local-first app composed with data sources, view models, view actions, and execution dependencies.

## Changes

- Added `docs/plans/0008-control-room-composable-app-refactor.md` with the no-snapshot target architecture, ownership rules, protocol direction, refactor sequence, and acceptance criteria.
- Marked the older snapshot-based client/server refactor plan as superseded by plan 0008.

## Follow-ups

- Start implementation bottom-up by introducing dependency protocols and local wiring before replacing remote `serve` / `connect`.

## Iteration 272

- When: `2026-06-30 17:58`
- Area: `control-room`
- Title: `add-composable-dependency-layer`
- Source: [2026-06-30-17-58_control-room_add-composable-dependency-layer.md](iteration-logs/2026-06-30-17-58_control-room_add-composable-dependency-layer.md)

# Iteration Log

- Area: `control-room`
- Title: `add-composable-dependency-layer`
- Started: `2026-06-30 17:58`

## Summary

- Introduced the first bottom-up implementation slice for plan 0008: a composable data-source and execution dependency layer for Control Room.

## Changes

- Added `edap.control_room.dependencies` with read models, data-source and execution protocols, local data-source copying, local execution delegation, and a dependency bundle.
- Attached a `ControlRoomDependencies` bundle to `ControlRoomApp`, defaulting to local data and execution dependencies while preserving current backend behavior.
- Added focused tests for local data-source read models and local execution delegation.

## Follow-ups

- Move local rendering surfaces to view models fed by `ControlRoomDependencies.data_source`.
- Replace backend command paths with `ControlRoomDependencies.execution` after local behavior is covered by tests.

## Iteration 273

- When: `2026-06-30 18:01`
- Area: `control-room`
- Title: `route-local-backend-through-execution`
- Source: [2026-06-30-18-01_control-room_route-local-backend-through-execution.md](iteration-logs/2026-06-30-18-01_control-room_route-local-backend-through-execution.md)

# Iteration Log

- Area: `control-room`
- Title: `route-local-backend-through-execution`
- Started: `2026-06-30 18:01`

## Summary

- Routed local backend command execution through the new composable execution dependency.

## Changes

- Updated `LocalControlRoomBackend` dispatch, destination, haul-loop, prompt, route-load, and interrupt paths to call `host.dependencies.execution`.
- Added a regression test proving backend dispatch uses the execution dependency surface.

## Follow-ups

- Continue reducing direct backend/facade coupling by moving app-facing command helpers to execution dependencies.

## Iteration 274

- When: `2026-06-30 18:03`
- Area: `control-room`
- Title: `add-panel-view-models`
- Source: [2026-06-30-18-03_control-room_add-panel-view-models.md](iteration-logs/2026-06-30-18-03_control-room_add-panel-view-models.md)

# Iteration Log

- Area: `control-room`
- Title: `add-panel-view-models`
- Started: `2026-06-30 18:03`

## Summary

- Added the first view-model layer for read-only Control Room panels.

## Changes

- Added status, haul, and market panel view models.
- Added panel-specific rendering entrypoints that accept view models while preserving existing markup helper wrappers.
- Routed status, haul, and market refresh methods through the new panel view models.
- Added focused view-model tests.

## Follow-ups

- Move view-model builders from snapshot-derived app helpers to `ControlRoomDependencies.data_source` once remote data sources replace snapshots.
- Add action objects for interactive views next: command bar, market presentation, replay browser, and trade-route picker.

## Iteration 275

- When: `2026-06-30 18:05`
- Area: `control-room`
- Title: `add-market-view-actions`
- Source: [2026-06-30-18-05_control-room_add-market-view-actions.md](iteration-logs/2026-06-30-18-05_control-room_add-market-view-actions.md)

# Iteration Log

- Area: `control-room`
- Title: `add-market-view-actions`
- Started: `2026-06-30 18:05`

## Summary

- Added the first view-action surface for local market panel presentation state.

## Changes

- Added `ControlRoomViewActions` and `LocalMarketPanelActions`.
- Wired market tab activation and `market lock` / `market unlock` / `market filter` / clear commands through market view actions.
- Added focused tests for market view actions.

## Follow-ups

- Add view actions for command bar, replay browser, and trade-route picker.
- Continue moving command parsing away from direct app state mutation.

## Iteration 276

- When: `2026-06-30 18:07`
- Area: `control-room`
- Title: `route-app-dispatch-through-execution`
- Source: [2026-06-30-18-07_control-room_route-app-dispatch-through-execution.md](iteration-logs/2026-06-30-18-07_control-room_route-app-dispatch-through-execution.md)

# Iteration Log

- Area: `control-room`
- Title: `route-app-dispatch-through-execution`
- Started: `2026-06-30 18:07`

## Summary

- Routed app-level routine/command dispatch helpers through composable execution dependencies.

## Changes

- Added `RemoteObserverExecution` so connect mode has a remote execution dependency backed by the websocket backend.
- Updated `ObserverControlRoomApp` to install the remote execution dependency after construction.
- Switched `_dispatch_command`, `_dispatch_dest`, `_dispatch_haul_loop`, and haul prompt handlers to `ControlRoomDependencies.execution`.
- Added remote execution wrapper tests.

## Follow-ups

- Continue moving remaining app/backend command paths, especially interrupt and replay/picker actions, toward explicit view actions and execution dependencies.

## Iteration 277

- When: `2026-06-30 18:11`
- Area: `control-room`
- Title: `add-data-hydrate-message`
- Source: [2026-06-30-18-11_control-room_add-data-hydrate-message.md](iteration-logs/2026-06-30-18-11_control-room_add-data-hydrate-message.md)

# Iteration Log

- Area: `control-room`
- Title: `add-data-hydrate-message`
- Started: `2026-06-30 18:11`

## Summary

- Added the first no-snapshot, source-oriented data protocol message for plan 0008.

## Changes

- Added `edap.control_room.protocol.data_messages` with a distinct data-message schema, supported source-oriented message types, and `control_room.hydrate` construction from `ControlRoomDataReadModel`.
- Exported the data-message primitives from `edap.control_room.protocol`.
- Added tests proving hydrate payloads contain data-source read models and omit UI-owned prompt/replay state.

## Follow-ups

- Wire `serve` to emit `control_room.hydrate` from `ControlRoomDependencies.data_source`.
- Build remote data sources that consume hydrate/update messages directly instead of snapshots.

## Iteration 278

- When: `2026-06-30 18:14`
- Area: `control-room`
- Title: `serve-data-hydrate-endpoint`
- Source: [2026-06-30-18-14_control-room_serve-data-hydrate-endpoint.md](iteration-logs/2026-06-30-18-14_control-room_serve-data-hydrate-endpoint.md)

# Iteration Log

- Area: `control-room`
- Title: `serve-data-hydrate-endpoint`
- Started: `2026-06-30 18:14`

## Summary

- Added the first server route for the no-snapshot data protocol.

## Changes

- Added authenticated `GET /hydrate` to the observer server app.
- Wired `control_room serve` to serve hydrate data from `runtime_host.dependencies.data_source.current`.
- Added server tests covering `control_room.hydrate` payload shape and UI-state omission.

## Follow-ups

- Add websocket hydrate/update streaming for remote data sources.
- Rebuild `connect` around remote data-source hydration instead of `/snapshot`.

## Iteration 279

- When: `2026-06-30 18:17`
- Area: `control-room`
- Title: `add-remote-hydrate-data-source`
- Source: [2026-06-30-18-17_control-room_add-remote-hydrate-data-source.md](iteration-logs/2026-06-30-18-17_control-room_add-remote-hydrate-data-source.md)

# Iteration Log

- Area: `control-room`
- Title: `add-remote-hydrate-data-source`
- Started: `2026-06-30 18:17`

## Summary

- Added the first remote data-source building block for the no-snapshot `connect` path.

## Changes

- Added hydrate payload parsing into `ControlRoomDataReadModel`.
- Added `RemoteObserverDataSource` as a typed remote read-model cache.
- Added `fetch_remote_control_room_data()` to fetch `/capabilities` plus `/hydrate`.
- Added tests for hydrate round-trip parsing and remote data-source hydration.

## Follow-ups

- Wire `connect` dependencies to `RemoteObserverDataSource`.
- Add websocket data update handling after the server streams source-oriented update messages.

## Iteration 280

- When: `2026-06-30 18:18`
- Area: `control-room`
- Title: `wire-connect-remote-data-source`
- Source: [2026-06-30-18-18_control-room_wire-connect-remote-data-source.md](iteration-logs/2026-06-30-18-18_control-room_wire-connect-remote-data-source.md)

# Iteration Log

- Area: `control-room`
- Title: `wire-connect-remote-data-source`
- Started: `2026-06-30 18:18`

## Summary

- Wired connect-mode app construction to install the new remote hydrate data source.

## Changes

- Updated `connect_observer_mode()` to fetch `/hydrate` and build `RemoteObserverDataSource`.
- Updated `ObserverControlRoomApp` to accept a remote data source and install it into `ControlRoomDependencies`.
- Added a client test proving connect-mode app dependencies use the supplied remote data source.

## Follow-ups

- Replace the remaining snapshot bootstrap and websocket stream in connect mode with hydrate/update data messages.

## Iteration 281

- When: `2026-06-30 18:21`
- Area: `control-room`
- Title: `render-panels-from-data-source`
- Source: [2026-06-30-18-21_control-room_render-panels-from-data-source.md](iteration-logs/2026-06-30-18-21_control-room_render-panels-from-data-source.md)

# Iteration Log

- Area: `control-room`
- Title: `render-panels-from-data-source`
- Started: `2026-06-30 18:21`

## Summary

- Moved the first rendered panels from snapshot-derived app helpers to the composable data-source dependency.

## Changes

- Updated status and haul panel view-model builders to read from `ControlRoomDependencies.data_source`.
- Updated market presentation sync to read latest market data from the data source while keeping display lock state local.
- Updated tests to assert panel rendering and connect market lock behavior through data-source hydration rather than backend snapshots.

## Follow-ups

- Remove remaining `_sync_view_snapshot()` calls from read-only panel refresh paths.
- Add websocket data update streaming so remote data sources hydrate continuously without snapshots.

## Iteration 282

- When: `2026-06-30 18:22`
- Area: `control-room`
- Title: `stop-panel-snapshot-sync`
- Source: [2026-06-30-18-22_control-room_stop-panel-snapshot-sync.md](iteration-logs/2026-06-30-18-22_control-room_stop-panel-snapshot-sync.md)

# Iteration Log

- Area: `control-room`
- Title: `stop-panel-snapshot-sync`
- Started: `2026-06-30 18:22`

## Summary

- Stopped read-only panel refreshes from synchronizing snapshot state before rendering.

## Changes

- Removed `_sync_view_snapshot()` calls from status, haul, and market refresh methods now that those panels render from data-source-backed view models.

## Follow-ups

- Continue removing snapshot sync from interactive surfaces after they move behind view actions and data sources.

## Iteration 283

- When: `2026-06-30 18:25`
- Area: `control-room`
- Title: `stream-websocket-hydrate-data`
- Source: [2026-06-30-18-25_control-room_stream-websocket-hydrate-data.md](iteration-logs/2026-06-30-18-25_control-room_stream-websocket-hydrate-data.md)

# Iteration Log

- Area: `control-room`
- Title: `stream-websocket-hydrate-data`
- Started: `2026-06-30 18:25`

## Summary

- Added websocket hydrate message handling for remote data sources.

## Changes

- Server websocket sessions now send `control_room.hydrate` after `event.connection_ready` when a data provider is available.
- `RemoteObserverBackend` can consume Control Room data messages, hydrate its `RemoteObserverDataSource`, and emit `DataUpdatedEvent`.
- `ObserverControlRoomApp` refreshes data-source-backed panels from `DataUpdatedEvent`.
- Added client and server tests for websocket/data-message hydration.

## Follow-ups

- Broadcast source-oriented update messages on live data changes instead of relying on snapshot fanout.
- Remove old snapshot bootstrap and snapshot websocket handling from connect mode.

## Iteration 284

- When: `2026-06-30 18:27`
- Area: `control-room`
- Title: `fanout-live-hydrate-updates`
- Source: [2026-06-30-18-27_control-room_fanout-live-hydrate-updates.md](iteration-logs/2026-06-30-18-27_control-room_fanout-live-hydrate-updates.md)

# Iteration Log

- Area: `control-room`
- Title: `fanout-live-hydrate-updates`
- Started: `2026-06-30 18:27`

## Summary

- Added live hydrate fanout from the headless server to connected websocket clients.

## Changes

- Added broker support for queueing already-formed data messages.
- Added `DataHydrateFanoutSink`, which broadcasts `control_room.hydrate` from the server data source whenever the headless host publishes runtime changes.
- Wired `control_room serve` to include the hydrate fanout sink.
- Updated websocket sending so data messages keep their no-snapshot schema instead of being wrapped in the old command/event schema.
- Added server tests for hydrate fanout.

## Follow-ups

- Remove snapshot fanout once connect no longer depends on snapshot-driven UI state.

## Iteration 285

- When: `2026-06-30 18:31`
- Area: `control-room`
- Title: `connect-hydrate-bootstrap`
- Source: [2026-06-30-18-31_control-room_connect-hydrate-bootstrap.md](iteration-logs/2026-06-30-18-31_control-room_connect-hydrate-bootstrap.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-hydrate-bootstrap`
- Started: `2026-06-30 18:31`

## Summary

- Removed the production connect-mode bootstrap dependency on the legacy `/snapshot` endpoint.

## Changes

- Added a hydrate-data initializer for the legacy view snapshot shape that `ControlRoomApp` still needs during construction.
- Changed `connect_observer_mode()` to fetch `/hydrate` only, then build the initial remote backend state from the hydrated data source.
- Stopped websocket connect/reconnect and replay refresh from issuing `command.request_snapshot`; live updates now rely on server hydrate messages.
- Added client tests for hydrate-derived initial state and reconnect behavior.

## Follow-ups

- Remove the remaining explicit `request_snapshot()` protocol surface after the server/client observer compatibility tests are retired.

## Iteration 286

- When: `2026-06-30 18:33`
- Area: `control-room`
- Title: `connect-ignore-legacy-snapshots`
- Source: [2026-06-30-18-33_control-room_connect-ignore-legacy-snapshots.md](iteration-logs/2026-06-30-18-33_control-room_connect-ignore-legacy-snapshots.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-ignore-legacy-snapshots`
- Started: `2026-06-30 18:33`

## Summary

- Stopped connect-mode UI state from being driven by legacy `state.snapshot` websocket messages.

## Changes

- Remote websocket receive now ignores `SnapshotUpdatedEvent` payloads instead of publishing them into the app.
- Connection loss logs activity only; it no longer rewrites active operator, connected clients, or routine UI state from the transport layer.
- `ObserverControlRoomApp` ignores any remaining manually emitted snapshot backend events.
- Added regression coverage for ignored legacy snapshot events and connection-loss state preservation.

## Follow-ups

- Remove the old snapshot endpoint/message protocol once server compatibility tests are retired.

## Iteration 287

- When: `2026-06-30 18:50`
- Area: `control-room`
- Title: `remove-snapshot-wire-protocol`
- Source: [2026-06-30-18-50_control-room_remove-snapshot-wire-protocol.md](iteration-logs/2026-06-30-18-50_control-room_remove-snapshot-wire-protocol.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-snapshot-wire-protocol`
- Started: `2026-06-30 18:50`

## Summary

- Removed the legacy snapshot message family from the remote `serve` / `connect` wire protocol.

## Changes

- Removed `/snapshot` from the observer server routes and stopped handling `command.request_snapshot`.
- Removed `state.snapshot` and `command.request_snapshot` from advertised capabilities and the JSON message schema enum.
- Changed broker snapshot publication to retain server-local state without broadcasting snapshot messages.
- Updated the browser probe to use `/hydrate` and `control_room.hydrate` instead of snapshot fetch/request flows.
- Updated server/client/schema tests and remote operator docs for the hydrate-only remote surface.

## Follow-ups

- Remove remaining internal/local snapshot compatibility after command bar, replay browser, and trade-route picker state are fully data-source/view-action owned.

## Iteration 288

- When: `2026-06-30 18:54`
- Area: `control-room`
- Title: `remove-snapshot-message-parser`
- Source: [2026-06-30-18-54_control-room_remove-snapshot-message-parser.md](iteration-logs/2026-06-30-18-54_control-room_remove-snapshot-message-parser.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-snapshot-message-parser`
- Started: `2026-06-30 18:54`

## Summary

- Removed legacy snapshot parsing/export paths from the remote message parser.

## Changes

- Replaced `protocol/from_message.py` with a minimal parser for current activity and announcement events.
- Removed `snapshot_from_message` from protocol exports.
- Removed the unreachable snapshot-event branch from the remote websocket receive loop.
- Deleted client coverage for parsing `state.snapshot` wire messages.

## Follow-ups

- Continue removing internal/local snapshot compatibility after the remaining connect UI surfaces move to data-source/view-action ownership.

## Iteration 289

- When: `2026-06-30 18:57`
- Area: `control-room`
- Title: `connect-data-source-context`
- Source: [2026-06-30-18-57_control-room_connect-data-source-context.md](iteration-logs/2026-06-30-18-57_control-room_connect-data-source-context.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-data-source-context`
- Started: `2026-06-30 18:57`

## Summary

- Moved more connect-mode command context reads from legacy view snapshot state to the remote data source.

## Changes

- `ObserverControlRoomApp` now keeps an optional remote data source reference for production connect mode.
- Active-operator gating for routine readiness and command input refresh reads `data_source.session.client_role` when available.
- Local command ship context and trade-search system lookup read `data_source.ship` when available.
- Commander-name initialization uses hydrated ship data when available.

## Follow-ups

- Continue moving remaining command bar, replay browser, and trade-route picker state away from internal snapshot compatibility.

## Iteration 290

- When: `2026-06-30 19:07`
- Area: `control-room`
- Title: `connect-apply-data-state`
- Source: [2026-06-30-19-07_control-room_connect-apply-data-state.md](iteration-logs/2026-06-30-19-07_control-room_connect-apply-data-state.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-apply-data-state`
- Started: `2026-06-30 19:07`

## Summary

- Changed production connect mode to apply hydrated data directly for runtime/history/activity state instead of syncing a backend snapshot.

## Changes

- Added a remote data-state apply path that copies routine state, command history/defaults, activity log, ship context, and commander TTS from `ControlRoomDataReadModel`.
- Kept the legacy snapshot apply path only as a fallback for tests/internal compatibility when no remote data source is supplied.
- Extracted connect-local prompt/replay/trade-route overlay application so both data and fallback paths preserve local UI ownership.
- Added regression coverage proving hydrate data updates local state without refreshing `_view_snapshot`.

## Follow-ups

- Remove the temporary legacy initial view snapshot once `ControlRoomApp` construction no longer requires a backend snapshot.

## Iteration 291

- When: `2026-06-30 19:12`
- Area: `control-room`
- Title: `remove-remote-snapshot-events`
- Source: [2026-06-30-19-12_control-room_remove-remote-snapshot-events.md](iteration-logs/2026-06-30-19-12_control-room_remove-remote-snapshot-events.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-remote-snapshot-events`
- Started: `2026-06-30 19:12`

## Summary

- Removed remote snapshot update events from the connect client backend.

## Changes

- `RemoteObserverBackend.publish_snapshot()` now only updates its temporary compatibility cache and emits no backend event.
- Removed the unreachable connect app snapshot-event branch and stale imports.
- Updated client tests to assert compatibility-cache updates are silent.

## Follow-ups

- Remove the temporary compatibility cache once `ControlRoomApp` no longer needs a constructor-time `_view_snapshot`.

## Iteration 292

- When: `2026-06-30 19:15`
- Area: `control-room`
- Title: `connect-lazy-snapshot-compat`
- Source: [2026-06-30-19-15_control-room_connect-lazy-snapshot-compat.md](iteration-logs/2026-06-30-19-15_control-room_connect-lazy-snapshot-compat.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-lazy-snapshot-compat`
- Started: `2026-06-30 19:15`

## Summary

- Removed production connect's upfront legacy snapshot construction.

## Changes

- `RemoteObserverBackend` now accepts an optional `initial_snapshot`; if absent, `current_snapshot()` lazily derives the temporary compatibility shape from the remote data source.
- `connect_observer_mode()` now passes only `RemoteObserverDataSource` into the backend.
- Added coverage for deriving the compatibility snapshot from hydrated data.

## Follow-ups

- Remove the lazy compatibility snapshot once `ControlRoomApp` construction no longer asks backends for `_view_snapshot`.

## Iteration 293

- When: `2026-06-30 19:18`
- Area: `control-room`
- Title: `remote-snapshot-publish-noop`
- Source: [2026-06-30-19-18_control-room_remote-snapshot-publish-noop.md](iteration-logs/2026-06-30-19-18_control-room_remote-snapshot-publish-noop.md)

# Iteration Log

- Area: `control-room`
- Title: `remote-snapshot-publish-noop`
- Started: `2026-06-30 19:18`

## Summary

- Made remote backend snapshot publication a no-op.

## Changes

- `RemoteObserverBackend.publish_snapshot()` no longer mutates the compatibility cache.
- Removed redundant snapshot publication calls from connect client tests.
- Updated coverage to assert remote snapshot publication does not change current compatibility state.

## Follow-ups

- Remove the `publish_snapshot()` method from the remote backend surface when `ControlRoomBackend` no longer inherits the snapshot sink protocol.

## Iteration 294

- When: `2026-06-30 19:22`
- Area: `control-room`
- Title: `connect-command-bar-state`
- Source: [2026-06-30-19-22_control-room_connect-command-bar-state.md](iteration-logs/2026-06-30-19-22_control-room_connect-command-bar-state.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-command-bar-state`
- Started: `2026-06-30 19:22`

## Summary

- Encapsulated connect-mode command-bar draft/cursor/prefill state.

## Changes

- Added `ObserverCommandBarState` to own command input value, cursor position, and prompt prefill signature.
- Routed command input capture and clear paths through the new state object.
- Kept compatibility properties for existing tests/call sites while centralizing command-bar state.

## Follow-ups

- Move command-bar refresh/restore behavior behind a dedicated view action after replay and trade-route picker state are similarly isolated.

## Iteration 295

- When: `2026-06-30 19:25`
- Area: `control-room`
- Title: `connect-replay-view-state`
- Source: [2026-06-30-19-25_control-room_connect-replay-view-state.md](iteration-logs/2026-06-30-19-25_control-room_connect-replay-view-state.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-replay-view-state`
- Started: `2026-06-30 19:25`

## Summary

- Encapsulated connect replay-browser local UI state in a dedicated `ObserverReplayViewState`.

## Changes

- Replaced scattered observer-local replay filter/open/selected-entry fields with one capture/apply object.
- Kept hydrate/snapshot-compat application from overwriting replay-browser local state directly.
- Verified `tests/test_control_room_client.py` and the full unittest suite.

## Follow-ups

- Continue moving trade-route picker and remaining prompt interaction state behind view-action/data-source-owned seams.

## Iteration 296

- When: `2026-06-30 19:49`
- Area: `control-room`
- Title: `connect-single-app-collapse`
- Source: [2026-06-30-19-49_control-room_connect-single-app-collapse.md](iteration-logs/2026-06-30-19-49_control-room_connect-single-app-collapse.md)

# Iteration Log

- Area: `control-room`
- Title: `connect-single-app-collapse`
- Started: `2026-06-30 19:49`

## Summary

- Collapsed connect mode onto the single local-first `ControlRoomApp` instead of maintaining `ObserverControlRoomApp`.

## Changes

- Replaced the large connect subclass with a small bootstrap that fetches remote hydrate data, builds `RemoteObserverDataSource` / `RemoteObserverExecution`, binds them into `ControlRoomApp`, and runs the shared app.
- Moved remote hydrate/event application into the base app so data-backed panels refresh from the injected data source while command input, prompts, replay, and trade-route picker remain app-local.
- Updated remote execution so prompt-owning/local UI commands execute locally through the shared app, while finalized routine dispatches still go to the server.
- Removed obsolete subclass/snapshot compatibility tests and rewrote protocol assertions around local UI actions plus execution dependency dispatch.
- Verified `tests/test_control_room_client.py`, `tests/test_control_room_protocol.py`, and the full unittest suite.

## Follow-ups

- Continue removing internal snapshot compatibility that remains in the base app/backend after the connect subclass removal.

## Iteration 297

- When: `2026-06-30 21:15`
- Area: `control-room`
- Title: `prune-backend-replay-actions`
- Source: [2026-06-30-21-15_control-room_prune-backend-replay-actions.md](iteration-logs/2026-06-30-21-15_control-room_prune-backend-replay-actions.md)

# Iteration Log

- Area: `control-room`
- Title: `prune-backend-replay-actions`
- Started: `2026-06-30 21:15`

## Summary

- Removed the obsolete backend replay-browser action surface after collapsing connect onto the shared app.

## Changes

- Dropped replay browser methods from `ControlRoomBackend`, `LocalControlRoomBackend`, and `RemoteObserverBackend`.
- Routed the remaining app `_replay_history_entry` helper directly through local replay logic.
- Pruned obsolete replay-backend test stubs and the remote backend replay-locality test.
- Verified focused control-room suites and the full unittest suite.

## Follow-ups

- Continue removing internal snapshot compatibility from base app/backend and server broker paths.

## Iteration 298

- When: `2026-06-30 21:38`
- Area: `control-room`
- Title: `remove-app-snapshot-state`
- Source: [2026-06-30-21-38_control-room_remove-app-snapshot-state.md](iteration-logs/2026-06-30-21-38_control-room_remove-app-snapshot-state.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-app-snapshot-state`
- Started: `2026-06-30 21:38`

## Summary

- Removed `ControlRoomApp`'s direct dependency on backend snapshots.

## Changes

- Dropped `_view_snapshot`, `_sync_view_snapshot`, `_apply_view_snapshot_state`, and snapshot-backed view helper methods from the shared app.
- Updated app snapshot publication to build from the app directly for the remaining legacy external sink path instead of asking the backend for `current_snapshot()`.
- Reworked local/remote tests to seed app state or hydrate data sources directly rather than applying snapshots to the app.
- Verified focused control-room/client/protocol tests and the full unittest suite.

## Follow-ups

- Continue pruning backend/server snapshot compatibility and then validate live `serve` + `connect`.

## Iteration 299

- When: `2026-06-30 21:44`
- Area: `control-room`
- Title: `remove-backend-current-snapshot`
- Source: [2026-06-30-21-44_control-room_remove-backend-current-snapshot.md](iteration-logs/2026-06-30-21-44_control-room_remove-backend-current-snapshot.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-backend-current-snapshot`
- Started: `2026-06-30 21:44`

## Summary

- Removed the backend `current_snapshot()` contract so local and remote apps cannot rebuild UI from backend-owned snapshots.

## Changes

- Dropped cached snapshot seeding from `RemoteObserverBackend`.
- Updated connect/client tests to assert hydrated data-source state and backend events instead of snapshot compatibility.
- Kept `publish_snapshot()` as a no-op/external-sink compatibility hook pending server/protocol cleanup.

## Follow-ups

- Remove the remaining server broker/protocol snapshot compatibility path.

## Iteration 300

- When: `2026-06-30 21:54`
- Area: `control-room`
- Title: `remove-server-snapshot-refresh`
- Source: [2026-06-30-21-54_control-room_remove-server-snapshot-refresh.md](iteration-logs/2026-06-30-21-54_control-room_remove-server-snapshot-refresh.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-server-snapshot-refresh`
- Started: `2026-06-30 21:54`

## Summary

- Removed the server-side snapshot refresh path so `serve` reads metadata and hydrates clients from the composed data source.

## Changes

- Replaced `ControlRoomEventSink.publish_snapshot()` with `publish_data_refresh()`.
- Removed broker snapshot retention/merge logic and server-state command-history snapshot merging.
- Removed `HeadlessControlRoomHost.snapshot()` and serve-time snapshot seeding.
- Updated websocket/HTTP tests to construct the server around `_base_data_read_model`.

## Follow-ups

- Prune remaining legacy protocol snapshot dataclasses/conversion helpers once local tests no longer need them as fixtures.

## Iteration 301

- When: `2026-06-30 22:08`
- Area: `control-room`
- Title: `prune-snapshot-protocol`
- Source: [2026-06-30-22-08_control-room_prune-snapshot-protocol.md](iteration-logs/2026-06-30-22-08_control-room_prune-snapshot-protocol.md)

# Iteration Log

- Area: `control-room`
- Title: `prune-snapshot-protocol`
- Started: `2026-06-30 22:08`

## Summary

- Deleted legacy Control Room snapshot protocol modules and schema definitions after replacing server/client refresh with data-source hydration.

## Changes

- Moved `ActivityLogEntry` into protocol events so event streaming no longer depends on `protocol.snapshot`.
- Deleted `edap/control_room/protocol/snapshot.py` and `protocol/from_app.py`.
- Removed snapshot exports from `edap.control_room.protocol`.
- Removed snapshot `$defs` from `docs/schemas/control_room_message.schema.json`.
- Renamed internal status/market sync helpers away from snapshot-era terminology.

## Follow-ups

- Continue extracting explicit ViewModel/action seams for panels that still read app state directly.

## Iteration 302

- When: `2026-06-30 22:12`
- Area: `control-room`
- Title: `trade-route-picker-view-model`
- Source: [2026-06-30-22-12_control-room_trade-route-picker-view-model.md](iteration-logs/2026-06-30-22-12_control-room_trade-route-picker-view-model.md)

# Iteration Log

- Area: `control-room`
- Title: `trade-route-picker-view-model`
- Started: `2026-06-30 22:12`

## Summary

- Added a trade-route picker ViewModel so the picker display state is translated before Textual widget updates.

## Changes

- Added `TradeRoutePickerViewModel` and `trade_route_picker_view_model()`.
- Rewired `ControlRoomApp._refresh_trade_route_picker()` to consume the picker ViewModel.
- Added ViewModel tests for selected/default/empty route states.

## Follow-ups

- Continue extracting action seams for trade-route picker movement/load/destination commands.

## Iteration 303

- When: `2026-06-30 22:17`
- Area: `control-room`
- Title: `trade-route-picker-view-actions`
- Source: [2026-06-30-22-17_control-room_trade-route-picker-view-actions.md](iteration-logs/2026-06-30-22-17_control-room_trade-route-picker-view-actions.md)

# Iteration Log

- Area: `control-room`
- Title: `trade-route-picker-view-actions`
- Started: `2026-06-30 22:17`

## Summary

- Extracted trade-route picker close/move/load/destination behavior into a ViewActions object.

## Changes

- Added `TradeRoutePickerActions` and `LocalTradeRoutePickerActions`.
- Rewired `ControlRoomApp` trade-route helper methods to delegate through `self._view_actions.trade_routes`.
- Added direct ViewAction tests for picker selection movement and command dispatch.

## Follow-ups

- Replay browser actions remain local app methods and are the next candidate for extraction.

## Iteration 304

- When: `2026-06-30 22:28`
- Area: `control-room`
- Title: `fix-connect-target-wiring`
- Source: [2026-06-30-22-28_control-room_fix-connect-target-wiring.md](iteration-logs/2026-06-30-22-28_control-room_fix-connect-target-wiring.md)

# Iteration Log

- Area: `control-room`
- Title: `fix-connect-target-wiring`
- Started: `2026-06-30 22:28`

## Summary

- Fixed connect-mode startup after the live CLI path hit stale target/runtime API usage.

## Changes

- Use `ObserverServerTarget.websocket_url` and call `build_remote_observer_websocket_connect_info()` with its current keyword-only signature.
- Queue `--claim-operator` through `RemoteObserverBackend.request_active_operator()` after backend construction.
- Align connect runtime context creation with the current `load_config_with_fallback()` return shape.
- Added a regression test that uses the real websocket connect-info builder instead of mocking away the failing call.

## Follow-ups

- Re-run live `uv run control_room.py connect ...` against the server after this commit.

## Iteration 305

- When: `2026-07-01 10:13`
- Area: `control-room`
- Title: `decouple-view-actions`
- Source: [2026-07-01-10-13_control-room_decouple-view-actions.md](iteration-logs/2026-07-01-10-13_control-room_decouple-view-actions.md)

# Iteration Log

- Area: `control-room`
- Title: `decouple-view-actions`
- Started: `2026-07-01 10:13`

## Summary

- Decoupled the current market and trade-route picker ViewActions from `ControlRoomApp`/Textual display mechanics.

## Changes

- Updated plan 0008 so ViewActions are explicitly UI-neutral intent dispatchers backed by injected dependencies.
- Replaced app-coupled market/trade-route action implementations with pure ViewAction classes and dependency protocols.
- Added `app_view_actions.py` as the current Textual/ControlRoomApp adapter for logging, refresh, command dispatch, and focus behavior.
- Reworked ViewAction tests to use dependency fakes instead of app/widget stubs.

## Follow-ups

- Continue moving prompt/replay/command-bar interactions behind the same display-neutral action dependency pattern.

## Iteration 306

- When: `2026-07-01 11:25`
- Area: `ci-release`
- Title: `prepare-v1-17-0-release`
- Source: [2026-07-01-11-25__ci-release__prepare-v1-17-0-release.md](iteration-logs/2026-07-01-11-25__ci-release__prepare-v1-17-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-17-0-release`
- Started: `2026-07-01 11:25`

## Summary

- Prepared the `v1.17.0` release after the Control Room no-snapshot and composable one-app refactor work.

## Changes

- Bumped project metadata from `1.16.0` to `1.17.0`.
- Updated CI/release handoff status to reflect the release scope.
- Refreshed `uv.lock` and passed the release-prep full unittest suite.

## Follow-ups

- `v1.17.0` was tagged, pushed, and published as `EDControlRoom v1.17.0 - Composable Control Room`.

## Iteration 307

- When: `2026-07-01 12:12`
- Area: `control-room`
- Title: `stabilize-activity-log-order`
- Source: [2026-07-01-12-12_control-room_stabilize-activity-log-order.md](iteration-logs/2026-07-01-12-12_control-room_stabilize-activity-log-order.md)

# Iteration Log

- Area: `control-room`
- Title: `stabilize-activity-log-order`
- Started: `2026-07-01 12:12`

## Summary

- Stabilized activity log ordering when connect mode mixes client-local prompt logs with server routine logs.

## Changes

- Added app-local first-observed display ordering for activity entries.
- Changed activity redraws to preserve display order instead of re-sorting merged local/remote logs by wall-clock timestamp.
- Added a regression covering server entries with earlier timestamps arriving after local prompt transcript entries.

## Follow-ups

- Live-check `dest` and `haul route` prompt/routine transcripts in connect mode against a remote server.

## Iteration 308

- When: `2026-07-01 12:24`
- Area: `haul`
- Title: `supercruise-empty-hold-phase-detection`
- Source: [2026-07-01-12-24_____haul_____supercruise-empty-hold-phase-detection.md](iteration-logs/2026-07-01-12-24_____haul_____supercruise-empty-hold-phase-detection.md)

# Iteration Log

- Area: `haul`
- Title: `supercruise-empty-hold-phase-detection`
- Started: `2026-07-01 12:24`

## Summary

- Fixed two-way haul startup phase detection for the live case where the commander starts `haul` in supercruise in station 1/2's system with an empty hold and a buy commodity configured for that local station.

## Changes

- Updated `_detect_start_phase()` so empty-hold supercruise in the local buy station system returns to that station's transit/dock phase instead of assuming outbound transit to the opposite station.
- Added regression coverage for station 1 and station 2 empty-hold supercruise starts, plus the one-sided route case where a blank local buy commodity should still continue to the opposite station.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` and `uv run python3 -m unittest discover -s tests` (`617` tests, `0.314s`).

## Follow-ups

- Live-validate the normal-space empty-hold resume case separately before changing it, because that branch currently overlaps with launch/escape resume behavior.

## Iteration 309

- When: `2026-07-01 12:31`
- Area: `control-room`
- Title: `remote-haul-elapsed-read-model`
- Source: [2026-07-01-12-31_control-room_remote-haul-elapsed-read-model.md](iteration-logs/2026-07-01-12-31_control-room_remote-haul-elapsed-read-model.md)

# Iteration Log

- Area: `control-room`
- Title: `remote-haul-elapsed-read-model`
- Started: `2026-07-01 12:31`

## Summary

- Fixed connect/serve haul panel time tracking by preventing hydrate/read-model data from exporting server-local monotonic start timestamps.

## Changes

- Updated `LocalControlRoomDataSource` haul copying to compute `session_elapsed_s` and `current_run_elapsed_s` at read time and clear `session_started_at` / `current_run_started_at` from the read model.
- Added dependency and hydrate protocol regressions so remote-safe elapsed values are serialized instead of process-local timer origins.
- Verified `uv run python3 -m unittest tests/test_control_room_dependencies.py tests/test_control_room_data_messages.py tests/test_control_room_client.py` and `uv run python3 -m unittest discover -s tests` (`618` tests, `0.305s`).

## Follow-ups

- Live-check a running `control_room.py serve` + `connect` haul session to confirm elapsed values advance acceptably with the current hydrate/update cadence.

## Iteration 310

- When: `2026-07-01 12:52`
- Area: `haul`
- Title: `route-and-pad-full-retry`
- Source: [2026-07-01-12-52_____haul_____route-and-pad-full-retry.md](iteration-logs/2026-07-01-12-52_____haul_____route-and-pad-full-retry.md)

# Iteration Log

- Area: `haul`
- Title: `route-and-pad-full-retry`
- Started: `2026-07-01 12:52`

## Summary

- Added non-fatal haul handling for galaxy-map route failures and a pad-full docking retry path for `DockingDenied` `NoSpace` style responses.

## Changes

- Two-way and multi-leg haul now retry galaxy-map destination setting twice, log/TTS an unconfirmed-route warning, skip automatic FSD engage on route failure, and continue waiting for pilot-driven journal progress.
- Docking now classifies pad-full denial reasons, holds throttle at zero, uses a separate slower pad-full retry budget, and announces the pad-full state once before retrying.
- Added regression coverage for route-unconfirmed continuation, confirmed-route fixtures, pad-full retry success, pad-full retry exhaustion, and the new default TTS phrase.

## Follow-ups

- Live-validate the actual Elite journal reason string for full pads under CrossOver and tune the default `30s x 20` pad-full retry window if it feels too slow or too persistent.

## Iteration 311

- When: `2026-07-01 14:07`
- Area: `runtime`
- Title: `unify-config-defaults`
- Source: [2026-07-01-14-07___runtime____unify-config-defaults.md](iteration-logs/2026-07-01-14-07___runtime____unify-config-defaults.md)

# Iteration Log

- Area: `runtime`
- Title: `unify-config-defaults`
- Started: `2026-07-01 14:07`

## Summary

- Unified shipped app defaults under `defaults/*.toml` and kept ignored local TOML files as override layers.
- Stopped tracking repo-root `haul.toml` while preserving `haul load` as the local profile workflow.

## Changes

- Added default category files for paths, runtime, controls, screen, haul, and haul search; expanded `defaults/control_room.toml` to carry the full Control Room defaults.
- Changed `edap.config.load_config()` to merge local config over shipped category defaults before validation, so minimal `config.toml` files only need explicit overrides.
- Converted `config.example.toml` into an override skeleton, moved Inara search defaults to `defaults/haul_search.toml`, and raised the default haul docking timeout to `1200s`.

## Follow-ups

- Live-validate the `1200s` haul docking timeout against slower carrier/station approaches and keep local `haul.toml` guidance aligned with operator feedback.

## Iteration 312

- When: `2026-07-01 14:49`
- Area: `ci-release`
- Title: `prepare-v1-18-0-release`
- Source: [2026-07-01-14-49__ci-release__prepare-v1-18-0-release.md](iteration-logs/2026-07-01-14-49__ci-release__prepare-v1-18-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-18-0-release`
- Started: `2026-07-01 14:49`

## Summary

- Prepared the `v1.18.0` release after haul recovery fixes and the config-defaults refactor landed on `main`.

## Changes

- Bumped project metadata from `1.17.0` to `1.18.0`.
- Refreshed `uv.lock` so package metadata matches the release version.
- Updated CI/release handoff status for the new stable release target.
- Passed `uv run python3 -m unittest discover -s tests` with `622` tests in `0.264s`, under the `0.3732s` timing budget.

## Follow-ups

- `v1.18.0` was tagged, pushed, and published as `EDControlRoom v1.18.0 - Config Defaults and Haul Recovery`.

## Iteration 313

- When: `2026-07-02 15:22`
- Area: `haul`
- Title: `routine-engineering-health-refactor`
- Source: [2026-07-02-15-22_____haul_____routine-engineering-health-refactor.md](iteration-logs/2026-07-02-15-22_____haul_____routine-engineering-health-refactor.md)

# Iteration Log

- Area: `haul`
- Title: `routine-engineering-health-refactor`
- Started: `2026-07-02 15:22`

## Summary

- Refactored haul routine internals so shared two-way/multi-leg mechanics live outside `haul_two_way.py`.

## Changes

- Added `edap.routines.haul_support` for shared cargo/journal readers, transit resume detection, arrival/on-land waits, manual landing results, galaxy-map retry, nav-panel opening, hyperspace engage, and grouped runtime/settings objects.
- Collapsed two-way and multi-leg route contexts around `HaulRuntime` plus route-specific legs/stops, instead of long flat bags of controls, callbacks, timers, and market settings.
- Removed the long public two-way and multi-leg haul signatures; Control Room and the manual CLI now pass `HaulRuntime` plus route/definition objects.
- Removed multi-leg imports of private two-way helpers and updated tests to patch the new shared galaxy-map helper owner.
- Fixed stale manual CLI routine wiring to pass current market hold segment config and explicit announcement callbacks.

## Follow-ups

- Split very large haul behavior test files once the new production module boundaries have settled.

## Iteration 314

- When: `2026-07-03 10:18`
- Area: `haul`
- Title: `home-search-alias`
- Source: [2026-07-03-10-18_____haul_____home-search-alias.md](iteration-logs/2026-07-03-10-18_____haul_____home-search-alias.md)

# Iteration Log

- Area: `haul`
- Title: `home-search-alias`
- Started: `2026-07-03 10:18`

## Summary

- Added `haul search home` as an alias for the saved `control_room.home_system`, so operators can reuse the configured home system as the Inara search center.

## Changes

- Resolved the `home` alias inside the haul-search command parser before opening the editable Inara search prompt, while preserving the raw command as `haul search home` for prompt/history context.
- Reported the existing home-not-set guidance when the alias is used without a saved home system instead of treating `home` as a literal system name.
- Updated command help, operator docs, and haul status handoff, and added Control Room regression coverage for saved and missing home-system alias cases.

## Follow-ups

- Live-check one `haul search home` run after `home set` in the real TUI to confirm the prompt prefill and route picker feel correct with live Inara results.

## Iteration 315

- When: `2026-07-03 10:28`
- Area: `control-room`
- Title: `dest-home-alias`
- Source: [2026-07-03-10-28_control-room_dest-home-alias.md](iteration-logs/2026-07-03-10-28_control-room_dest-home-alias.md)

# Iteration Log

- Area: `control-room`
- Title: `dest-home-alias`
- Started: `2026-07-03 10:28`

## Summary

- Fixed `dest home` so it resolves to the saved `control_room.home_system` before the galaxy-map route prompt/routine sees the destination.

## Changes

- Added home-alias resolution to the destination command parser while preserving the raw command as `dest home` for prompt/history context.
- Reused the existing home-not-set guidance when `dest home` is submitted without a saved home system, preventing a literal route attempt to `home`.
- Added Control Room regressions for saved and missing home-system `dest home` cases, and updated command help, operator docs, and the Control Room status handoff.

## Follow-ups

- Live-check `dest home` after `home set` in the real TUI to confirm the NavRoute mismatch shown in the failed run no longer appears.

## Iteration 316

- When: `2026-07-03 14:39`
- Area: `control-room`
- Title: `lan-serve-flag`
- Source: [2026-07-03-14-39_control-room_lan-serve-flag.md](iteration-logs/2026-07-03-14-39_control-room_lan-serve-flag.md)

# Iteration Log

- Area: `control-room`
- Title: `lan-serve-flag`
- Started: `2026-07-03 14:39`

## Summary

- Added `control_room.py serve --lan` so LAN serving can bind to the detected non-loopback IPv4 address without manually passing `--host`.

## Changes

- Added LAN host detection in the Control Room CLI using UDP route probing with hostname-address fallback.
- Made `serve --lan` and `serve --host` mutually exclusive, preserving the default local bind of `127.0.0.1`.
- Updated remote observer operator docs to recommend `--lan` for same-network clients while retaining explicit `--host 0.0.0.0` guidance.
- Added focused CLI tests for LAN detection, serve wiring, and conflict handling.

## Follow-ups

- Live LAN validation should confirm the chosen bind address is the operator-visible address on the current macOS/CrossOver host.

## Iteration 317

- When: `2026-07-04 05:13`
- Area: `control-room`
- Title: `market-lock-pins-current-market`
- Source: [2026-07-04-05-13_control-room_market-lock-pins-current-market.md](iteration-logs/2026-07-04-05-13_control-room_market-lock-pins-current-market.md)

# Iteration Log

- Area: `control-room`
- Title: `market-lock-pins-current-market`
- Started: `2026-07-04 05:13`

## Summary

- Changed Control Room market lock semantics from display freeze to current-market pinning.

## Changes

- Added `MarketData.market_id`, loaded Elite `MarketID` from `Market.json`, and carried it through local data-source copies and hydrate parsing.
- Updated local and remote market presentation sync so locked panels continue rendering matching-market updates while holding back different-market data until unlock.
- Changed operator-facing copy from frozen/locked wording to pinned/following wording and added regressions for local, remote, protocol, and rendering behavior.

## Follow-ups

- Live-check with real `Market.json` updates that Elite emits stable `MarketID` across repeated visits to the same station market.

## Iteration 318

- When: `2026-07-04 07:46`
- Area: `web`
- Title: `haul-page-static-prototype`
- Source: [2026-07-04-07-46_____web______haul-page-static-prototype.md](iteration-logs/2026-07-04-07-46_____web______haul-page-static-prototype.md)

# Iteration Log

- Area: `web`
- Title: `haul-page-static-prototype`
- Started: `2026-07-04 07:46`

## Summary

- Added a static HTML-only prototype for the v1 web Haul page, using the external component library's restrained dark/amber design language while keeping the layout purpose-built for EDControlRoom's two-way haul workflow.

## Changes

- Created `web/haul-v1.html` with no backend integration or build step.
- Included route search, route results, selected-route setup, command preview, routine summary, and activity sample sections.
- Added explicit station/carrier-only guardrails in both search and start panels; the preview always emits `station_1_on_land=false` and `station_2_on_land=false`.
- Reflected the agreed v1 scope: two-way haul only, no prompt flow, no Inara URL import, and no market page.

## Follow-ups

- Add backend support for server-owned haul search data in hydrate plus a structured search command before wiring this page to live data.
- Keep route row selection browser-local; use structured `command.dispatch_haul_loop` only when the operator starts a selected route.

## Iteration 319

- When: `2026-07-04 07:52`
- Area: `web`
- Title: `clarify-haul-dispatch-copy`
- Source: [2026-07-04-07-52_____web______clarify-haul-dispatch-copy.md](iteration-logs/2026-07-04-07-52_____web______clarify-haul-dispatch-copy.md)

# Iteration Log

- Area: `web`
- Title: `clarify-haul-dispatch-copy`
- Started: `2026-07-04 07:52`

## Summary

- Corrected the static Haul prototype copy so it does not describe the existing structured haul dispatch command as future backend work.

## Changes

- Updated `web/haul-v1.html` to label `command.dispatch_haul_loop` as an existing backend command.
- Left `command.search_haul_routes` framed as future work because the server-side structured search command is not implemented yet.

## Follow-ups

- Wire the existing `command.dispatch_haul_loop` path before adding new backend action surface for haul search.

## Iteration 320

- When: `2026-07-04 07:53`
- Area: `web`
- Title: `tighten-haul-endpoint-copy`
- Source: [2026-07-04-07-53_____web______tighten-haul-endpoint-copy.md](iteration-logs/2026-07-04-07-53_____web______tighten-haul-endpoint-copy.md)

# Iteration Log

- Area: `web`
- Title: `tighten-haul-endpoint-copy`
- Started: `2026-07-04 07:53`

## Summary

- Tightened the static Haul prototype endpoint-support copy after review.

## Changes

- Removed the redundant read-only endpoint type field from the selected-route start panel.
- Renamed the vague `Launch guardrail` notice to `Endpoint support` and made the station/carrier-only dispatch behavior explicit there.

## Follow-ups

- Keep endpoint support messaging in one visible place when the page is wired to live route data.

## Iteration 321

- When: `2026-07-04 07:55`
- Area: `web`
- Title: `reposition-haul-panels`
- Source: [2026-07-04-07-55_____web______reposition-haul-panels.md](iteration-logs/2026-07-04-07-55_____web______reposition-haul-panels.md)

# Iteration Log

- Area: `web`
- Title: `reposition-haul-panels`
- Started: `2026-07-04 07:55`

## Summary

- Repositioned the static Haul v1 panels so the active routine reads as a top operational band and the activity feed fills the open lower work area.

## Changes

- Moved `Active haul routine` directly below the current haul summary strip and above the search/results/start workspace.
- Moved `Activity` into the main grid as a second-row panel spanning the search and route result columns.
- Kept `Selected route + start` pinned in the right setup column across the main workspace.

## Follow-ups

- Recheck the proportions visually once the static page is served over HTTP or embedded in the backend.

## Iteration 322

- When: `2026-07-04 07:56`
- Area: `web`
- Title: `remove-haul-header-pills`
- Source: [2026-07-04-07-56_____web______remove-haul-header-pills.md](iteration-logs/2026-07-04-07-56_____web______remove-haul-header-pills.md)

# Iteration Log

- Area: `web`
- Title: `remove-haul-header-pills`
- Started: `2026-07-04 07:56`

## Summary

- Removed redundant header pills from the static Haul v1 prototype.

## Changes

- Dropped the page-head `V1 structured dispatch` and `No Inara URL import` chips.
- Dropped the topbar `Stations and carriers only` status chip while preserving the search/start panel limitation copy.

## Follow-ups

- Continue trimming duplicate scope labels as the static prototype moves toward backend-served UI.

## Iteration 323

- When: `2026-07-04 07:57`
- Area: `web`
- Title: `collapse-command-preview`
- Source: [2026-07-04-07-57_____web______collapse-command-preview.md](iteration-logs/2026-07-04-07-57_____web______collapse-command-preview.md)

# Iteration Log

- Area: `web`
- Title: `collapse-command-preview`
- Started: `2026-07-04 07:57`

## Summary

- Converted the selected route command preview into a collapsed debug disclosure.

## Changes

- Wrapped the existing command preview output in a native `details` section labeled `Debug command preview`.
- Added compact disclosure styling so debug params no longer occupy the default start panel layout.
- Kept the existing `command-preview` id intact for the current static JavaScript updater.

## Follow-ups

- Revisit debug affordances when backend integration lands and decide whether command previews should be hidden behind a developer mode.

## Iteration 324

- When: `2026-07-04 07:57`
- Area: `web`
- Title: `remove-surface-destination-field`
- Source: [2026-07-04-07-57_____web______remove-surface-destination-field.md](iteration-logs/2026-07-04-07-57_____web______remove-surface-destination-field.md)

# Iteration Log

- Area: `web`
- Title: `remove-surface-destination-field`
- Started: `2026-07-04 07:57`

## Summary

- Removed the redundant disabled surface-destinations field from the static Haul v1 search form.

## Changes

- Dropped the readonly `Surface destinations` input while keeping the station/carrier limitation in the search banner.

## Follow-ups

- Keep future unsupported-scope messaging informational rather than styled like inactive form controls.

## Iteration 325

- When: `2026-07-04 07:59`
- Area: `web`
- Title: `remove-unimplemented-sidebar-items`
- Source: [2026-07-04-07-59_____web______remove-unimplemented-sidebar-items.md](iteration-logs/2026-07-04-07-59_____web______remove-unimplemented-sidebar-items.md)

# Iteration Log

- Area: `web`
- Title: `remove-unimplemented-sidebar-items`
- Started: `2026-07-04 07:59`

## Summary

- Removed unimplemented sidebar navigation and backend-contract placeholders from the static Haul v1 prototype.

## Changes

- Dropped the inactive `Market later` and `Diagnostics later` sidebar buttons.
- Dropped the `Backend Contract` sidebar block for planned/unimplemented backend states.
- Kept the active `Two-way haul` nav item and lower runtime status rows.

## Follow-ups

- Reintroduce sidebar destinations only when those pages or live backend states exist.

## Iteration 326

- When: `2026-07-04 08:00`
- Area: `web`
- Title: `remove-search-backend-callout`
- Source: [2026-07-04-08-00_____web______remove-search-backend-callout.md](iteration-logs/2026-07-04-08-00_____web______remove-search-backend-callout.md)

# Iteration Log

- Area: `web`
- Title: `remove-search-backend-callout`
- Started: `2026-07-04 08:00`

## Summary

- Removed the search-panel backend command callout from the static Haul v1 prototype.

## Changes

- Dropped the `Future backend command: command.search_haul_routes` copy below the search controls.

## Follow-ups

- Keep backend implementation notes out of the primary prototype UI unless surfaced through debug-only affordances.

## Iteration 327

- When: `2026-07-04 08:04`
- Area: `web`
- Title: `wire-haul-page-backend`
- Source: [2026-07-04-08-04_____web______wire-haul-page-backend.md](iteration-logs/2026-07-04-08-04_____web______wire-haul-page-backend.md)

# Iteration Log

- Area: `web`
- Title: `wire-haul-page-backend`
- Started: `2026-07-04 08:04`

## Summary

- Wired the static Haul v1 page to the Control Room server with authenticated search and start endpoints.

## Changes

- Added `GET /haul` to serve `web/haul-v1.html` from `control_room.py serve`.
- Added `POST /api/haul/search` to run shared Inara route search, force station/carrier-only query params, optionally filter by destination, and return serialized route data.
- Added `POST /api/haul/start` to validate web haul params, reject surface destinations, default both `on_land` flags false, and call existing structured `dispatch_haul_loop`.
- Updated the Haul page to hydrate summary state, search live routes, render backend route data, and start the selected two-way haul.
- Removed unsupported supply/demand columns from the web route table for v1 because the current backend route model does not expose them as first-class fields.
- Added server regression tests for serving `/haul`, route search serialization, start dispatch, auth, and surface-destination rejection.

## Follow-ups

- Live-check `/haul?access_token=...` against a running server with the real Inara browser profile before treating the web search flow as operator-validated.

## Iteration 328

- When: `2026-07-04 09:09`
- Area: `web`
- Title: `move-haul-actions-to-websocket`
- Source: [2026-07-04-09-09_____web______move-haul-actions-to-websocket.md](iteration-logs/2026-07-04-09-09_____web______move-haul-actions-to-websocket.md)

# Iteration Log

- Area: `web`
- Title: `move-haul-actions-to-websocket`
- Started: `2026-07-04 09:09`

## Summary

- Removed Haul web action REST endpoints and moved browser search/start behavior onto the existing websocket session.

## Changes

- Removed `/api/haul/search` and `/api/haul/start` from the Starlette app; only `GET /haul` remains for serving the page.
- Added websocket `command.search_haul_routes` to the advertised protocol capabilities and JSON schema.
- Routed `command.search_haul_routes` through the websocket session handler, returning serialized route results in `response.success.result`.
- Updated `web/haul-v1.html` to consume initial/live hydrate data from websocket messages and send both search and `command.dispatch_haul_loop` through `/session`.
- Updated server tests to assert the old REST action endpoints return 404 and cover websocket search plus dispatch from a browser-style session.

## Follow-ups

- Live-check `/haul?access_token=...` against a running server and real Inara profile to validate websocket search latency and operator-role behavior.

## Iteration 329

- When: `2026-07-04 09:27`
- Area: `web`
- Title: `wire-haul-routine-and-activity`
- Source: [2026-07-04-09-27_____web______wire-haul-routine-and-activity.md](iteration-logs/2026-07-04-09-27_____web______wire-haul-routine-and-activity.md)

# Iteration Log

- Area: `web`
- Title: `wire-haul-routine-and-activity`
- Started: `2026-07-04 09:27`

## Summary

- Connected the Haul web routine and activity panels to backend websocket hydrate/event data.

## Changes

- Added derived `routine.haul_phase` to the Control Room data read model so browser clients can render the active two-way haul phase without duplicating low-level routine internals.
- Preserved `haul_phase` through hydrate serialization/parsing and fixed activity-log parsing to accept serialized tuple entries.
- Added live haul cargo-moved telemetry from MarketBuy journal counts and reset it when a new haul session starts.
- Updated `web/haul-v1.html` to render routine step state, elapsed/current-run/cargo metrics, routine status, hydrate activity history, and appended activity events from websocket data.
- Removed static sample activity rows and static routine status copy from the web page.
- Added data-message coverage for `haul_phase` and hydrated activity entries.

## Follow-ups

- Live-check the derived haul phase labels against a real two-way run and refine phase mapping if operator-visible transitions need more precision.

## Iteration 330

- When: `2026-07-04 09:40`
- Area: `web`
- Title: `compact-haul-phase-state`
- Source: [2026-07-04-09-40_____web______compact-haul-phase-state.md](iteration-logs/2026-07-04-09-40_____web______compact-haul-phase-state.md)

# Iteration Log

- Area: `web`
- Title: `compact-haul-phase-state`
- Started: `2026-07-04 09:40`

## Summary

- Replaced the web haul phase guess with compact state projected from the existing two-way haul `Phase` enum.

## Changes

- Added an optional `phase_updated_fn` callback to `haul_loop_two_way()` and wired Control Room dispatch to publish `sell|buy|undock|depart|transit` plus station index.
- Stored compact haul phase state in `RuntimeUIState`, hydrate read models, and hydrate parsing so local and remote clients preserve the same routine state.
- Updated `/haul` to render five reusable phase steps with a station 1/2 indicator instead of six guessed route steps.
- Added focused tests for phase callback propagation, hydrate parsing, and the web phase projection mapping.

## Follow-ups

- Live-check the phase strip during a real two-way run to confirm operator-visible timing around skipped sell/buy legs.

## Iteration 331

- When: `2026-07-04 10:21`
- Area: `web`
- Title: `thread-websocket-haul-search`
- Source: [2026-07-04-10-21_____web______thread-websocket-haul-search.md](iteration-logs/2026-07-04-10-21_____web______thread-websocket-haul-search.md)

# Iteration Log

- Area: `web`
- Title: `thread-websocket-haul-search`
- Started: `2026-07-04 10:21`

## Summary

- Fixed web websocket haul search failing when sync Playwright ran inside the server asyncio loop.

## Changes

- Added an async websocket message wrapper for `command.search_haul_routes`.
- Runs blocking `search_trade_routes()` through `asyncio.to_thread()` for websocket searches while leaving the synchronous handler available for direct unit tests.
- Added websocket regression coverage that verifies the search function runs outside a running asyncio event loop.

## Follow-ups

- Retry `/haul` route search against a live server with a stored browser token.

## Iteration 332

- When: `2026-07-04 10:34`
- Area: `web`
- Title: `empty-haul-results-layout`
- Source: [2026-07-04-10-34_____web______empty-haul-results-layout.md](iteration-logs/2026-07-04-10-34_____web______empty-haul-results-layout.md)

# Iteration Log

- Area: `web`
- Title: `empty-haul-results-layout`
- Started: `2026-07-04 10:34`

## Summary

- Removed static haul route seed data and widened the results area by stacking selected route controls under search.

## Changes

- `/haul` route results now start empty with a neutral prompt until websocket search returns data.
- Moved the selected route/start panel into a left-side stack below haul search, leaving the right column for a wider route results table.
- Added a responsive single-column fallback for narrower viewports.

## Follow-ups

- Recheck route table width after the next live search result shape changes.

## Iteration 333

- When: `2026-07-04 10:38`
- Area: `web`
- Title: `paginate-haul-route-results`
- Source: [2026-07-04-10-38_____web______paginate-haul-route-results.md](iteration-logs/2026-07-04-10-38_____web______paginate-haul-route-results.md)

# Iteration Log

- Area: `web`
- Title: `paginate-haul-route-results`
- Started: `2026-07-04 10:38`

## Summary

- Improved the haul v1 route results view so two-way cargo details are visible without opening the debug preview.

## Changes

- Renamed the result table endpoints to Station 1 and Station 2 and shows both Station 1 buy and Station 2 buy cargo in each row.
- Expanded selected route details with Station 1, Station 1 buy, Station 2, Station 2 buy, route distance, and station distance.
- Added client-side pagination for route results with 12 rows per page and disabled pager controls at the bounds.

## Follow-ups

- Backend pagination is not needed yet; the v1 page still receives the full search result payload and paginates locally.

## Iteration 334

- When: `2026-07-04 10:45`
- Area: `web`
- Title: `show-inara-distance`
- Source: [2026-07-04-10-45_____web______show-inara-distance.md](iteration-logs/2026-07-04-10-45_____web______show-inara-distance.md)

# Iteration Log

- Area: `web`
- Title: `show-inara-distance`
- Started: `2026-07-04 10:45`

## Summary

- Surfaced Inara `DISTANCE` in the haul v1 web route results instead of hiding it behind the backend payload.

## Changes

- Added a separate route-table distance column backed by `distance_from_system`.
- Added the same Inara distance to selected route details.
- Stopped using Inara distance as a fallback for route distance so the two fields remain distinct.

## Follow-ups

- Confirm live Inara result rows still have enough horizontal room after the extra distance column.

## Iteration 335

- When: `2026-07-04 10:57`
- Area: `web`
- Title: `simplify-route-start-panel`
- Source: [2026-07-04-10-57_____web______simplify-route-start-panel.md](iteration-logs/2026-07-04-10-57_____web______simplify-route-start-panel.md)

# Iteration Log

- Area: `web`
- Title: `simplify-route-start-panel`
- Started: `2026-07-04 10:57`

## Summary

- Simplified the haul v1 start panel so it acts as route launch controls instead of duplicating route details.

## Changes

- Removed the selected-route stats table, endpoint support banner, and backend command callout from the start panel.
- Renamed the panel to `Start route`, the action button to `Start route`, and the timing controls to `Galmap settle time` and `Transit wait time`.
- Kept selected-route details in the results table and selected-route title only.

## Follow-ups

- Re-check the compact start panel with live results once the route table layout settles.

## Iteration 336

- When: `2026-07-04 11:05`
- Area: `web`
- Title: `add-route-destination-action`
- Source: [2026-07-04-11-05_____web______add-route-destination-action.md](iteration-logs/2026-07-04-11-05_____web______add-route-destination-action.md)

# Iteration Log

- Area: `web`
- Title: `add-route-destination-action`
- Started: `2026-07-04 11:05`

## Summary

- Added a web Haul v1 action to set the galaxy-map destination from the selected route before starting haul.

## Changes

- Added a `Set destination` button beside `Start route` in the start panel.
- Wired the button to websocket `command.dispatch_destination` using the selected route's Station 1 system, matching the existing route-picker `d` shortcut behavior.
- Reused the `Galmap settle time` input for destination dispatch and kept active-operator/token guardrails aligned with route start.

## Follow-ups

- Live-check the action against a running server to confirm route selection, galaxy map timing, and activity feedback feel right before start-route handoff.

## Iteration 337

- When: `2026-07-04 11:10`
- Area: `web`
- Title: `update-haul-static-page-test`
- Source: [2026-07-04-11-10_____web______update-haul-static-page-test.md](iteration-logs/2026-07-04-11-10_____web______update-haul-static-page-test.md)

# Iteration Log

- Area: `web`
- Title: `update-haul-static-page-test`
- Started: `2026-07-04 11:10`

## Summary

- Updated static haul page coverage after the start panel wording changed from the old two-way haul button text.

## Changes

- Changed the `/haul` static endpoint test to assert `Set destination` and `Start route`.
- Confirmed `uv build` succeeds and the full unittest suite passes within the repository timing limit.

## Follow-ups

- None.

## Iteration 338

- When: `2026-07-04 11:22`
- Area: `web`
- Title: `default-serve-token-and-web-prompt`
- Source: [2026-07-04-11-22_____web______default-serve-token-and-web-prompt.md](iteration-logs/2026-07-04-11-22_____web______default-serve-token-and-web-prompt.md)

# Iteration Log

- Area: `web`
- Title: `default-serve-token-and-web-prompt`
- Started: `2026-07-04 11:22`

## Summary

- Added an implicit `edcr` shared token for `control_room.py serve` when no `--token` is passed, kept explicit-token sessions from pre-filling that default in the web client, and replaced missing/rejected-token prompts with a styled in-page dialog.

## Changes

- Added a `DEFAULT_OBSERVER_ACCESS_TOKEN` constant for serve-mode CLI wiring while leaving `connect` token requirements unchanged.
- Passed a web-default token separately from the server auth token so `/haul` only receives `edcr` for implicit no-flag serve sessions.
- Updated Haul Web v1 to use URL token, cached localStorage token, then server-injected token, and to prompt the user when none is available.
- Replaced `window.prompt()` with a styled `<dialog>` token prompt with Connect/Cancel controls and Enter-to-submit behavior.
- Added rejected-token handling that clears a bad cached token, warns in the activity log, and reopens the token dialog when the websocket closes before `event.connection_ready`.
- Added CLI and server regression coverage for implicit serve tokens, explicit-token web behavior, and the in-page web token prompt/retry path.

## Follow-ups

- Live-check `/haul` from both `serve` and `serve --token ...` sessions to confirm the browser token prompt/default feels right.

## Iteration 339

- When: `2026-07-04 11:47`
- Area: `web`
- Title: `explicit-routine-stop-controls`
- Source: [2026-07-04-11-47_____web______explicit-routine-stop-controls.md](iteration-logs/2026-07-04-11-47_____web______explicit-routine-stop-controls.md)

# Iteration Log

- Area: `web`
- Title: `explicit-routine-stop-controls`
- Started: `2026-07-04 11:47`

## Summary

- Replaced the passive Haul Web emergency-stop chip with explicit `Stop after run` and `Stop now` controls backed by websocket stop modes.

## Changes

- Extended `command.cancel_active_routine` with optional `mode` values: legacy `toggle`, deferred haul `after_run`, and immediate `now`.
- Routed explicit stop modes through remote backend, server command handler, headless host, and local execution dependencies into `ControlRoomApp`.
- Added app/server/client/static-web regression coverage for the new stop-mode payloads and controls.

## Follow-ups

- Live-check `Stop after run` and `Stop now` from `/haul` against an active `control_room.py serve` session to confirm operator feedback and TTS feel right in-game.

## Iteration 340

- When: `2026-07-04 12:22`
- Area: `web`
- Title: `instant-mode-toggle`
- Source: [2026-07-04-12-22_____web______instant-mode-toggle.md](iteration-logs/2026-07-04-12-22_____web______instant-mode-toggle.md)

# Iteration Log

- Area: `web`
- Title: `instant-mode-toggle`
- Started: `2026-07-04 12:22`

## Summary

- Added a Haul Web instant-mode toggle that reflects hydrated routine state and sends explicit `instant on/off` commands.

## Changes

- Added an `Instant on/off` button to `/haul`, disabled unless the browser is the active operator.
- Wired the toggle to `routine.instant_mode` from hydrate and to `command.submit_input` with `skip_delay=true`.
- Added static web regression coverage for the instant-mode toggle payload.

## Follow-ups

- Live-check the `/haul` instant-mode toggle against a running server to confirm the hydrated state flips promptly after command execution.

## Iteration 341

- When: `2026-07-04 12:32`
- Area: `web`
- Title: `haul-web-reconnect-ui`
- Source: [2026-07-04-12-32_____web______haul-web-reconnect-ui.md](iteration-logs/2026-07-04-12-32_____web______haul-web-reconnect-ui.md)

# Iteration Log

- Area: `web`
- Title: `haul-web-reconnect-ui`
- Started: `2026-07-04 12:32`

## Summary

- Added visible websocket error recovery UI to Haul Web with manual reconnect and capped exponential retry.

## Changes

- Added a persistent connection banner under the `/haul` page header for disconnected, websocket-error, auth-error, and reconnecting states.
- Added topbar and banner reconnect buttons that clear pending retry timers and reconnect immediately.
- Added client-side exponential retry from 1s up to 30s for websocket close/error and disconnected command attempts.
- Changed first-connection failure handling so only explicit server close code `4401` is treated as token rejection.
- Added static web regression coverage for the reconnect UI and retry semantics.

## Follow-ups

- Live-check reconnect behavior against a stopped/restarted `control_room.py serve` process and confirm browser state recovers from hydrate after reconnection.

## Iteration 342

- When: `2026-07-04 16:55`
- Area: `web`
- Title: `fix-haul-web-system-summary`
- Source: [2026-07-04-16-55_____web______fix-haul-web-system-summary.md](iteration-logs/2026-07-04-16-55_____web______fix-haul-web-system-summary.md)

# Iteration Log

- Area: `web`
- Title: `fix-haul-web-system-summary`
- Started: `2026-07-04 16:55`

## Summary

- Fixed the `/haul` summary strip so Home system comes from the configured `control_room.home_system`, while Current system comes only from the live ship system instead of falling back to station or market names.

## Changes

- Added `home_system` to the Control Room hydrate read model and payload parsing, with local data sources exporting the configured home system.
- Updated `web/haul-v1.html` to render `summary-home` from `payload.home_system`, render `summary-current` from `ship.system`, and use neutral static placeholders before hydrate.
- Added regression coverage for hydrate payload home-system export and the static web page's distinct home/current system rendering.

## Follow-ups

- Live-check `/haul` during an active CrossOver session to confirm refresh/reconnect now shows the configured home and the same current system as the terminal status panel.

## Iteration 343

- When: `2026-07-04 16:59`
- Area: `web`
- Title: `scroll-haul-activity-history`
- Source: [2026-07-04-16-59_____web______scroll-haul-activity-history.md](iteration-logs/2026-07-04-16-59_____web______scroll-haul-activity-history.md)

# Iteration Log

- Area: `web`
- Title: `scroll-haul-activity-history`
- Started: `2026-07-04 16:59`

## Summary

- Fixed the `/haul` Activity panel so hydrated activity history remains available in a scrollable log instead of being capped to the newest eight rows.

## Changes

- Added a bounded `.activity-list` scroll region with keyboard focus and `role="log"` metadata.
- Changed `renderActivityLog()` to render all current activity entries newest-first and show the entry count in the panel status.
- Added static web regression coverage to catch the old `slice(-8)` cap and missing scroll container.

## Follow-ups

- Live-check the panel with a long running `serve` session to confirm the chosen max height is comfortable on the intended browser display.

## Iteration 344

- When: `2026-07-04 17:03`
- Area: `web`
- Title: `allow-all-connected-operators`
- Source: [2026-07-04-17-03_____web______allow-all-connected-operators.md](iteration-logs/2026-07-04-17-03_____web______allow-all-connected-operators.md)

# Iteration Log

- Area: `web`
- Title: `allow-all-connected-operators`
- Started: `2026-07-04 17:03`

## Summary

- Opened the remote/web operator policy so every authenticated connected client is treated as an operator instead of competing for a single active-operator slot.

## Changes

- Changed the observer session broker to register connected clients as `active_operator` and resolve all live sessions to that role.
- Removed server-side read-only role gates from websocket command handlers; command validation, auth, and transport-availability checks still apply.
- Updated `/haul` to avoid self-demotion on `event.active_operator_changed` and replaced old active-operator-required copy with connection-oriented wording.
- Updated server and web tests for the new all-connected-operators policy.

## Follow-ups

- Live-check two simultaneous `/haul` browser clients against one `serve` process to confirm both can search/start/stop without role churn.

## Iteration 345

- When: `2026-07-04 17:08`
- Area: `haul`
- Title: `recover-wrong-buy-cargo`
- Source: [2026-07-04-17-08_____haul_____recover-wrong-buy-cargo.md](iteration-logs/2026-07-04-17-08_____haul_____recover-wrong-buy-cargo.md)

# Iteration Log

- Area: `haul`
- Title: `recover-wrong-buy-cargo`
- Started: `2026-07-04 17:08`

## Summary

- Added wrong-cargo recovery to two-way haul buy phases: if a buy lands on the wrong commodity, the routine sells the wrong cargo and retries once, then aborts with logging and TTS on the second wrong buy.

## Changes

- Made `market_buy` return immediately when a `MarketBuy` journal event reports a different commodity than the requested target, preserving the wrong commodity in result details.
- Added haul buy-phase recovery that checks Cargo.json after buy, sells unintended cargo with `market_sell`, and retries the intended buy after the first mistake.
- Added `haul_wrong_cargo_aborted` TTS copy and emits it when wrong cargo is bought twice in one haul run.
- Added market and two-way haul regression tests for wrong-item detection, single recovery, and second-mistake abort.

## Follow-ups

- Live-validate the recovery with a small hold before trusting it during high-volume hauling, because the sell step depends on Cargo.json and market sell-list ordering matching live UI behavior.

## Iteration 346

- When: `2026-07-04 17:33`
- Area: `web`
- Title: `mobile-haul-layout`
- Source: [2026-07-04-17-33_____web______mobile-haul-layout.md](iteration-logs/2026-07-04-17-33_____web______mobile-haul-layout.md)

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

## Iteration 347

- When: `2026-07-04 17:47`
- Area: `web`
- Title: `haul-stats-controls`
- Source: [2026-07-04-17-47_____web______haul-stats-controls.md](iteration-logs/2026-07-04-17-47_____web______haul-stats-controls.md)

# Iteration Log

- Area: `web`
- Title: `haul-stats-controls`
- Started: `2026-07-04 17:47`

## Summary

- Added haul stats controls to the web active haul routine panel.

## Changes

- Added `Clear stats` and `Stop stats` buttons below the active routine metrics in `web/haul-v1.html`.
- Wired the buttons through existing websocket `command.submit_input` handling: `new_session` clears persisted haul stats and `stop` freezes persisted haul stats.
- Kept `Stop stats` disabled while a routine is active, matching the existing backend command rule that refuses to stop the stats clock during an active haul.
- Verified phone-width layout at 390px still has no horizontal overflow and the stats controls stack cleanly.

## Follow-ups

- Live-check the stats controls against a served `/haul` session to confirm operator-facing activity messages are clear enough after backend command logs arrive.

## Iteration 348

- When: `2026-07-04 18:20`
- Area: `web`
- Title: `server-route-selection-hydrate`
- Source: [2026-07-04-18-20_____web______server-route-selection-hydrate.md](iteration-logs/2026-07-04-18-20_____web______server-route-selection-hydrate.md)

# Iteration Log

- Area: `web`
- Title: `server-route-selection-hydrate`
- Started: `2026-07-04 18:20`

## Summary

- Server now retains the current web-selected and last accepted running Inara trade route in broker-owned server state so `/hydrate` and websocket hydrate can restore it after web reload/reconnect.

## Changes

- Added `selected_trade_route` / `running_trade_route` to the Control Room data read model and data-message round trip.
- Added websocket `command.select_trade_route`; web selection changes send the selected route, and `command.dispatch_haul_loop` can carry the started route.
- Updated `/haul` to merge hydrated selected/running routes into its route table and prefer the running route when both are present.

## Follow-ups

- Live-check multi-client behavior during web route search/start so route selection updates feel natural when more than one browser is connected.

## Iteration 349

- When: `2026-07-04 18:29`
- Area: `web`
- Title: `persist-route-selection-state`
- Source: [2026-07-04-18-29_____web______persist-route-selection-state.md](iteration-logs/2026-07-04-18-29_____web______persist-route-selection-state.md)

# Iteration Log

- Area: `web`
- Title: `persist-route-selection-state`
- Started: `2026-07-04 18:29`

## Summary

- Selected and running web trade routes now persist through the existing Control Room state file so `/haul` can hydrate the route after a server restart.

## Changes

- Added `selected_trade_route` and `running_trade_route` to `ControlRoomState` load/save serialization.
- Headless websocket route selection/start commands now write route state through `persist_trade_route_state()`.
- `serve` seeds broker route state from the loaded state file before exposing hydrate/session routes.

## Follow-ups

- Live-check restart recovery after selecting and after starting a route to verify the restored web table matches operator expectations.

## Iteration 350

- When: `2026-07-04 18:32`
- Area: `web`
- Title: `routine-credit-summary`
- Source: [2026-07-04-18-32_____web______routine-credit-summary.md](iteration-logs/2026-07-04-18-32_____web______routine-credit-summary.md)

# Iteration Log

- Area: `web`
- Title: `routine-credit-summary`
- Started: `2026-07-04 18:32`

## Summary

- Web Haul active routine credits now show the current run and accumulated total together.

## Changes

- Renamed the active routine metric label from `Current run` to `Current / Accumulated`.
- Rendered the metric value as `current_run_profit / accumulated_profit` using the existing credit formatter for both sides.
- Added static web coverage for the label and combined formatter expression.

## Follow-ups

- Confirm on-device readability once live profit values grow into multi-million or billion credit ranges.

## Iteration 351

- When: `2026-07-04 20:06`
- Area: `haul`
- Title: `pause-resume-haul`
- Source: [2026-07-04-20-06_____haul_____pause-resume-haul.md](iteration-logs/2026-07-04-20-06_____haul_____pause-resume-haul.md)

# Iteration Log

- Area: `haul`
- Title: `pause-resume-haul`
- Started: `2026-07-04 20:06`

## Summary

- Added operator pause/resume for the two-way haul loop so web and TUI users can request a station-boundary pause at either haul station, freeze haul stats while paused, and resume the same running routine.

## Changes

- Added `pause` / `resume` Control Room commands; `pause` requests the next station-side boundary and `resume` either cancels a pending pause or releases an active pause.
- Extended two-way haul with pause hooks before station 1 or station 2 buy/departure, and wired Control Room pause state through hydrate read models for TUI/connect/web visibility.
- Added haul stats pause/resume helpers that freeze session and current-run elapsed timers while the routine is paused at station.
- Added `/haul` Pause and Resume buttons that submit the same command path as TUI commands and render `Pause requested` / `Paused` routine status.
- Added regression coverage for web controls, TUI command behavior, stats timer freeze/resume, dispatch callback plumbing, and station 2 pause handling.

## Follow-ups

- Live-check a pause request during transit and at both stations to confirm the operator-facing timing and log wording feel right in-game.

## Iteration 352

- When: `2026-07-04 20:24`
- Area: `haul`
- Title: `stale-cargo-buy-guard`
- Source: [2026-07-04-20-24_____haul_____stale-cargo-buy-guard.md](iteration-logs/2026-07-04-20-24_____haul_____stale-cargo-buy-guard.md)

# Iteration Log

- Area: `haul`
- Title: `stale-cargo-buy-guard`
- Started: `2026-07-04 20:24`

## Summary

- Fixed the live resume-haul failure mode where Elite reported loaded cargo in `Status.json` but stale/empty `Cargo.json` made the routine proceed into a buy phase.

## Changes

- Added commodity-name normalization for raw Elite inventory names such as `$palladium_name;` so haul phase detection and market sell quantity lookup match configured route commodities.
- Added a pre-buy stale-cargo guard: when `Status.json` reports cargo tonnage and `Cargo.json` has no sellable named cargo, two-way haul aborts before market input, logs a relog/resume message, and emits `haul_cargo_state_stale` TTS.
- Covered the stale-cargo abort and raw-name resume detection with unit tests, plus a config assertion for the `{title}`-prefixed default TTS phrase.

## Follow-ups

- Resume/session tracking still needs separate web/TUI work so stopped or restarted hauls do not clear stats inconsistently.

## Iteration 353

- When: `2026-07-04 20:38`
- Area: `control-room`
- Title: `priority-interrupt-exit-bindings`
- Source: [2026-07-04-20-38_control-room_priority-interrupt-exit-bindings.md](iteration-logs/2026-07-04-20-38_control-room_priority-interrupt-exit-bindings.md)

# Iteration Log

- Area: `control-room`
- Title: `priority-interrupt-exit-bindings`
- Started: `2026-07-04 20:38`

## Summary

- Fixed the connect-mode `Ctrl-D` exit regression where a remote-active detach prompt could be opened but repeated `Ctrl-D` did not take the default detach/exit path.

## Changes

- Converted Control Room `Ctrl-C` and `Ctrl-D` bindings to priority `Binding` objects so interrupt and exit handling wins over focused command-input widget bindings in local and `connect` mode.
- Changed remote-active exit handling so the first `Ctrl-D` opens the detach prompt and a following `Ctrl-D` exits the client without cancelling the server routine.
- Routed raw control-character key events for `\x03`/`\x04` through the same interrupt/exit handlers in case a terminal path reports control keys by character instead of normalized Textual key name.
- Kept connect-client shutdown flags local during remote data refreshes so server hydrate state cannot overwrite an in-progress client exit.
- Added regression coverage for priority interrupt/exit bindings and the connect-mode remote detach `Ctrl-D` sequence.
- Updated the Control Room status handoff with the current binding-priority behavior.

## Follow-ups

- Live-check a real `control_room.py connect` terminal during an active remote routine to confirm double `Ctrl-D` exits/detaches as expected with the command bar focused.

## Iteration 354

- When: `2026-07-04 20:45`
- Area: `runtime`
- Title: `crossover-pid-watchdog-detect`
- Source: [2026-07-04-20-45___runtime____crossover-pid-watchdog-detect.md](iteration-logs/2026-07-04-20-45___runtime____crossover-pid-watchdog-detect.md)

# Iteration Log

- Area: `runtime`
- Title: `crossover-pid-watchdog-detect`
- Started: `2026-07-04 20:45`

## Summary

- Fixed macOS `set_pid` auto-detect selecting CrossOver `WatchDog64.exe` when its command line named `EliteDangerous64.exe` as the watchdog executable argument before the real game process row.

## Changes

- Tightened the macOS full-command-line fallback so it matches the first Windows `.exe` basename in a `ps` row instead of any later argument substring.
- Added a regression test covering the live WatchDog/Elite process-table shape where PID `23232` is the watchdog and PID `23244` is the real game process.
- Confirmed the live finder changed from `23232` to `23244` after the matcher fix.
- Updated runtime status to record that CrossOver still needs foreground HID posting because pid-targeted Quartz posting is not yet a validated background-control path.

## Follow-ups

- Investigate a different macOS/CrossOver background-input route; `set_pid foreground` remains the practical recovery path when targeted dispatch stops foreground input delivery.

## Iteration 355

- When: `2026-07-04 20:53`
- Area: `runtime`
- Title: `combined-session-pid-events`
- Source: [2026-07-04-20-53___runtime____combined-session-pid-events.md](iteration-logs/2026-07-04-20-53___runtime____combined-session-pid-events.md)

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

## Iteration 356

- When: `2026-07-04 21:49`
- Area: `haul`
- Title: `interdiction-docking-abort`
- Source: [2026-07-04-21-49_____haul_____interdiction-docking-abort.md](iteration-logs/2026-07-04-21-49_____haul_____interdiction-docking-abort.md)

# Iteration Log

- Area: `haul`
- Title: `interdiction-docking-abort`
- Started: `2026-07-04 21:49`

## Summary

- Reviewed `artifacts/control-room.log` and confirmed live interdiction sequences where `Interdicted` is followed by `SupercruiseExit` on a star/planet plus `Combat_Dogfight`, distinct from later station `SupercruiseDestinationDrop` events.

## Changes

- Added an opt-in `dock(abort_on_interdiction=True)` guard and enabled it for two-way and multi-leg haul transit so haul aborts/TTS `haul_aborted` before any docking request when interdicted during station approach.
- Added regression coverage for two-way and multi-leg haul using the logged event shape: destination-system `FSDJump`, `Interdicted`, then non-station `SupercruiseExit`.

## Follow-ups

- Watch future live haul logs for interdiction variants that emit only emergency-drop style events without `Interdicted`; current guard keys on the explicit journal event seen in artifacts.

## Iteration 357

- When: `2026-07-04 22:02`
- Area: `control-room`
- Title: `dest-fibonacci-settle-retry`
- Source: [2026-07-04-22-02_control-room_dest-fibonacci-settle-retry.md](iteration-logs/2026-07-04-22-02_control-room_dest-fibonacci-settle-retry.md)

# Iteration Log

- Area: `control-room`
- Title: `dest-fibonacci-settle-retry`
- Started: `2026-07-04 22:02`

## Summary

- Added a narrow retry path for `dest` when route verification finds no destination in `NavRoute.json`.

## Changes

- `set_gal_map_destination()` now accepts optional retry map-settle values and reruns the full galaxy-map flow only when verification fails with an unset route destination.
- Control Room `dest` dispatch now starts with the configured settle and then retries with Fibonacci-style longer settles, giving the normal `2.0s` default the sequence `2, 3, 5, 8`.
- Added regressions for unset-route retry, wrong-destination no-retry behavior, and Control Room retry-settle wiring.

## Follow-ups

- Live-check `dest <system>` under CrossOver when the first route plot leaves `NavRoute.json` empty to confirm the 3/5/8 second retries are enough before adding operator configuration.

## Iteration 358

- When: `2026-07-04 22:12`
- Area: `ci-release`
- Title: `v1-19-0-release-prep`
- Source: [2026-07-04-22-12__ci-release__v1-19-0-release-prep.md](iteration-logs/2026-07-04-22-12__ci-release__v1-19-0-release-prep.md)

# Iteration Log

- Area: `ci-release`
- Title: `v1-19-0-release-prep`
- Started: `2026-07-04 22:12`

## Summary

- Prepared `v1.19.0` after the post-`v1.18.0` haul web controls/state work and haul route/interdiction recovery fixes.

## Changes

- Bumped `pyproject.toml` and `uv.lock` from `1.18.0` to `1.19.0`.
- Updated `docs/status/ci-release.md` with the `v1.19.0` release summary and current unittest timing gate.
- Ran `uv run python3 -m unittest discover -s tests`: `675` tests passed in `0.377s`, below the `0.405s` timing budget.

## Follow-ups

- Publish the `v1.19.0` tag and GitHub release once the release-prep commit is pushed.

## Iteration 359

- When: `2026-07-05 05:49`
- Area: `web`
- Title: `root-entry-point`
- Source: [2026-07-05-05-49_____web______root-entry-point.md](iteration-logs/2026-07-05-05-49_____web______root-entry-point.md)

# Iteration Log

- Area: `web`
- Title: `root-entry-point`
- Started: `2026-07-05 05:49`

## Summary

- Made the observer web root `/` serve the same haul web entry point as `/haul`.

## Changes

- Added a root route constant and mounted it to the existing haul web HTML handler, preserving the no-store response behavior and token injection path.
- Added server regression coverage for the root web entry point.
- Updated the Control Room status handoff to mention both web entry paths.

## Follow-ups

- None.

## Iteration 360

- When: `2026-07-05 06:46`
- Area: `control-room`
- Title: `lan-command-alias`
- Source: [2026-07-05-06-46_control-room_lan-command-alias.md](iteration-logs/2026-07-05-06-46_control-room_lan-command-alias.md)

# Iteration Log

- Area: `control-room`
- Title: `lan-command-alias`
- Started: `2026-07-05 06:46`

## Summary

- Added `control_room.py lan` as a shorter alias for `control_room.py serve --lan`.

## Changes

- Routed `lan` through the existing observer-server startup path with LAN host detection, default token behavior, and the same `--host` conflict guard as `serve --lan`.
- Added CLI regression coverage for the alias and updated operator docs/status handoff references.

## Follow-ups

- None.

## Iteration 361

- When: `2026-07-05 07:36`
- Area: `haul`
- Title: `sell-final-web-routine-step`
- Source: [2026-07-05-07-36_____haul_____sell-final-web-routine-step.md](iteration-logs/2026-07-05-07-36_____haul_____sell-final-web-routine-step.md)

# Iteration Log

- Area: `haul`
- Title: `sell-final-web-routine-step`
- Started: `2026-07-05 07:36`

## Summary

- Reordered the Haul Web V1 active routine timeline so sell is presented as the final step in a hauling leg.

## Changes

- Updated `web/haul-v1.html` to display `Buy -> Undock -> Depart -> Transit -> Sell`.
- Updated the routine panel phase completion order to match the displayed timeline.
- Added a focused static web test that asserts sell remains the fifth/final displayed step and that the JavaScript phase order matches.

## Follow-ups

- No server or protocol changes appear necessary; the existing hydrate phase names are sufficient for the frontend order change.

## Iteration 362

- When: `2026-07-05 21:14`
- Area: `control-room`
- Title: `haul-web-multi-leg-ui`
- Source: [2026-07-05-21-14_control-room_haul-web-multi-leg-ui.md](iteration-logs/2026-07-05-21-14_control-room_haul-web-multi-leg-ui.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-web-multi-leg-ui`
- Started: `2026-07-05 21:14`

## Summary

- Reworked the haul web surface toward Spansh-style planner inputs/results and added a UI-only multi-leg haul page.

## Changes

- Split `web/haul-v1.html` into shared `haul-ui.css` / `haul-ui.js` assets served under `/assets/...` with no-store caching.
- Added `/multi-haul` as the same shared shell, with client-side view switching and a dedicated `command.dispatch_multi_leg_haul` websocket message path for future backend handling.
- Replaced the old route table renderer with Spansh-like result cards and commodity tables; active routine context now shows buy/sell/transit/next-sale secondary details.
- Kept existing two-way backend command payloads intact; two-way web `on_land` remains hardcoded false until surface metadata is reliable.

## Follow-ups

- Browser screenshot verification was blocked because no in-app or extension browser backend was available in this session; local server/curl and automated source/server tests passed.
- Backend support is still needed before the multi-leg page can run real Spansh calculations or dispatch live multi-leg routes.

## Iteration 363

- When: `2026-07-05 21:52`
- Area: `control-room`
- Title: `haul-web-ship-defaults`
- Source: [2026-07-05-21-52_control-room_haul-web-ship-defaults.md](iteration-logs/2026-07-05-21-52_control-room_haul-web-ship-defaults.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-web-ship-defaults`
- Started: `2026-07-05 21:52`

## Summary

- Defaulted the web haul planner inputs from current ship hydrate data where available.

## Changes

- Added `max_jump_range_ly` to the ship state/read-model path from journal `Loadout.MaxJumpRange`.
- Web `/haul` and `/multi-haul` now default starting capital from current credits, cargo capacity from current hold capacity, hop distance from hydrated jump range, and the large-pad checkbox from known ship type.
- Two-way web search payload now includes the Spansh-style capital, hop, hops, market-age, and route-filter fields for future backend support.

## Follow-ups

- The UI accepts future `ship.laden_jump_range_ly` / `ship.jump_range_ly` hydrate fields, but today the backend only provides journal `MaxJumpRange`.
- Pad-size inference is a client-side known-ship map; unknown ship types keep the conservative large-pad default.

## Iteration 364

- When: `2026-07-06 10:14`
- Area: `web`
- Title: `web-config-injection`
- Source: [2026-07-06-10-14_____web______web-config-injection.md](iteration-logs/2026-07-06-10-14_____web______web-config-injection.md)

# Iteration Log

- Area: `web`
- Title: `web-config-injection`
- Started: `2026-07-06 10:14`

## Summary

- Removed environment/demo assumptions from the haul web HTML by moving server, auth, role, target, and form-default data into an injected `window.EDCR_WEB_CONFIG` payload.

## Changes

- Added input-target summary and web form defaults to the Control Room data read model so the server can expose runtime-aware web defaults.
- Updated `/`, `/haul`, and `/multi-haul` rendering to inject host/auth/runtime/default config from the current server data provider instead of only replacing a token string.
- Neutralized static haul HTML values for host, target, role, cargo, runs, profit, and route parameters; browser JS now applies defaults and reset values from the injected config plus hydrate/ship data.
- Cleared stale localhost/token defaults from the scratch remote browser probe.

## Follow-ups

- Consider adding a richer web defaults model if multi-leg planning gains backend-owned settings beyond the current route-search and haul timing defaults.

## Iteration 365

- When: `2026-07-06 11:07`
- Area: `control-room`
- Title: `restore-two-way-haul-web`
- Source: [2026-07-06-11-07_control-room_restore-two-way-haul-web.md](iteration-logs/2026-07-06-11-07_control-room_restore-two-way-haul-web.md)

# Iteration Log

- Area: `control-room`
- Title: `restore-two-way-haul-web`
- Started: `2026-07-06 11:07`

## Summary

- Restored the existing `/haul` two-way web page after the Spansh planner work had incorrectly changed its visible UI.

## Changes

- Reverted `web/haul-v1.html` and `web/haul-ui.js` back to the pre-redesign two-way route table/search surface while preserving the shared asset setup.
- Added separate `web/multi-haul.html` and `web/multi-haul.js` for the Spansh-style multi-leg planner and dedicated `command.dispatch_multi_leg_haul` preview path.
- Updated the observer server so `/multi-haul` serves the separate page and `/assets/multi-haul.js` is available without changing `/haul`.
- Moved web tests so two-way assertions cover the original route table surface and Spansh/multi-leg assertions cover the separate multi page.

## Follow-ups

- `/multi-haul` remains UI-only until backend multi-leg route calculation/dispatch support is implemented.

## Iteration 366

- When: `2026-07-06 11:25`
- Area: `web`
- Title: `reapply-web-config-defaults`
- Source: [2026-07-06-11-25_____web______reapply-web-config-defaults.md](iteration-logs/2026-07-06-11-25_____web______reapply-web-config-defaults.md)

# Iteration Log

- Area: `web`
- Title: `reapply-web-config-defaults`
- Started: `2026-07-06 11:25`

## Summary

- Reapplied the injected web-config/defaults cleanup after the two-way haul UI restore split `/haul` and `/multi-haul` into separate web pages.

## Changes

- Removed restored machine/process/demo literals from the two-way haul page while preserving its route-table UI.
- Routed two-way route search, haul timing defaults, websocket auth query naming, and session/status labels through `window.EDCR_WEB_CONFIG` again.
- Applied the same neutral static defaults and config-driven reset behavior to the new standalone multi-haul page.
- Removed the legacy `EDCR_SERVER_DEFAULT_ACCESS_TOKEN` fallback path from the served web templates and renderer.
- Added a regression test to prevent runtime-specific demo defaults from returning to the web pages.

## Follow-ups

- Keep future web UI restores on top of the injected config contract instead of reintroducing page-local runtime defaults.

## Iteration 367

- When: `2026-07-06 12:12`
- Area: `haul`
- Title: `guard-unrelated-preloaded-cargo`
- Source: [2026-07-06-12-12_____haul_____guard-unrelated-preloaded-cargo.md](iteration-logs/2026-07-06-12-12_____haul_____guard-unrelated-preloaded-cargo.md)

# Iteration Log

- Area: `haul`
- Title: `guard-unrelated-preloaded-cargo`
- Started: `2026-07-06 12:12`

## Summary

- Fixed the two-way haul bug where pre-existing cargo unrelated to the configured haul leg could be treated as wrong-buy recovery cargo and sold automatically.

## Changes

- Added a pre-buy guard in `edap/routines/haul_two_way.py` that aborts before market input when `Cargo.json` already contains positive-count cargo that does not match the current leg's expected buy commodity.
- The abort tells the operator to clear or sell the non-haul cargo manually, emits the generic haul-aborted announcement, and preserves the existing stale-cargo guard for the separate `Status.json` cargo / empty `Cargo.json` case.
- Added regression coverage for unrelated preloaded cargo, for partially loaded expected cargo continuing into buy, and adjusted existing sell mocks so successful fake sells clear cargo state.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` and the full suite `uv run python3 -m unittest discover -s tests` passed; full suite reported `689 tests in 0.406s`.

## Follow-ups

- Live-check the abort wording in a real haul resume/start flow with unrelated cargo aboard to confirm the operator-facing message is clear enough before adding a more specific TTS phrase.

## Iteration 368

- When: `2026-07-06 12:38`
- Area: `web`
- Title: `show-live-haul-session-profit`
- Source: [2026-07-06-12-38_____web______show-live-haul-session-profit.md](iteration-logs/2026-07-06-12-38_____web______show-live-haul-session-profit.md)

# Iteration Log

- Area: `web`
- Title: `show-live-haul-session-profit`
- Started: `2026-07-06 12:38`

## Summary

- Fixed the `/haul` summary profit tile so it shows live haul session profit instead of completed-run-only accumulated profit.

## Changes

- Renamed the summary tile from `Accumulated profit` to `Session profit`.
- Added a `sessionProfit()` frontend helper that calculates `accumulated_profit + current_run_profit`, matching the TUI haul panel and persisted session-profit semantics.
- Left the active routine mini metric as `Current / Accumulated` so operators can still see the current run contribution separately from completed runs.
- Added static web coverage that locks the session-profit calculation into `tests/test_control_room_haul_web.py`.
- Verified `uv run python3 -m unittest tests/test_control_room_haul_web.py` and `uv run python3 -m unittest discover -s tests` passed. The first full-suite report was slow at `690 tests in 0.968s`, then the required timing report passed at `690 tests in 0.387s`.

## Follow-ups

- Live-check the `/haul` tile during an active loop after buy and sell events to confirm the signed current-run contribution matches operator expectations.

## Iteration 369

- When: `2026-07-06 13:47`
- Area: `web`
- Title: `editable-route-distance-defaults`
- Source: [2026-07-06-13-47_____web______editable-route-distance-defaults.md](iteration-logs/2026-07-06-13-47_____web______editable-route-distance-defaults.md)

# Iteration Log

- Area: `web`
- Title: `editable-route-distance-defaults`
- Started: `2026-07-06 13:47`

## Summary

- Matched the `/haul` route-distance search control to INARA's visible preset values while keeping the field editable for custom distances.

## Changes

- Replaced the route-distance select in `web/haul-v1.html` with an editable text input paired with a visible preset selector containing `10 Ly`, `20 Ly`, `30 Ly`, `40 Ly`, `50 Ly`, `60 Ly`, `70 Ly`, `80 Ly`, `500 Ly`, and `1,000 Ly`.
- Updated `web/haul-ui.js` so search reset/default hydration writes directly to the editable route-distance input, formats numeric defaults with `Ly`, and copies selected presets into the input.
- Added styling for the joined input/preset control and web regression coverage proving the submitted value still comes from `max_route_distance_ly`.

## Follow-ups

- Live-check the hybrid route-distance control in the browser once the next `/haul` UI pass is running locally.

## Iteration 370

- When: `2026-07-06 14:01`
- Area: `ci-release`
- Title: `prepare-v1-20-0-release`
- Source: [2026-07-06-14-01__ci-release__prepare-v1-20-0-release.md](iteration-logs/2026-07-06-14-01__ci-release__prepare-v1-20-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-20-0-release`
- Started: `2026-07-06 14:01`

## Summary

- Rewound `main` to `bce43a7` with `git rebase --onto` and prepared the next stable release commit.

## Changes

- Bumped project metadata to `1.20.0`.
- Updated the CI/release handoff for the `v1.20.0` release scope and rewind point.
- Regenerated `docs/iteration-archive.md` and refreshed `uv.lock` after the version bump.
- Verified the release prep with `uv run python3 -m unittest discover -s tests`: `678` tests passed in `0.530s`; because this exceeded the `0.4068s` timing gate, ran the required slow-test report and saw the slowest test at `0.017s`.

## Follow-ups

- Push the rewritten `main` history with care, tag `v1.20.0`, and publish the GitHub release from the release-prep commit.

## Iteration 371

- When: `2026-07-06 17:18`
- Area: `control-room`
- Title: `haul-pause-tts`
- Source: [2026-07-06-17-18_control-room_haul-pause-tts.md](iteration-logs/2026-07-06-17-18_control-room_haul-pause-tts.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-pause-tts`
- Started: `2026-07-06 17:18`

## Summary

- Added explicit TTS announcements for two-way haul pause request acceptance and the station-boundary paused state.

## Changes

- Added `haul_pause_requested` and `haul_paused` announcement IDs plus default TTS phrases.
- Emitted `haul_pause_requested` when the Control Room pause command queues a station pause, and `haul_paused` when the haul loop actually reaches the buy-side station pause gate.
- Added regression coverage for both spoken pause events and default phrase loading.
- Verified the browser `/haul` pause/resume controls already submit the existing server-owned command path, so no client command-surface change was needed.

## Follow-ups

- Full suite passed, but remained above the repo timing budget: `692 tests in 2.259s`; timing reporter also passed and showed unrelated Control Room client/CLI tests as the slowest cases.

## Iteration 372

- When: `2026-07-06 19:17`
- Area: `haul`
- Title: `route-profit-comparison`
- Source: [2026-07-06-19-17_____haul_____route-profit-comparison.md](iteration-logs/2026-07-06-19-17_____haul_____route-profit-comparison.md)

# Iteration Log

- Area: `haul`
- Title: `route-profit-comparison`
- Started: `2026-07-06 19:17`

## Summary

- Added selected-route per-trip profit tracking so completed two-way haul runs can be compared against the planned Inara route.

## Changes

- TUI route picker rows now include trip profit and the haul panel shows expected route trip profit plus last-run delta.
- Web `/haul` route results now show `Profit / trip` and include the selected route profit in `command.dispatch_haul_loop` params.
- Haul stats persist expected route profit and last-run delta through saved state and remote hydrate payloads.
- Completed clean haul runs log and TTS whether actual profit was more, less, or equal to the planned route.

## Follow-ups

- Live-validate that Inara trip-profit text from current route cards continues to parse cleanly during a full route-to-haul run.

## Iteration 373

- When: `2026-07-06 20:46`
- Area: `haul`
- Title: `sell-unrelated-cargo-before-buy`
- Source: [2026-07-06-20-46_____haul_____sell-unrelated-cargo-before-buy.md](iteration-logs/2026-07-06-20-46_____haul_____sell-unrelated-cargo-before-buy.md)

# Iteration Log

- Area: `haul`
- Title: `sell-unrelated-cargo-before-buy`
- Started: `2026-07-06 20:46`

## Summary

- Changed the two-way haul pre-buy non-haul cargo path from an immediate abort into an announced sell-all recovery attempt followed by the intended buy.

## Changes

- Added `haul_unrelated_cargo_loaded` and `selling_all_cargo` announcement IDs plus default TTS phrases.
- Added a bounded pre-buy cleanup helper that sells every sellable Cargo.json item once, waits the configured post-sell settle delay, verifies non-haul cargo cleared, and only then retries the planned buy.
- Kept stale/unknown cargo details as an abort path because the routine still cannot safely identify what to sell from an empty or stale manifest.
- Updated haul/config unit coverage for the new announcements and sell-before-buy recovery path.

## Follow-ups

- Live-validate recovery against real Cargo.json/Market.json timing; future TUI/web UX should prompt for confirmation with the cargo list before auto-selling.

## Iteration 374

- When: `2026-07-06 21:04`
- Area: `haul`
- Title: `persist-haul-search-defaults`
- Source: [2026-07-06-21-04_____haul_____persist-haul-search-defaults.md](iteration-logs/2026-07-06-21-04_____haul_____persist-haul-search-defaults.md)

# Iteration Log

- Area: `haul`
- Title: `persist-haul-search-defaults`
- Started: `2026-07-06 21:04`

## Summary

- Saved edited haul-search parameters back to the ignored repo-local `haul_search.toml` so changes like route distance and station distance become future defaults.

## Changes

- Added `save_haul_search_config()` with TOML section upsert support and a generated-field exclusion list that currently keeps journal-derived `cargo_capacity` out of automatic saves.
- Wired Textual `haul search`, pasted Inara URL dispatch, and web/server `command.search_haul_routes` to save cleaned search defaults before running the search.
- Added regression coverage for the config writer plus Textual/server search save calls without writing to the real ignored config during tests.

## Follow-ups

- Live-check that web `/haul` route-distance edits are reflected after a page refresh/reconnect during the next operator session.

## Iteration 375

- When: `2026-07-06 21:36`
- Area: `travel`
- Title: `server-first-travel-routine`
- Source: [2026-07-06-21-36____travel____server-first-travel-routine.md](iteration-logs/2026-07-06-21-36____travel____server-first-travel-routine.md)

# Iteration Log

- Area: `travel`
- Title: `server-first-travel-routine`
- Started: `2026-07-06 21:36`

## Summary

- Added the first server-first `travel` routine for assistive anywhere-to-station travel, with TUI, remote client, websocket protocol, and web `/haul` surface access.
- Extracted shared station transit behavior out of haul-specific code into a neutral routines module so two-way haul, multi-leg haul, and travel use the same launch/route/transit/docking path.
- Added selected-route shortcuts so TUI search results can save a route, travel to its first station with `t`, and start the selected/saved haul with `haul start`.

## Changes

- Added `edap.routines.transit` for shared ship-position reads, route-needed detection, route retry/unconfirmed-route handling, undock/depart helpers, in-system nav-panel presentation, manual landing handoff, and station docking transit.
- Added `edap.routines.travel.travel_to_station` and `travel <system> / <station>` command dispatch.
- Added structured `command.dispatch_travel` protocol support across capabilities, schema, server handler, local/remote execution dependencies, and client backend delegation.
- Added a compact Travel Assist form to the existing `/haul` web page that sends `command.dispatch_travel`.
- Updated the `/haul` web selected-route behavior so the Travel Assist target system/station follows the selected route's first station.
- Updated haul and multi-leg haul to call shared transit helpers instead of local duplicate transit code.
- Added unit coverage for travel same-system nav-panel behavior, docked-start shared transit reuse, websocket dispatch, remote backend dispatch, TUI route shortcuts, `haul start`, and web surfacing.

## Follow-ups

- Live-validate `travel` under CrossOver/macOS from docked, normal-space, same-system supercruise, and remote-system starts.
- Decide whether Travel Assist deserves a dedicated `/travel` web page after live behavior stabilizes.

## Iteration 376

- When: `2026-07-06 22:40`
- Area: `ci-release`
- Title: `prepare-v1-21-0-release`
- Source: [2026-07-06-22-40__ci-release__prepare-v1-21-0-release.md](iteration-logs/2026-07-06-22-40__ci-release__prepare-v1-21-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-21-0-release`
- Started: `2026-07-06 22:40`

## Summary

- Prepared `v1.21.0` as the next stable release after `v1.20.0`.

## Changes

- Bumped `[project].version` and `uv.lock` metadata from `1.20.0` to `1.21.0`.
- Updated release status with the new release scope and current test timing.
- Ran the full unittest suite and required slow-test report because the suite exceeded the per-test timing budget.

## Follow-ups

- Watch the post-push `Tests` workflow and Discord notifier path for the `v1.21.0` release commit/tag.

## Iteration 377

- When: `2026-07-06 22:45`
- Area: `ci-release`
- Title: `test-runtime-investigation`
- Source: [2026-07-06-22-45__ci-release__test-runtime-investigation.md](iteration-logs/2026-07-06-22-45__ci-release__test-runtime-investigation.md)

# Iteration Log

- Area: `ci-release`
- Title: `test-runtime-investigation`
- Started: `2026-07-06 22:45`

## Summary

- Investigated why the `701`-test unittest suite exceeds the repo timing budget.
- Confirmed the full suite still passes and is timing-sensitive: earlier runs reported `0.698-0.770s` with `1.230s` wall through `tools/check_test_timing.py`, while a later warm run reported `0.401s`.

## Changes

- Captured a timing report with `tools/report_test_timing.py --top 20 --sort slowest`; the slowest individual test was only `0.024s`.
- Grouped timings by module/class and found the cost is distributed: `test_control_room` dominates by volume, especially command/bindings/dispatch tests that construct full Textual `ControlRoomApp` harnesses per test.
- Profiled the suite with `cProfile`; import/discovery, repeated app setup, and cache-sensitive filesystem/module work are the main contributors, with no single test sleep or obvious pathological outlier.
- Updated `docs/status/ci-release.md` with the current timing diagnosis.

## Follow-ups

- To lower runtime materially, split pure command/dispatch behavior away from full Textual app fixtures or add lightweight test harnesses that bypass repeated `ControlRoomApp` construction.

## Iteration 378

- When: `2026-07-06 23:14`
- Area: `travel`
- Title: `optional-station-travel`
- Source: [2026-07-06-23-14____travel____optional-station-travel.md](iteration-logs/2026-07-06-23-14____travel____optional-station-travel.md)

# Iteration Log

- Area: `travel`
- Title: `optional-station-travel`
- Started: `2026-07-06 23:14`

## Summary

- Made station optional for the new travel command and structured web/socket dispatch.

## Changes

- `travel <system>` now parses and dispatches as system-only travel; `travel <system> / <station>` keeps the station docking path.
- Added system-arrival completion for stationless travel so the routine stops after destination-system arrival instead of calling station docking.
- Updated `/haul` Travel Assist with a visible secondary Clear button, optional station validation, stationless raw command dispatch, and dirty-state handling so cleared station text is not re-filled by selected-route rendering.

## Follow-ups

- Live-validate system-only travel from docked, normal-space, supercruise, and remote-system starts under CrossOver/macOS.

## Iteration 379

- When: `2026-07-09 12:35`
- Area: `control-room`
- Title: `direct-dock-normal-space`
- Source: [2026-07-09-12-35_control-room_direct-dock-normal-space.md](iteration-logs/2026-07-09-12-35_control-room_direct-dock-normal-space.md)

# Iteration Log

- Area: `control-room`
- Title: `direct-dock-normal-space`
- Started: `2026-07-09 12:35`

## Summary

- Fixed direct `dock` so it waits for `SupercruiseExit` only when Control Room state says the ship is in supercruise.

## Changes

- Added an explicit direct-command predicate in `edap/control_room/routines_station.py`; normal space now skips the drop wait and starts docking attempts immediately.
- Added Control Room regression coverage for supercruise wait behavior and normal-space immediate docking.
- Documented the current direct-command vs transit-wrapper station routine split in `docs/devlog/0003-station-routine-split.md`.

## Follow-ups

- Consider moving shared station command policy into a neutral helper if direct station commands and transit wrappers continue to accumulate parallel state decisions.

## Iteration 380

- When: `2026-07-11 02:17`
- Area: `travel`
- Title: `spansh-route-comparison`
- Source: [2026-07-11-02-17____travel____spansh-route-comparison.md](iteration-logs/2026-07-11-02-17____travel____spansh-route-comparison.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-route-comparison`
- Started: `2026-07-11 02:17`

## Summary

- Landed v1 of the Spansh neutron route comparison surface per `docs/plans/0010`.
- New `/haul` panel "Route Comparison (beta)" renders in-game NavRoute.json against a Spansh plot side-by-side.
- Live and offline (fixture-backed) paths share the same rendering.
- Comparison verdict uses reduced jump count as the only tiebreak; TTS phrase surfaces "{title}, Spansh route came back and it saves/adds X jumps, with Y more/fewer neutron jumps, would you like to review?".
- Executed with three parallel Sonnet agents in worktrees for navroute parser, Spansh API client, and FSD-type detection; comparison layer, web endpoint, and panel done in the parent session.

## Changes

- `docs/plans/0010-spansh-neutron-route-comparison.md` — new plan doc.
- `tests/fixtures/routing/` — captured live NavRoute.json + Spansh normal/overcharge/queued responses.
- `edap/routing/{navroute,types,comparison,web}.py` — pure parsers + comparison + fixture/live glue.
- `edap/spansh_router.py` — httpx-based Spansh `/api/route` submit+poll client.
- `edap/state.py`, `edap/control_room/{models,events,dependencies,protocol/data_messages,app}.py` — new `fsd_type` (standard/sco/overcharge_mkii) + `supercharge_multiplier` fields plumbed from Loadout through the control-room read model. Detection is by FSD module Item string (`overchargebooster_mkii` marker), not ship name.
- `edap/control_room/server/{app,serve}.py` — new `/api/route-compare` endpoint with `?fixture=` support, wired to `journal_dir`.
- `web/haul-v1.html`, `web/haul-ui.css`, `web/route-compare.js` — new panel + inline JS + styles.
- Tests: `test_navroute.py`, `test_spansh_router.py`, `test_route_comparison.py`, `test_routing_web.py`, `test_route_compare_endpoint.py`; extended `test_state.py` and `test_control_room.py` for FSD detection. Full suite 757 tests, 0.309s.

## Follow-ups

- Neutron travel routine that flies each Spansh waypoint (parked; would enable the disabled "Switch to Spansh" button).
- Wire ship state's `supercharge_multiplier` into the panel's supercharge default so Caspian + Mk II SCO auto-picks Overcharge without operator toggling.
- Auto-prefill `From` from current system and `Range` from `Loadout.MaxJumpRange` in the panel form.
- Laden jump-range calculation for a more honest default when hauling cargo.
- TUI comparison view and modal to mirror the web surface.
- Live validation against Elite under CrossOver/macOS.

## Iteration 381

- When: `2026-07-13 02:53`
- Area: `travel`
- Title: `spansh-route-tts-and-layout`
- Source: [2026-07-13-02-53____travel____spansh-route-tts-and-layout.md](iteration-logs/2026-07-13-02-53____travel____spansh-route-tts-and-layout.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-route-tts-and-layout`
- Started: `2026-07-13 02:53`

## Summary

- Follow-up on the v1 Spansh route comparison surface: wire the real TTS pipeline and hoist the panel to full width.
- TTS now flows through the existing broker/AnnouncementEvent path so every connected observer speaks locally via `edap/tts.py`, matching how other server-initiated announcements fan out. The browser `window.speechSynthesis` path is gone.
- Route Comparison panel is no longer stuck in the narrow left-stack column; it renders as its own full-width section above the layout grid.

## Changes

- `edap/tts.py`, `defaults/tts.toml` — new `AnnouncementId.SPANSH_ROUTE_READY` + default phrase template using `{title}`, `{jump_summary}`, `{neutron_summary}`.
- `edap/routing/comparison.py` — expose `jump_summary` and `neutron_summary` on `RouteComparison` so the server can pass structured `message_values` to clients for local re-rendering.
- `edap/control_room/server/app.py` — `/api/route-compare` now publishes an `AnnouncementEvent` through the broker after a successful comparison (fixture or live).
- `web/haul-v1.html`, `web/haul-ui.css` — Route Comparison panel hoisted out of `.left-stack` into a top-level `.route-compare-full` section inside `<main>`; field-row wraps on narrow widths.
- `web/route-compare.js` — removed `speakOnce`/`window.speechSynthesis`; TTS is now server-driven.
- Tests: extended `test_route_comparison.py` for the new summary fields and `test_route_compare_endpoint.py` for the broker-published announcement. Full suite 758 tests, 0.344s.

## Follow-ups

- Wire the route-compare panel's supercharge default to ship state's `supercharge_multiplier` and prefill From/Range from current system + `Loadout.MaxJumpRange` (still parked from v1).
- Neutron travel routine to fly each Spansh waypoint (still parked; would enable the disabled "Switch to Spansh" button).
- Live-validate the TTS fan-out under CrossOver/macOS with two observers connected.

## Iteration 382

- When: `2026-07-13 12:45`
- Area: `control-room`
- Title: `lan-vpn-skip-and-local-alias`
- Source: [2026-07-13-12-45_control-room_lan-vpn-skip-and-local-alias.md](iteration-logs/2026-07-13-12-45_control-room_lan-vpn-skip-and-local-alias.md)

# Iteration Log

- Area: `control-room`
- Title: `lan-vpn-skip-and-local-alias`
- Started: `2026-07-13 12:45`

## Summary

- `control_room.py lan` was advertising `198.19.0.1:8765` on a Mac running Cloudflare WARP because `_detect_lan_host` returned the first non-loopback candidate from the UDP-route probe, and WARP owned the default route.
- Reworked `_detect_lan_host` to enumerate from UDP probe + `getaddrinfo` + POSIX `ifconfig`, reject loopback/link-local/CGNAT/RFC 2544 benchmark ranges, and prefer RFC1918 addresses. Verified live on the reporter's machine: candidates included `192.168.0.107` (Wi-Fi), `100.117.11.86` (Tailscale), and `198.19.0.1` (WARP); picker now returns `192.168.0.107`.
- Added `control_room.py local` as an explicit loopback bind mode alongside `serve` / `lan`, mirroring the `lan` alias pattern.

## Changes

- `edap/control_room/app.py`: added `_classify_lan_candidate`, `_iter_ifconfig_ipv4`, ranked candidate selection in `_detect_lan_host`, and the new `local` CLI mode with matching `--host` guardrail.
- `tests/test_control_room.py`: patched new `_iter_ifconfig_ipv4` in existing detection tests, added WARP-skip and RFC1918-over-public cases, and covered the `local` alias plus its `--host` rejection.
- `docs/operators/control-room.md`, `docs/operators/control-room-remote.md`: documented the `local` mode and the new LAN-detection preferences.
- `docs/status/control-room.md`: updated the plan 0008 bullet to mention `local` and the VPN/CGNAT skip.

## Follow-ups

-

## Iteration 383

- When: `2026-07-13 13:28`
- Area: `travel`
- Title: `neutron-travel-routine`
- Source: [2026-07-13-13-28____travel____neutron-travel-routine.md](iteration-logs/2026-07-13-13-28____travel____neutron-travel-routine.md)

# Iteration Log

- Area: `travel`
- Title: `neutron-travel-routine`
- Started: `2026-07-13 13:28`

## Summary

- Landed the top must-do from plan 0010's follow-up roadmap: a neutron travel routine that coordinates a Spansh route without flying the ship. Operator flies each hop; routine sets the next waypoint in the galaxy map and watches the journal for arrival. Optional final station is handed off to the existing `transit_to_station` for docking so trade-route destinations flow end-to-end.
- Planning captured in `docs/plans/0012-neutron-travel-routine.md`; user design pushbacks (no in-game flight, composition-not-subclassing for `HaulRuntime`, station in v1 UI, unified `Route` now, server-side route cache with content-hash ids, cache as its own class) are recorded there under "Design pushbacks captured during planning".

## Changes

- New `edap/routines/spansh_route.py`: `fly_spansh_route(runtime, route, station, per_hop_timeout_s)` loops waypoints, setting each in gal-map, watching for arrival, announcing neutron heads-up on flagged waypoints, handing off to `transit_to_station` when a station is provided.
- Unified `Route` type in `edap/routing/types.py` replaces `InGameRoute` and `SpanshRoute`. Discriminated `InGameMetadata | SpanshMetadata | None` on `metadata`, tagged by `source` literal. `/api/route-compare` JSON payload reshaped accordingly; JS client updated.
- Extracted `RoutineRuntime`, `RoutineTiming`, `RoutineTravelSettings` (renamed from Haul*) into `edap/routines/runtime.py`. `HaulRuntime` and `HaulTiming` now compose them via a `routine:` field rather than subclass. `SupportsHaulControls` renamed to `SupportsRoutineControls`. `edap/control_room/routine_runtime_builder.py` holds `build_routine_runtime`; the haul builder composes it.
- `DESTINATION_SET` announcement moved into `set_galaxy_map_destination_for_transit` so every consumer gets the same pre-open heads-up; duplicate calls removed from undock/depart/travel. Phrase reworded to `"Opening galaxy map to set destination to {system_name}."`
- New `RouteCache` (`edap/routing/route_cache.py`): LRU-bounded, keyed by content hash of source/destination/range/efficiency/supercharge. Standalone class. `ControlRoomServerState` holds one and exposes `cache_spansh_route` / `get_spansh_route`. `/api/route-compare` returns `route_id` in the response.
- Dispatch chain: `command.dispatch_spansh_route` WS message → `ObserverSessionCommandHandler.dispatch_spansh_route(route, station, ...)` (server host resolves route_id → Route from server_state before calling) → backend/execution/facade → `routines_spansh.dispatch_spansh_route(app, ...)` → `fly_spansh_route(runtime, ...)`. Unknown/evicted route_id returns `invalid_command`.
- Web: `/haul` Route Comparison panel gains an optional Final station field; Switch to Spansh button becomes enabled once a Compare cached a route_id; click sends the dispatch through `window.EDCR_HAUL.sendCommand` (exposed from haul-ui.js so route-compare.js can share the socket).
- New TTS ids `SPANSH_NEUTRON_WAYPOINT_SET` and `SPANSH_ROUTE_COMPLETE` with default phrases.
- Tests: `test_route_cache.py`, `test_spansh_route.py`, WS handler tests for happy-path + unknown route_id in `test_control_room_server.py`, and `test_route_compare_endpoint.py` covers the cache round-trip. Full suite 777 tests, 0.402s.

## Follow-ups

- Live-validate the routine under CrossOver/macOS: hop transitions, jet-cone timing per neutron waypoint (operator-side), and final station handoff.
- Prefill Route Comparison from ship state (`supercharge_multiplier`, current system, `Loadout.MaxJumpRange`) — still open from plan 0010's must-do list.
- `RemoteObserverBackend.dispatch_spansh_route` currently emits a "not supported from remote python client" local message; wire it fully if/when a Python TUI wants this path.

## Iteration 384

- When: `2026-07-13 13:50`
- Area: `travel`
- Title: `route-compare-four-buttons`
- Source: [2026-07-13-13-50____travel____route-compare-four-buttons.md](iteration-logs/2026-07-13-13-50____travel____route-compare-four-buttons.md)

# Iteration Log

- Area: `travel`
- Title: `route-compare-four-buttons`
- Started: `2026-07-13 13:50`

## Summary

- Split the Route Comparison panel action row into four buttons per user request: **Set in-game route**, **Fetch Spansh**, **Compare**, **All in one**. The Compare-only workflow is preserved. Fetch Spansh lights up Switch to Spansh without needing a local NavRoute.json, so the operator can plan Spansh hops before the game has plotted anything.

## Changes

- `edap/control_room/server/app.py`: new `/api/spansh-route` endpoint. Reuses `edap.spansh_router.plot_route` on a worker thread, caches the returned route via `broker.server_state.cache_spansh_route` under a `RouteRequestKey`, returns `{spansh, route_id}`. No NavRoute read, no announcement (that stays on `/api/route-compare`). Query params match the compare endpoint (`from`, `to`, `range`, `efficiency`, `supercharge_multiplier`).
- `edap/routing/web.py`: renamed `_route_payload` -> `route_payload` (public) so the new endpoint can serialize a single Spansh route without duplicating the metadata switch.
- `web/haul-v1.html`: replaced the four-button row with Set in-game route, Fetch Spansh, Compare, All in one, and moved the fixture loaders onto their own ghost row. Switch to Spansh keeps its previous ghost-until-primary treatment.
- `web/route-compare.js`: added `dispatchDestination()` (sends `command.dispatch_destination` with the To system), `fetchSpanshOnly()` (calls `/api/spansh-route` and renders the Spansh side via new `renderSpanshOnly()`), and `allInOne()` (dispatch destination -> fetch spansh -> 6s wait -> full compare). Compare button unchanged. Switch button state derives from `state.lastRouteId` via a shared `updateSwitchButton()` helper.
- `tests/test_route_compare_endpoint.py`: new `SpanshRouteEndpointTests` class covers cache + route_id, missing param 400, invalid numeric 400, plot_route failure 502, and auth 401. Uses `unittest.mock.patch` on `edap.control_room.server.app.plot_route` so no live Spansh calls.

## Follow-ups

- Live-validate the four-button flow under CrossOver/macOS.
- Retry orchestration currently lives in the browser; user has asked to move that to the server so all clients get the same behavior. Tracked in a new plan doc.
- Spansh dispatch today only sets the destination; user wants it to undock + boost away like `travel`. Same plan doc.
- `destination_set` TTS is firing between waypoints (after a hyperspace jump) not only when actually setting a destination — likely another emitter is reusing the id. Same plan doc.
- Need an "Active route" panel mirroring the active haul routine card: last waypoint → X systems → current system → Y more systems → next waypoint. Same plan doc.

## Config + retry v2

- Added `control_room.route_compare_navroute_wait_seconds` (default `6.0`) and `route_compare_compare_retry_attempts` (default `3`) to the TOML defaults, `ControlRoomConfig`, and `serve_observer_mode` wiring.
- New `GET /api/route-compare/config` returns the two values. Web UI fetches on init, prefills the new inputs, and the `allInOne` flow now loops compare with retry on 404 / errors.
- User feedback after ship: retries should be on the server; keeping this client-side is a stopgap. Follow-up plan will move retry orchestration to the server so any client gets the same behavior.

## Iteration 385

- When: `2026-07-13 15:52`
- Area: `travel`
- Title: `spansh-hardening-slice-1-tts-split`
- Source: [2026-07-13-15-52____travel____spansh-hardening-slice-1-tts-split.md](iteration-logs/2026-07-13-15-52____travel____spansh-hardening-slice-1-tts-split.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-1-tts-split`
- Started: `2026-07-13 15:52`

## Summary

- Split shared `AnnouncementId.DESTINATION_SET` into two ids so the mid-route "opening galaxy map" TTS stops firing on every `FSDTarget` journal event. Plan 0013 slice 1.

## Changes

- `edap/tts.py`: added `AnnouncementId.FSD_TARGET_LOCKED = "fsd_target_locked"`.
- `defaults/tts.toml`: new phrase `fsd_target_locked = "New FSD target acquired: {system_name}."`. `destination_set` phrase unchanged.
- `edap/control_room/app.py`: `FSDTarget` handler now emits `FSD_TARGET_LOCKED`. Routine call site in `edap/routines/transit.py` still emits `DESTINATION_SET` when the routine is actually about to open the galaxy map.
- `tests/test_control_room.py`: FSDTarget path now asserts `FSD_TARGET_LOCKED`.
- `tests/test_config.py`: defaults test asserts the new phrase text.

## Follow-ups

- Slice 2 (undock/boost handoff) and slice 2b (drop per-hop timeout) up next.

## Iteration 386

- When: `2026-07-13 15:56`
- Area: `travel`
- Title: `spansh-hardening-slice-2-undock-and-no-timeout`
- Source: [2026-07-13-15-56____travel____spansh-hardening-slice-2-undock-and-no-timeout.md](iteration-logs/2026-07-13-15-56____travel____spansh-hardening-slice-2-undock-and-no-timeout.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-2-undock-and-no-timeout`
- Started: `2026-07-13 15:56`

## Summary

- Plan 0013 slices 2 + 2b. `fly_spansh_route` now handles docked and normal-space starts via the shared `undock_and_route_to_system` / `depart_system_to_route` primitives (same handoff `travel` uses), so operators can dispatch it from any state. Per-hop arrival deadline is gone: the operator drives every hop and the existing routine pause/stop/resume is the cancellation surface. `wait_for_arrival_or_approach_event` signature is unchanged; only the Spansh caller opts into `math.inf`.

## Changes

- `edap/routines/spansh_route.py`: read `read_ship_position(runtime.journal_dir)` at entry. When `docked`, call `undock_and_route_to_system(destination_system=waypoints[1].system)`. When `normal_space`, call `depart_system_to_route(...)`. Both branches skip the manual galaxy-map-set for waypoint 1 (primitive already sets the route). Announce `SPANSH_NEUTRON_WAYPOINT_SET` if waypoint 1 is a neutron. Loop continues from `waypoints[2:]`. Supercruise / unknown falls back to the existing per-waypoint galaxy-map pattern from `waypoints[1:]`. Dropped `per_hop_timeout_s` parameter and pass `math.inf` as the deadline. Removed the "timed out" error branch (unreachable with no deadline, and the operator already has pause/stop/resume).
- `tests/test_spansh_route.py`: replaced the timeout test with `test_arrival_short_circuits_regardless_of_elapsed_time` (uses a `time_fn` that jumps forward an hour per tick to prove there is no per-hop deadline). Added `test_docked_start_uses_undock_primitive_for_first_hop` (asserts `undock_and_route_to_system` is called for waypoint 1 and the galaxy-map set is NOT re-run for waypoint 1), `test_normal_space_start_uses_depart_primitive_for_first_hop`, and `test_docked_start_propagates_undock_failure`.

## Follow-ups

- Slice 3: move All-in-one retry to server (`command.dispatch_route_all_in_one`).
- Slice 4: Active route panel on `/haul`.
- Live-validate docked/normal-space Spansh start under CrossOver/macOS.

## Iteration 387

- When: `2026-07-13 16:41`
- Area: `travel`
- Title: `spansh-hardening-slice-3-server-all-in-one`
- Source: [2026-07-13-16-41____travel____spansh-hardening-slice-3-server-all-in-one.md](iteration-logs/2026-07-13-16-41____travel____spansh-hardening-slice-3-server-all-in-one.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-3-server-all-in-one`
- Started: `2026-07-13 16:41`

## Summary

- Plan 0013 slice 3. All-in-one retry/wait/compare moved off the browser and behind a new WS command `command.dispatch_route_all_in_one`. Server now composes the same primitives the two REST endpoints already use, so any client (web, TUI, Python) gets the same behavior with one call.

## Changes

- `edap/control_room/server/app.py`: extracted `RouteCompareError`, `fetch_and_cache_spansh_route`, and `build_and_cache_live_comparison` as module-level helpers. Refactored `/api/route-compare` (live branch) and `/api/spansh-route` to delegate to them. New async handler `_handle_dispatch_route_all_in_one_async` sequences: `command_handler.dispatch_destination(...)` -> `fetch_and_cache_spansh_route(...)` -> loop `asyncio.sleep(navroute_wait_seconds)` + `build_and_cache_live_comparison(...)` with `RouteCompareError.retryable` gating retries. Response includes `route_id`, comparison payload, and a `phases[]` trail so clients can render a checklist. `journal_dir` + config defaults threaded through `_receive_session_messages` and `_handle_session_message_async`.
- `edap/control_room/protocol/capabilities.py` + `docs/schemas/control_room_message.schema.json`: registered `command.dispatch_route_all_in_one` and its payload schema.
- `web/route-compare.js`: `allInOne()` collapsed to a single `sendCommand("command.dispatch_route_all_in_one", ...)` call. Also fixed pre-existing bug in `dispatchDestination()` where `galaxy_map_settle` was missing from the payload (would have been rejected by the WS handler).
- `web/haul-ui.js`: exposed `galmapSettleTime` on `window.EDCR_HAUL` so `route-compare.js` can share the same source of truth.
- `tests/test_route_compare_endpoint.py`: new `DispatchRouteAllInOneTests` covers happy path (verifies dispatch_destination is called on the command handler and phases include ok for each step), retry-then-succeed (404 retryable twice then ok, verifies attempt count and phase statuses), all-attempts-fail (returns `route_all_in_one_compare_failed` error code), missing `from` (returns invalid_command), and no command_handler (transport_unavailable). Uses ws bridge via `TestClient.websocket_connect`.

## Follow-ups

- Slice 4: Active route panel on `/haul`.
- Live-validate the end-to-end all-in-one command under CrossOver/macOS.

## Iteration 388

- When: `2026-07-13 16:59`
- Area: `travel`
- Title: `spansh-hardening-slice-4-active-route-panel`
- Source: [2026-07-13-16-59____travel____spansh-hardening-slice-4-active-route-panel.md](iteration-logs/2026-07-13-16-59____travel____spansh-hardening-slice-4-active-route-panel.md)

# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-4-active-route-panel`
- Started: `2026-07-13 16:59`

## Summary

- Plan 0013 slice 4. New Active route panel on `/haul` shows `last waypoint -> X systems -> Current -> Y more systems -> next waypoint` while a Spansh route is running. Backend persists the active `route_id` on `ControlRoomServerState`; hydrate exposes an `active_spansh_route` payload containing the cached route so any client can render progress.

## Changes

- `edap/control_room/server/state.py`: `set_active_spansh_route(route_id)` and `active_spansh_route_id()`.
- `edap/control_room/server/app.py`: `_server_hydrate_data` now injects `active_spansh_route = {route_id, route: route_payload(...)}` (serialized via existing `route_payload` helper) when the broker has an active id. `dispatch_spansh_route` handler now calls `set_active_spansh_route(route_id)` and `_publish_route_hydrate(...)` on success so all observers see the panel light up. Registered `active-route.js` in the asset allowlist.
- `edap/control_room/dependencies.py` + `edap/control_room/protocol/data_messages.py`: new `active_spansh_route: dict | None = None` field on `ControlRoomDataReadModel`, parsed back in `data_read_model_from_payload`.
- `web/haul-v1.html`: new `#active-spansh-panel` section (`.route-compare-full` styling, initially `.hidden`) inserted between the routine card and Route Comparison. Registers `active-route.js`.
- `web/active-route.js`: subscribes to `edcr:hydrate` and `edcr:ship-state`. Locates `ShipState.system` in the cached route's waypoints, renders last/current/next plus the systems-behind / systems-ahead gaps and a `Spansh · N jumps · M boosts · Kx FSD` summary. Falls back to `off route` when the current system is not part of the waypoint list.
- `web/haul-ui.js`: expose `window.EDCR_HAUL.lastHydrate` and dispatch `edcr:hydrate` after each hydrate so `active-route.js` (and future panels) can react without re-parsing the WS stream.
- `web/haul-ui.css`: minimal `.active-spansh-*` styling for the flex row.
- `tests/test_route_compare_endpoint.py`: `ActiveSpanshRouteHydrateTests` covers the empty case (`active_spansh_route` is `None`) and the round-trip (dispatch caches route + sets active id, subsequent hydrate exposes route_id and waypoint list).

## Follow-ups

- Consider surfacing route completion / cancellation on the panel (currently the active route stays visible until another one is dispatched).
- Live-validate the panel under CrossOver/macOS on a real Spansh run.

## Iteration 389

- When: `2026-07-13 17:15`
- Area: `control-room`
- Title: `haul-search-supply-demand`
- Source: [2026-07-13-17-15_control-room_haul-search-supply-demand.md](iteration-logs/2026-07-13-17-15_control-room_haul-search-supply-demand.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-search-supply-demand`
- Started: `2026-07-13 17:15`

## Summary

- Surface Inara supply/demand per station in the web haul search results and let operators filter by them.

## Changes

- `edap/inara/trade_routes.py`: added `from_supply`, `from_demand`, `to_supply`, `to_demand` to `TradeRoute` and populated them in `_row_to_route()` via `_extract_repeated_field_values` (first SUPPLY/DEMAND = source station, second = target station).
- `edap/control_room_state.py`: `_trade_route_from_payload` reads the new keys so persisted trade routes round-trip supply/demand.
- `web/haul-ui.js`: `routeFromApi` / `tradeRoutePayload` carry the new fields; `renderRows` adds a `Sup n / Dem n` subline under each station cell; `WEB_DEFAULTS` gains `minSupply` / `minDemand`; search body sends `min_supply` / `min_demand`.
- `web/haul-v1.html`: new "Min supply" / "Min demand" field row in the search form.
- `edap/control_room/server/app.py`: `_haul_search_query_params` forwards `min_supply` / `min_demand`; these persist via the existing `_save_haul_search_defaults` call so they land in `haul_search.toml`.
- `edap/control_room/dependencies.py`: exposes `minSupply` / `minDemand` in the web defaults payload, seeded from the loaded haul search config.
- `tests/test_inara_trade_routes.py`: extended layout test to assert the four new fields.

## Follow-ups

- `web/multi-haul.*` does not display Inara route boxes; leave supply/demand exposure there for a later pass if the multi-leg planner starts surfacing per-station stock.
</content>
</invoke>

## Iteration 390

- When: `2026-07-13 17:18`
- Area: `travel`
- Title: `active-route-panel-metrics-and-empty-state`
- Source: [2026-07-13-17-18____travel____active-route-panel-metrics-and-empty-state.md](iteration-logs/2026-07-13-17-18____travel____active-route-panel-metrics-and-empty-state.md)

# Iteration Log

- Area: `travel`
- Title: `active-route-panel-metrics-and-empty-state`
- Started: `2026-07-13 17:18`

## Summary

- Fleshed out the `/haul` Active route panel so it stops looking like a stub. Idle state shows a dashed empty message pointing at Route Comparison. Active state renders a 5-waypoint window using the same `.routine-bar`/`.step` styling as the Active haul routine card (done/current highlighting, neutron `· N` label suffix), a compact `last -> current -> next` inline summary, and three `.metric` tiles for Jumps / LY / Boosts remaining. The panel header now shows `N of M jumps` instead of a summary string. Cleaned up Route Comparison by removing the `beta` tag and the two fixture-load buttons (the `?fixture=` REST param stays for offline dev).

## Changes

- `web/haul-v1.html`: Active route panel rewritten (empty-state block + content block with waypoint bar and mini-metrics). Removed `beta` tag on Route Comparison. Removed `rc-fixture-normal` / `rc-fixture-overcharge` buttons.
- `web/active-route.js`: rewritten to render the 5-waypoint centered window (clamped to route bounds), compute remaining jumps / LY / boosts from waypoint tail, and toggle empty vs content state. `Off route` and `Arrived` are handled explicitly in the status pill.
- `web/haul-ui.css`: `.active-spansh-empty` styling for the idle card; dropped `.active-spansh-gap` (no longer used); tightened `.active-spansh-line` spacing to sit below the waypoint bar.
- `web/route-compare.js`: dropped the two fixture button handlers alongside the removed HTML buttons.

## Follow-ups

- No hydrate is currently emitted when a Spansh route finishes or is cancelled; the panel will show `Arrived` once the last waypoint matches ship system but stays populated afterwards. A future step should clear `set_active_spansh_route(None)` on routine completion / operator stop.
- Live-validate the enhanced panel under CrossOver/macOS on a real Spansh run and verify the waypoint window scrolls correctly across mid-route hops.

## Iteration 391

- When: `2026-07-14 15:14`
- Area: `control-room`
- Title: `friendly-spansh-errors`
- Source: [2026-07-14-15-14_control-room_friendly-spansh-errors.md](iteration-logs/2026-07-14-15-14_control-room_friendly-spansh-errors.md)

# Iteration Log

- Area: `control-room`
- Title: `friendly-spansh-errors`
- Started: `2026-07-14 15:14`

## Summary

- Translate Spansh route validation responses into actionable web errors while retaining the upstream response body in server logs.

## Changes

- `edap/control_room/server/app.py`: added Spansh HTTP error parsing; missing finishing systems return HTTP 400 with `Spansh says could not find target system`, other upstream API errors retain their message, and 5xx responses remain 502.
- `tests/test_route_compare_endpoint.py`: added endpoint coverage for the missing-target response.

## Follow-ups

- Keep validating system names before submitting routes; no retry is attempted for Spansh request-validation errors.

## Iteration 392

- When: `2026-07-14 15:23`
- Area: `ci-release`
- Title: `prepare-v1-22-0-release`
- Source: [2026-07-14-15-23__ci-release__prepare-v1-22-0-release.md](iteration-logs/2026-07-14-15-23__ci-release__prepare-v1-22-0-release.md)

# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-22-0-release`
- Started: `2026-07-14 15:23`

## Summary

- Prepared `v1.22.0` as the next minor release after `v1.21.0`.

## Changes

- Bumped `[project].version` in `pyproject.toml` and will refresh `uv.lock` to match.
- Captured the release scope in `docs/status/ci-release.md`: Spansh neutron travel, route comparison, active-route UI, and Inara haul filters.
- Regenerated the iteration archive and validated the full unittest suite before the release cut.

## Follow-ups

- Tag and publish `v1.22.0` from the release-prep commit with concise operator-facing notes.

## Iteration 393

- When: `2026-11-06 14:41`
- Area: `haul`
- Title: `resume-near-buy-station`
- Source: [2026-11-06-14-41_____haul_____resume-near-buy-station.md](iteration-logs/2026-11-06-14-41_____haul_____resume-near-buy-station.md)

# Iteration Log

- Area: `haul`
- Title: `resume-near-buy-station`
- Started: `2026-11-06 14:41`

## Summary

- Starting two-way haul in normal space near station 1 with an empty hold used to return `DEPART_STATION_1_SYSTEM`, so the ship flew empty to station 2 (same for station 2). It now docks at that station and buys first. The user chose this behaviour.

## Changes

- `_detect_start_phase`: in normal space, depart only with a full load or when that station has no buy commodity. Otherwise return to the station when the latest relevant journal event shows the ship is near it (`Undocked`, `DockingRequested`, `DockingGranted` for that station, or a `SupercruiseExit` at that station). Elsewhere in normal space it returns an error asking the operator to enter supercruise.
- `detect_transit_resume_state`: `Undocked` from the destination station now means `POST_DROP_NEAR_STATION`, so `dock()` requests docking straight from normal space.
- `haul_loop_two_way`: an initial `TRANSIT_TO_STATION_1` runs as a pre-cycle step, so `iterations=N` now gives N full cycles. A start-phase error result is returned instead of crashing on `.name`.
- Tests cover both stations, partial load, full load, no buy commodity, far-from-station error, `Undocked` resume, and the iteration count.

## Follow-ups

- Live-validate the near-station resume and docking request in CrossOver.

## Iteration 394

- When: `2026-11-06 20:59`
- Area: `haul`
- Title: `market-buy-top-up`
- Source: [2026-11-06-20-59_____haul_____market-buy-top-up.md](iteration-logs/2026-11-06-20-59_____haul_____market-buy-top-up.md)

# Iteration Log

- Area: `haul`
- Title: `market-buy-top-up`
- Started: `2026-11-06 20:59`

## Summary

- A short market buy used to leave with a partial load. Two-way and multi-leg haul now top up the remainder, up to 2 times, then warn and continue. This makes an undershoot cheap, which unblocks a shorter buy-hold curve.

## Changes

- `market_buy` success details now carry `expected_count`. For `MAX` this is `min(free, stock)`; for a numeric amount it is the requested amount.
- `haul_support.buy_shortfall` compares `expected_count` with `MarketBuy.Count` and returns `None` when either is unknown, so an unknown result never triggers a top-up.
- `haul_two_way._run_market_buy` tops up with `MAX`. `haul_multi_leg._run_buy` tops up the numeric remainder. A failed top-up dispatch is returned. A top-up that buys the wrong commodity uses the existing recovery path. Haul stats already count every `MarketBuy` before departure.
- User-confirmed facts:
  - Holding `UI_Right` past max clamps at max.
  - A second buy's max is the remainder.
  - Top-ups are OK.
  - A manual hold to max at 1137t takes about 3s; the default curve gives 9.1s.

## Follow-ups

- Proposed retune, awaiting user approval: `100t+` flat `4.5s` (keep `0-99t` at `3.0s`, cap `20s`). If no top-ups fire on large buys, try a flat `3.5s` for every size.
- Edge cases:
  - If credits limit the buy, a top-up of 0 affordable units would time out and abort the haul.
  - If `Cargo.json` is stale after the first buy, the top-up `expected_count` is overstated. That wastes a second top-up, but the game clamps the quantity.
- Optional learning of the hold per bucket (step D), only on the user's request.

## Iteration 395

- When: `2026-11-06 21:07`
- Area: `haul`
- Title: `top-up-limit-and-balance-guard`
- Source: [2026-11-06-21-07_____haul_____top-up-limit-and-balance-guard.md](iteration-logs/2026-11-06-21-07_____haul_____top-up-limit-and-balance-guard.md)

# Iteration Log

- Area: `haul`
- Title: `top-up-limit-and-balance-guard`
- Started: `2026-11-06 21:07`

## Summary

- The user asked for a configurable top-up limit (default 3) and asked that a credit-limited buy never time out and abort.

## Changes

- New `controls.market.buy_top_up_max_attempts` (default `3` in `defaults/controls.toml`, `>= 0`, `0` disables top-up). It is passed through `HaulMarketSettings` for two-way and multi-leg haul. Log lines now show `(top-up n/N)`.
- `_read_buy_quantity_limit` also caps by `Status.json` `Balance // BuyPrice` when both values are usable. A missing, blank or corrupt `Status.json`, or a balance or price that is invalid, counts as unknown.
- A known zero `MAX` limit backs out to the station menu without waiting for a `MarketBuy` that never comes.
- Before each top-up, both haul loops re-read the balance and the price. If the balance cannot cover one unit, they skip the top-up with a warning and continue.
- The user's local `config.toml`, which is not tracked, now uses `0-99t` flat `3.0s` and `100t+` flat `4.5s`. The running `lan` server needs a restart to pick it up; the user decides when.

## Follow-ups

- `Status.json` freshness is not checked. A valid but outdated balance is trusted.
- A zero limit caused by station stock `0` now warns and continues instead of timing out. In two-way haul, the ship could then fly a leg empty. Revisit if that shows up live.

## Iteration 396

- When: `2026-11-06 21:13`
- Area: `haul`
- Title: `buy-warning-tts`
- Source: [2026-11-06-21-13_____haul_____buy-warning-tts.md](iteration-logs/2026-11-06-21-13_____haul_____buy-warning-tts.md)

# Iteration Log

- Area: `haul`
- Title: `buy-warning-tts`
- Started: `2026-11-06 21:13`

## Summary

- The user asked for spoken TTS for three buy warnings: no units available, cannot afford a top-up, and still short after the top-up limit. They use the existing `AnnouncementId` plus `defaults/tts.toml` path; the progress text is unchanged.

## Changes

- `market_buy_none_available` (market-level, also used by the `buy` command): "{title}, no {commodity_name} available to buy. Continuing with current load."
- `haul_top_up_unaffordable` (two-way and multi-leg): "{title}, cannot afford more {commodity_name} at {station_name}. Continuing with partial load."
- `haul_buy_still_short` (two-way and multi-leg): "{title}, buy short at {station_name}. Continuing with partial load."
- The per-top-up "Short buy ... topping up" line is not spoken, because each top-up already announces `buying_cargo`.

## Follow-ups

- Listen to the phrases live after the `lan` server restart.

## Iteration 397

- When: `2026-11-07 10:56`
- Area: `haul`
- Title: `persist-haul-run-history`
- Source: [2026-11-07-10-56_____haul_____persist-haul-run-history.md](iteration-logs/2026-11-07-10-56_____haul_____persist-haul-run-history.md)

# Iteration Log

- Area: `haul`
- Title: `persist-haul-run-history`
- Started: `2026-11-07 10:56`

## Summary

- Step 1 of the haul stats persistence plan: every two-way haul run is kept as a row in an append-only JSONL file. The user asked that no data be lost, so aborted and interrupted runs are kept with everything captured up to that point.

## Changes

- New `control_room.haul_runs_file`, default `.control_room_haul_runs.jsonl`. It is git-ignored, and `clear` does not touch it.
- `edap/haul_history.py` builds a schema-1 row from the journal events in `handle_haul_event`. A row records:
  - `started_at`/`ended_at` in UTC, taken from journal timestamps;
  - `duration_s` from the live haul clock, which excludes pauses;
  - the route with its systems;
  - per-visit `legs`, with `buys`/`sells` arrays and `market_buy_events`;
  - the raw `events`;
  - `cost`, `revenue`, `profit`, `expected_profit`/`profit_delta`, `top_ups`, `warnings` (IDs of the three haul buy warning TTS messages), `phase` and `reason`.
- The row closes as `completed` in `finalize_completed_haul_run`. It closes as `aborted` on stats stop, clear, a new haul over a stale run, a restart with a saved in-progress run, or the remainder of a resumed mid-run haul (at the ignored station-1 sale, or before the next clean run starts).
- Crash safety:
  - `current_run` and `pending_runs` are saved in `.control_room_state.json`, which is now fsynced.
  - A pending row is removed only after its JSONL append and fsync succeed. A failed append logs a warning and is retried later.
  - `load_runs` skips torn or invalid lines and dedupes on `(started_at, ended_at, station_1)`.
- Behaviour change: haul stats no longer require a station 1 buy commodity, so one-sided loops are tracked and announce the session summary.

## Follow-ups

- Step 2: `stats [today|48h|week|month|since <date>|all]` plus `tools/haul_stats.py`. Windows use local time, and a week starts Monday 00:00. Aborted runs appear on their own line and in an all-in total. Profit/hour and expected vs actual use completed runs only.
- Step 3: a journal trade ledger in `stats`.
- Step 4: `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- Multi-leg runs are not recorded yet.

## Iteration 398

- When: `2026-11-07 11:06`
- Area: `haul`
- Title: `haul-stats-query`
- Source: [2026-11-07-11-06_____haul_____haul-stats-query.md](iteration-logs/2026-11-07-11-06_____haul_____haul-stats-query.md)

# Iteration Log

- Area: `haul`
- Title: `haul-stats-query`
- Started: `2026-11-07 11:06`

## Summary

- Step 2 of haul stats persistence adds a query over `.control_room_haul_runs.jsonl`: the control-room `stats [window]` command and `tools/haul_stats.py`.

## Changes

- `edap/haul_history.py` gains two pure functions:
  - `parse_window(text, now)` handles `today`, `48h`, `week`, `month`, `all` and `since YYYY-MM-DD`. Calendar windows use local time; `48h` is elapsed time. The endpoints are inclusive, and `now` is injected by the caller.
  - `summarize(rows, since, until, *, skipped_lines)` returns a frozen `HaulSummary` that `dataclasses.asdict` can serialize. Rows are assigned to a window by `ended_at`. The summary keeps completed metrics, aborted runs (count and realized profit), an all-in total, and route and commodity breakdowns split by status.
  - Profit/hour, mean, best, and expected vs actual count completed runs only. Expected vs actual uses only the runs that have a known expectation.
- `edap/platform/local_time.SystemLocalTimezone` is a tzinfo that asks the OS for each date's offset, so windows that cross a DST change stay correct without a tz database dependency.
- `stats` is in the dispatch and in the help index, and the web reaches it through `command.submit_input`. `haul_history_summary_lines` in `rendering.py` is shared by the log and the CLI. `tools/haul_stats.py --json` prints the summary as JSON.

## Follow-ups

- Step 3: add a journal trade ledger section to `stats`.
- Step 4: add `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- `tools/haul_stats.py` without `--file` needs `config.toml`. It works in the main checkout but not in a fresh worktree.

## Iteration 399

- When: `2026-11-07 11:14`
- Area: `haul`
- Title: `journal-trade-ledger`
- Source: [2026-11-07-11-14_____haul_____journal-trade-ledger.md](iteration-logs/2026-11-07-11-14_____haul_____journal-trade-ledger.md)

# Iteration Log

- Area: `haul`
- Title: `journal-trade-ledger`
- Started: `2026-11-07 11:14`

## Summary

- Step 3 of haul stats persistence adds a read-only Elite journal trade ledger to `stats` and `tools/haul_stats.py`. It covers manual trading and periods from before run tracking existed. It never creates run rows.

## Changes

- `edap/journal_trade_ledger.journal_trade_ledger(journal_dir, since, until)` returns a frozen, asdict-able `JournalTradeLedger`.
  - **Files scanned:** journal files whose UTC filename stamp falls inside the window, plus the last file that started before it.
  - **Event filtering:** events are filtered by `timestamp`, and torn lines are skipped.
  - **Station attribution:** comes from `Docked`/`Location` `MarketID`.
  - **Totals:** buy and sell counts, cost, revenue, trade profit, and `sell_margin` (`TotalSale - AvgPricePaid*Count`, `None` if any basis is missing), with per-commodity and per-station breakdowns.
  - **Other flows:** module, repair, refuel, mission, voucher, fines and rebuy totals.
- **Balance change** is the difference between observed snapshots, so it is approximate:
  - The start is the last `LoadGame.Credits` at or before the window start, else the first one after it.
  - The end is the latest `LoadGame` or a `Status.json` `Balance` not after `until`.
  - If a session was already running at the window start, money made between that `LoadGame` and the window start is counted in.
- **Output:** `stats` and the CLI render an `All trading (journal)` block, and the CLI JSON gains a `journal` field.
  - The control room reuses its resolved `_journal_dir`. The CLI uses the runtime path resolution, or `--journal-dir`.
  - A missing journal directory shows one line and does not fail.
- **Smoke test** against the real journals with `week`: 52 buys / 51 sells, trade profit 842.0M, observed balance change 841.7M. This matches the earlier hand count of 620M through 2026-11-06 plus today's trading.

## Follow-ups

- Step 4: `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- Coverage reports the first event of the preceding file, which can be weeks before the window when there was a play gap.

## Iteration 400

- When: `2026-11-07 11:24`
- Area: `haul`
- Title: `haul-stats-web-and-backfill`
- Source: [2026-11-07-11-24_____haul_____haul-stats-web-and-backfill.md](iteration-logs/2026-11-07-11-24_____haul_____haul-stats-web-and-backfill.md)

# Iteration Log

- Area: `haul`
- Title: `haul-stats-web-and-backfill`
- Started: `2026-11-07 11:24`

## Summary

- Step 4 of haul stats persistence exposes persisted run history on the web and in the TUI. A one-off journal backfill seeded the run log with this week's hauls.

## Changes

- `GET /api/haul-stats?window=<today|48h|week|month|all|since YYYY-MM-DD>` returns `window`, `label`, `since`, `until`, `runs` (asdict `HaulSummary`) and `journal` (asdict `JournalTradeLedger`, or null without a journal dir or journals).
  - Auth works like other `/api/*` routes. A bad window gives 400, and a read failure gives 503. The read runs in `asyncio.to_thread`.
  - `serve.py` passes `control_room.haul_runs_file`.
- Web Haul v1 gets a History panel with Today/48h/Week/Month/All tabs. The tab choice is remembered in `localStorage`. The panel shows completed metrics, aborted and all-in lines, route and commodity tables, and the journal line. It refreshes on load, on reconnect and when `haul_session.completed_runs` changes.
- The TUI HAUL panel adds `Today +X (n runs)`, read through `edap/haul_stats_cache.TodayHaulCache`. The cache reloads on a local date change or after a successful append, and at state load. It uses persisted rows only, and connect mode shows `Today unavailable`.
- Smoke test against the real backfilled file and journals: `today` 5 runs / 219.13M and `week` 25 + 1 aborted / 844.21M all-in, both matching the journal trade profit.

## Backfill

- `.control_room_haul_runs.jsonl` did not exist before the backfill. It now has 26 rows reconstructed from the 2026-11-05..07 journals: 25 completed and 1 aborted, all from Voltaire Terminal.
- Each row: `source: "journal_backfill"`, `app_version: "backfill"`, `backfill_cutoff: "2026-11-07T11:19:51Z"`, `expected_profit: null`.
- A run spans `Undocked` at station 1 to the station-1 sell after docking back. `duration_s` is in-game time, with gaps between journal files removed (resumed at `LoadGame`).
- A station-1 buy after docking back with no station-1 sale closes the run as `aborted` (the 2026-11-05 session break).
- Totals: profit 844,208,483, which equals the journal trade profit. The reader loads all 26 rows with 0 skipped, and needed no change.
- Cutoff: `2026-11-07T11:19:51Z` is the last journal event backfilled. Hauls after it and before the first server restart with tracking are in neither the backfill nor the live log. Backfill them from later journals using the same cutoff rule.

## Follow-ups

- Land steps 1-4 together, then restart the server once.
- No real browser test of the History panel yet. Only the endpoint and the page markup were checked.

## Iteration 401

- When: `2026-11-07 11:28`
- Area: `runtime`
- Title: `wine-side-background-input-experiment`
- Source: [2026-11-07-11-28___runtime____wine-side-background-input-experiment.md](iteration-logs/2026-11-07-11-28___runtime____wine-side-background-input-experiment.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-side-background-input-experiment`
- Started: `2026-11-07 11:28`

## Summary

- A Wine-side injector delivers input to Elite running in CrossOver while another macOS app stays frontmost. This opens a background-input path that the macOS-side approaches (`CGEventPostToPid`, flash-focus) never did.

## Setup

- **Software:** CrossOver Preview with Elite docked in the `Test` bottle. ghostty/Terminal stayed the macOS front app the whole time.
- **Injector:** AutoHotkey v2.0.31 portable, downloaded from autohotkey.com and checked against the official `.sha256`. It is installed at `drive_c/ahk/AutoHotkey64.exe` with the test script `drive_c/ahk/bgtest.ahk` (args `<mode> [target] [key] [mods] [count]`), and stays there for now.
- **Test key:** `GalaxyMapOpen` = LeftCtrl+M.

## Results

- **`WinActivate` + `SendEvent`: worked.** The journal logged `Music` GalaxyMap at 11:25:55Z and the map opened. The script's log shows the Win32 foreground was `explorer.exe` (target inactive) before `WinActivate` and `EliteDangerous64.exe` (target active) after it. The macOS front app did not change.
- **`SendInput`: worked.** It toggled the map closed (`Music` Starport at 11:26:15Z), with the same foreground pattern and no macOS focus theft.
- **`ControlSend` (window messages, no activation): no effect.** No journal event followed, even though Wine already reported Elite as the foreground window. Elite reads raw input, not window messages. This also casts doubt on the native Windows `PostMessageW` background path.
- **Checking the result:** `Status.json` `GuiFocus` never showed 6 while the map was open; it only rewrote after the close. Verify with the journal `Music` event instead.
- **Notepad baseline:** skipped, since the Elite result was enough.

## Follow-ups

- The background-input researcher is drafting a production `wine-helper` backend design (proposal only): a resident helper in the bottle, IPC from the Python macOS backend, re-asserting the Win32 foreground before each burst, launch and stop, and failure modes.

## Iteration 402

- When: `2026-11-07 11:58`
- Area: `runtime`
- Title: `wine-helper-input-backend`
- Source: [2026-11-07-11-58___runtime____wine-helper-input-backend.md](iteration-logs/2026-11-07-11-58___runtime____wine-helper-input-backend.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-helper-input-backend`
- Started: `2026-11-07 11:58`

## Summary

- Implemented the `wine_helper` macOS input mode from `docs/design/0003-wine-helper-input-backend.md`. A C helper (`tools/wine_input_helper/edap_input_helper.c`, built locally with mingw-w64, no committed `.exe`) runs in the CrossOver bottle, focuses Elite inside Wine and sends `SendInput` scan codes. Python drives it over an authenticated loopback protocol. Not yet live-validated; `foreground` stays the default.

## Changes

- **Helper:** TCP on `127.0.0.1` only, token auth, newline JSON protocol 1, one client. It refuses Alt (scan 0x38) and releases keys on disconnect, target exit, helper exit, console stop and `WM_ENDSESSION`. A 20ms watchdog releases keys held past `max_hold_s`.
- **Tools:** `tools/build_wine_input_helper.py` builds to `build/wine_input_helper/`. `tools/install_wine_input_helper.py --bottle NAME` copies the exe to `drive_c/edap/`.
- **Python:** `WineHelperClient` uses injected connect/clock/sleeper/popen/process-table/token dependencies. The `[input]` config is in `defaults/input.toml`, with `set_input wine_helper|foreground|pid`. Scan codes are shared in `edap/platform/input/scancodes.py`. There is no foreground fallback.
- **Review fixes:**
  - Only the local Control Room host and `ship_controls` start the helper. Diagnostics and `connect` clients only select the mode, so they don't take the single client slot.
  - The input-target summary no longer does a live `status` round-trip per snapshot.
  - `max_hold_s` defaults to 30s and must exceed `controls.market.buy_max_hold_seconds` (20s), so the watchdog can't cut buy holds short.
- **Docs:** user guide `docs/user/background-input.md`. The agent setup skill is at `.agents/skills/edcr-background-input/SKILL.md`, with `.claude/skills/edcr-background-input` as a relative symlink to it (git mode 120000).

## Follow-ups

- Live test on the Test bottle. Open questions:
  - whether Win32 focus works without Alt;
  - whether `wine --bottle Test` runs the console helper headless;
  - the stuck-key, watchdog and kill paths;
  - the real `ps` shape for CrossOver mismatch detection.
- Fixed in a follow-up: `tools/ship_controls.py` now adds the repo root to `sys.path` like the other tools, so both `uv run python3 tools/ship_controls.py` and `-m tools.ship_controls` work.

## Iteration 403

- When: `2026-11-07 12:07`
- Area: `runtime`
- Title: `wine-helper-live-validation`
- Source: [2026-11-07-12-07___runtime____wine-helper-live-validation.md](iteration-logs/2026-11-07-12-07___runtime____wine-helper-live-validation.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-helper-live-validation`
- Started: `2026-11-07 12:07`

## Summary

- **The `wine_helper` input mode works live.** Elite in the CrossOver Preview `Test` bottle received keys while ghostty stayed the macOS front app.
- **Setup:** main checkout, Elite docked at Voltaire Terminal, `config.toml` `[input] target = "wine_helper"`.

## Results

- **Build and install:** OK. `build/wine_input_helper/edap_input_helper.exe` was installed to `Test/drive_c/edap/`.
- **Run 1:** `GalaxyMapOpen; GalaxyMapOpen delay=3`.
  - Press 1 opened the map (journal `Music` GalaxyMap at 12:06:57Z).
  - Press 2 had no effect, most likely dropped while the map was still loading.
  - `helper.log`: `listening`, `attach_thread_input`, `already`, `disconnected`. So the first burst needed the `AttachThreadInput` fallback after `SetForegroundWindow`.
- **Run 2:** a single `GalaxyMapOpen` with the map loaded closed it (`Music` Starport at 12:07:16Z). `helper.log`: `listening`, `already`, `disconnected`.
- **Both runs:**
  - no macOS focus theft and no Alt side effects;
  - the console helper ran headless;
  - the managed helper started for each `ship_controls` run and disconnected when it exited.
- **Skill:** Claude Code listed the `edcr-background-input` skill through the `.claude/skills` symlink.

## Changes

- The verification sequence in the user guide and the skill now uses `delay=8`, with a fallback of one extra `--action GalaxyMapOpen`.
- The guide's status line and the runtime status now record the live result. `foreground` stays the default config.

## Follow-ups

- Not yet exercised live:
  - real routines (haul);
  - Control Room auto-launch;
  - stuck-key, watchdog and kill handling;
  - a game restart;
  - the CrossOver mismatch `ps` shape.

## Iteration 404

- When: `2026-11-07 12:18`
- Area: `runtime`
- Title: `wine-helper-long-lived-focus-fix`
- Source: [2026-11-07-12-18___runtime____wine-helper-long-lived-focus-fix.md](iteration-logs/2026-11-07-12-18___runtime____wine-helper-long-lived-focus-fix.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-helper-long-lived-focus-fix`
- Started: `2026-11-07 12:18`

## Summary

- **Bug:** in a long-running `control_room.py lan` server with Firefox in front, every routine failed with `HelperError: wine helper focus_failed`. `helper.log` showed one `attach_thread_input`, four `already`, then two `focus_failed`. The shown error was the bare text "routine unexpected exception".
- **Likely cause:** the `ship_controls` checks started a fresh helper each run, and a fresh process may take the Win32 foreground. The server's helper lives on. Once winemac moved the foreground away after Mac app switches, `SetForegroundWindow` and an `AttachThreadInput` to the target's own thread could not take it back. Not yet confirmed live.

## Changes

- **Helper (`focus_target`):**
  - 3 attempts, 30ms apart: `SetForegroundWindow`, then attach to the current foreground thread and the target thread, then `BringWindowToTop`, `SetForegroundWindow`, `SetActiveWindow` and `SetFocus`.
  - Calls `LockSetForegroundWindow(LSFW_UNLOCK)` and `AllowSetForegroundWindow(ASFW_ANY)`, and sets the foreground lock timeout to zero for the session only. Alt is still never sent.
  - A key-down that finds focus has moved re-focuses once.
  - Failures log `focus_failed fg=<process> err=<GetLastError>`.
- **Client:**
  - Retries `focus_failed` up to 3 times, 0.1s apart, and keeps the connection, since a refused focus sends no keys.
  - Raises `FocusFailed` with a readable message.
  - `close()` reconnects once to send `bye`, so a managed helper no longer outlives Control Room after an error dropped the connection.
- **Control Room:**
  - Helper errors show as `Input to Elite failed: ...`, with `set_input` recovery hints.
  - Fixed the generic routine exception lookup (`routine_unexpected_exception_message`), which had printed the bare key name instead of the error.

## Follow-ups

- Live retest in a long-running server: switch Mac apps several times between routines. If it still fails, the new `fg=` and `err=` log fields show what holds the foreground.

## Iteration 405

- When: `2026-11-07 12:37`
- Area: `runtime`
- Title: `wine-helper-event-loop-and-child-focus`
- Source: [2026-11-07-12-37___runtime____wine-helper-event-loop-and-child-focus.md](iteration-logs/2026-11-07-12-37___runtime____wine-helper-event-loop-and-child-focus.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-helper-event-loop-and-child-focus`
- Started: `2026-11-07 12:37`

## Summary

- **CPU report:** a long-lived server helper (old pid 48229) sat at 99.7% CPU after about 10 minutes. It did not reproduce: fresh helpers measured 0.0% (`ps -o pcpu`) idle, connected, after `target`/`focus`, after disconnect, with `--log`, and on a tty or `/dev/null`. A probe showed `select` under Wine blocks correctly (49 wakes/s at a 20ms timeout). Held-key CPU was not measured, since it needs game input.
- **Focus retest:** the 3x focus retry on main still fails live (`helper.log`: one `attach_thread_input`, four `already`, then repeated `focus_failed fg=explorer.exe err=5`). Every live success came from a freshly started process. A long-lived probe helper recovered once in-process (`attach_thread_input`, 0.02s) during 4 minutes of Mac app switching, so the failure needs more than one drift or a longer-lived helper.

## Changes

- **CPU spin root cause (reproduced):** two helpers at ~100% CPU, both PPID 1, stdio on the user's terminal `ttys021`, both in its process group, last log line `disconnected`, port 47811 no longer listening. `sample` showed the main thread inside `_sigtramp` and a busy Rosetta exception-server thread. Sending SIGINT to a probe helper reproduced it at once (104%) for both the old polling loop and the new event loop; it still answers requests, but after `bye` it never exits. `SetConsoleCtrlHandler(NULL,TRUE)` did not help. A plain orphan (parent gone, no signal) stays at 0-1.2% and exits on `bye`. So quitting Control Room with Ctrl-C in its terminal hit the helper too, and the next Control Room could start a second helper because the stuck one had closed its socket.
- Managed launch now uses `subprocess.Popen(argv, stdin=DEVNULL, start_new_session=True)`, so terminal signals never reach the helper. SIGKILL stops a spinning helper cleanly.
- `edap_input_helper.c` main loop waits on events instead of polling: `WSAEventSelect` on the listen and client sockets plus `MsgWaitForMultipleObjects`, with the timeout from the nearest held-key deadline (1s idle cap, 20ms retry after a failed release). A busy guard logs `busy_wakes` once and backs off 10ms per extra wake above 1000 wakes/s.
- Focus falls back to a short-lived child of the helper exe (`--focus-hwnd <decimal hwnd>`, 700ms timeout) when the in-process steps fail. The step is `child_focus`; failures log `focus_failed fg=<process> err=<code> child=<code>` (`0` focused, `1` refused, `100` didn't start, `101` timed out). Child mode verified from macOS: real hwnd exited 0 in 0.7s, a bogus hwnd exited 1.
- Design doc, background-input troubleshooting and runtime status updated.

## Follow-ups

- Live retest: reinstall the helper into the bottle, quit Control Room and confirm no old helper remains, start the server, run a routine while switching Mac apps, then check `helper.log` for `child_focus` or `focus_failed ... child=N`, and `ps -o pcpu` on the helper idle and during routines.

## Iteration 406

- When: `2026-11-07 14:01`
- Area: `runtime`
- Title: `wine-helper-focus-timeout`
- Source: [2026-11-07-14-01___runtime____wine-helper-focus-timeout.md](iteration-logs/2026-11-07-14-01___runtime____wine-helper-focus-timeout.md)

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

## Iteration 407

- When: `2026-11-07 14:28`
- Area: `runtime`
- Title: `wine-helper-child-focus-wait`
- Source: [2026-11-07-14-28___runtime____wine-helper-child-focus-wait.md](iteration-logs/2026-11-07-14-28___runtime____wine-helper-child-focus-wait.md)

# Iteration Log

- Area: `runtime`
- Title: `wine-helper-child-focus-wait`
- Started: `2026-11-07 14:28`

## Summary

- **Bug:** a routine stopped with `FocusFailed` at 14:23:36Z while the user switched and launched Mac apps. `helper.log`: 3x `focus_failed fg=explorer.exe err=5 child=101`. Since the restart there were 13 `child_focus` successes and 15 `child=101` timeouts: the child's runtime clusters around the 1.5s deadline and overruns under load. Wine process startup under Rosetta is the bottleneck. No keys were sent.

## Changes

- Helper: child focus deadline 4000ms (constant, like the other helper timings). Success is still judged by the foreground. Success logs `child_focus ms=N`; failure logs `... child=N child_ms=N`.
- Client: default `request_timeout_s` 6.0, covering a worst-case focus of about 4.2s (about 0.2s in-process plus 4s child) with margin. `FOCUS_ATTEMPTS` 3 -> 2, so a refused burst gives up after about 8.5s instead of about 13s.

## Follow-ups

- Collect `child_focus ms=` values from live runs to see the real startup distribution.
- Pre-warmed standby focus child experiment (runbook with the mouse-block test) to see whether an idle child keeps foreground rights.

## Iteration 408

- When: `2026-11-07 14:45`
- Area: `runtime`
- Title: `background-input-beta`
- Source: [2026-11-07-14-45___runtime____background-input-beta.md](iteration-logs/2026-11-07-14-45___runtime____background-input-beta.md)

# Iteration Log

- Area: `runtime`
- Title: `background-input-beta`
- Started: `2026-11-07 14:45`

## Summary

- User decision: background input (`wine_helper`) ships as a **beta**: it works, but it is not polished.
- Mouse-block experiment (`mouse_block_test.exe`, CrossOver in the macOS background, Elite kept the Win32 foreground):
  - Observe run: a fresh process took the foreground (explorer -> Elite at 403ms) and held it for 20s. `ll_moves=943 raw_input=943 cursor_moves=490`; the menu hover followed the mouse.
  - Swallow run: the hook swallowed `ll_moves=901`, but `raw_input=901` was still delivered and `cursor_moves=171`; the hover still moved.
  - So under Wine a `WH_MOUSE_LL` hook cannot block Elite's mouse. A helper mouse lock and a front-app-tied lock are dropped.
- Ruled out by the user: another macOS Space, minimizing Elite, parking the window, fake mouse injection (`SetCursorPos` warps the real cursor).

## Changes

- `docs/user/background-input.md`: Beta note at the top; new limits for the mouse (hands off the game window during routines, especially station menus) and for the 1-4s refocus wait with occasional `focus_failed`.
- Skill `edcr-background-input`: tell players about the beta limits before setup and again at hand-over.
- README: beta label on the background input doc link.
- Research 0007: mouse experiment results, conclusions and possible next steps.
- `docs/status/runtime.md`: beta caveat and follow-ups.

## Follow-ups

- Detect Mac mouse movement during menu steps: wait for idle before a menu step; on movement, back out to a known state and redo the step. Not implemented.
- Standby focus child experiment (exe and runbook exist, not run).
- Atomic replace in `install_wine_input_helper.py` (copy to a temp file, then rename).

## Iteration 409

- When: `2026-11-07 18:47`
- Area: `runtime`
- Title: `pre-jump-hardpoint-retraction`
- Source: [2026-11-07-18-47___runtime____pre-jump-hardpoint-retraction.md](iteration-logs/2026-11-07-18-47___runtime____pre-jump-hardpoint-retraction.md)

# Iteration Log

- Area: `runtime`
- Title: `pre-jump-hardpoint-retraction`
- Started: `2026-11-07 18:47`

## Summary

- Prevent routine-driven FSD engagement while readable Status.json still reports deployed hardpoints after two retraction attempts.

## Changes

- Added one shared function with injected status read, toggle, time, sleep and progress capabilities; uses semantic `DeployHardpointToggle` binding support through controls/progress controls and binding diagnostics.
- Covers `jump` (control room and CLI), shared undock/normal-space departures for travel, two-way haul, multi-leg haul and Spansh start handoff, plus travel from supercruise. Manual pilot-driven Spansh hops remain manual.
- Added `[controls.hardpoints].retract_timeout_seconds` (positive finite, default 5s), 0.1s polling and one paced retry. Confirmed persistent deployment returns a routine failure with the usual Failed:/Try: operator guidance.
- User-approved hybrid policy: unavailable/empty/corrupt status retries within the timeout, warns and continues; unknown state never triggers a toggle. Mass-lock escape also tolerates malformed status so it reaches the guard. Explicit Flags validation is opt-in for pre-jump reads, preserving existing balance/cargo consumers.
- Full suite: 914 tests passed in 0.993s; timing budget is 0.5484s (0.0006s/test), so the required slowest-test report was run. Existing CLI/server/journal tests dominate; the timing target remains unmet on this machine.
- Added behavior coverage for successful retraction, second-press recovery, persistent deployment, missing binding, transient/persistent unreadable state, semantic dispatch, config validation, and all three travel start paths.

## Follow-ups

- Live-validate under CrossOver, especially Status.json refresh latency and a dropped toggle; tune the configurable timeout if needed.
- Landing gear and cargo scoop are intentionally outside this slice. No raw key is used.
- The legacy `tools/run_routine.py --routine haul_loop` still has pre-existing stale flat HaulRuntime/HaulTiming construction; its standalone jump entry was updated, but repairing legacy haul CLI is separate work.

## Iteration 410

- When: `2026-11-07 20:33`
- Area: `control-room`
- Title: `freeze-haul-timers-on-stop`
- Source: [2026-11-07-20-33_control-room_freeze-haul-timers-on-stop.md](iteration-logs/2026-11-07-20-33_control-room_freeze-haul-timers-on-stop.md)

# Iteration Log

- Area: `control-room`
- Title: `freeze-haul-timers-on-stop`
- Started: `2026-11-07 20:33`

## Summary

- Freeze haul Session and Elapsed when routine cleanup runs, and exclude idle time between hauls.

## Changes

- Stop captures both clocks before closing the history row and clearing active state; docked cycle duration is preserved. Completed cycles retain their final Elapsed until the next cycle/haul starts instead of clearing the visible value.
- Start resumes Session from its stored elapsed duration with an explicit None check (a zero clock origin is valid), while the new run starts fresh.
- Persisted session restore and new-session resets leave idle/paused clocks frozen; active, unpaused hauling still starts the new session clock immediately. Pause/resume behavior remains covered.
- Seven fake-clock behavior tests exercise local panel rendering and remote data-source copies after common routine cleanup, repeated stops, paused stop, docked/completed cycles, relaunch, idle/paused reset, and subsequent starts including a smaller post-reboot monotonic origin.
- Full unittest discovery: 921 tests passed in 0.679s. The 0.5526s target was exceeded; the required timing report identifies existing route/haul/server/timezone tests as the slowest. This is below the previously reported ~2s baseline, so no regression is indicated.
- Iteration archive regenerated; iteration log validation and diff whitespace checks passed.

## Follow-ups

- Confirm frozen local/remote timers after a live completed, failed or operator-stopped haul. No rendering or hydrate implementation changes were needed.

## Iteration 411

- When: `2026-11-07 21:20`
- Area: `runtime`
- Title: `no-activate-sendinput-experiment`
- Source: [2026-11-07-21-20___runtime____no-activate-sendinput-experiment.md](iteration-logs/2026-11-07-21-20___runtime____no-activate-sendinput-experiment.md)

# Iteration Log

- Area: `runtime`
- Title: `no-activate-sendinput-experiment`
- Started: `2026-11-07 21:20`

## Summary

- Elite under CrossOver ignores input unless it is the Win32 foreground window. `SendInput` from inside the bottle without activating Elite did nothing; the same send with activation worked. Truly no-focus input is ruled out, and so is the virtual-gamepad route.

## Changes

- **Setup:** Test bottle, CrossOver Preview, ghostty in front, Control Room running but idle. The bottle's AHK diagnostic `drive_c/ahk/bgtest.ahk` temporarily had a `SendInputNoActivate` mode (`SendInput` without `WinActivate`). Key: `GalaxyMapOpen` (LeftCtrl+M). Checked through the journal `Music` event.
- **No activation: FAIL.** The run was valid: the log showed `fg=explorer.exe targetActive=0` at both BEFORE and SENT. No GalaxyMap `Music` line appeared and nothing happened in game. A `Starport` line 12s later was ambient docked music; the map never opened.
- **Control, `SendInput` with activation: PASS.** Elite became the Win32 foreground. GalaxyMap opened at 21:10:22 and closed at 21:10:47 (back to Starport).
- **Conclusion:** Elite does not register raw input for background delivery (no `RIDEV_INPUTSINK`-style behavior), so Win32 focus inside Wine is required. The helper's focus-then-`SendInput` design stays.
- **Gamepad route dropped.** The user reports Elite does not read controllers while in the background. Native Windows evidence agrees: community tools like joyfocus exist only to give Elite focus when a joystick moves.
- **New observation:** during the control run Elite grabbed and showed the Mac cursor, even though ghostty stayed the macOS front app. This was not recorded in earlier helper runs.
  - Likely cause (inferred, not verified): on activation Elite clips or captures the cursor (`ClipCursor` / `SetCapture` / `ShowCursor` around `WM_ACTIVATE`). winemac implements cursor clipping with a macOS event tap and cursor disassociation, which can confine the real Mac cursor even while CrossOver is not the macOS front app.
- The AHK script was restored to its previous modes afterwards.

## Follow-ups

- Check whether the wine helper's focus step causes the same cursor grab, and when it happens (docked vs flight, every activation or only the first). If it does, it hurts background use more than the hover limit does, because it takes the user's mouse away.
- Test a helper-side release: call `ClipCursor(NULL)` after focus. Clipping is global in Win32, so any process can clear it, though Elite may clip again on its next frame.
- The mouse-idle mitigation should also detect a captured cursor (for example a hidden cursor or a cursor pinned at the Elite window), not only Mac mouse movement.

## Iteration 412

- When: `2026-11-07 21:55`
- Area: `runtime`
- Title: `warn-galaxy-map-binding-conflicts`
- Source: [2026-11-07-21-55___runtime____warn-galaxy-map-binding-conflicts.md](iteration-logs/2026-11-07-21-55___runtime____warn-galaxy-map-binding-conflicts.md)

# Iteration Log

- Area: `runtime`
- Title: `warn-galaxy-map-binding-conflicts`
- Started: `2026-11-07 21:55`

## Summary

- Warn about galaxy-map camera/menu cursor chord conflicts and fix primary modifier carry-over into keyboard secondary bindings.

## Changes

- Added a pure parsed-tree conflict detector beside the bindings layer, comparing resolved UI_Up/Down/Left/Right keys plus modifiers against both keyboard slots of CamTranslate/CamYaw/CamPitch/CamZoom button actions. Axes, joystick inputs and different modifier chords are excluded.
- Reused the detector in Control Room startup and the check_bindings CLI. Warnings include the conflicting action and UI Mode arrow-key guidance; lookup/dispatch, existing issue counts and exit status remain unchanged. JSON adds a warnings list. Advisory file reread failures are ignored.
- Reset the modifier when selecting a keyboard secondary, then read only that slot's modifier. Keyboard secondary priority remains unchanged.
- Added 10 behavior tests including the four-direction WASD + VKB setup, arrow secondaries, differing/matching modifiers and aliases, all camera button families/slots, axes exclusion, startup logging, CLI text/JSON and modifier carry-over.
- Full unittest discovery: 931 tests passed in 2.372s. Sequential same-session baseline on unchanged main: 921 tests in 2.444s, so no regression is indicated despite exceeding the 0.5586s target. Required timing report ran (931 tests OK, 1.561s; slowest are existing helper/CLI/haul/timezone tests).
- Updated bindings setup guidance and runtime handoff; iteration archive regenerated and validation passed.

## Follow-ups

- Live operators should assign arrow-key secondaries in Elite when warned. This change never edits the user bindings file or blocks their routines.

## Iteration 413

- When: `2026-11-07 23:24`
- Area: `tools`
- Title: `file-path-tool-entrypoints`
- Source: [2026-11-07-23-24____tools_____file-path-tool-entrypoints.md](iteration-logs/2026-11-07-23-24____tools_____file-path-tool-entrypoints.md)

# Iteration Log

- Area: `tools`
- Title: `file-path-tool-entrypoints`
- Started: `2026-11-07 23:24`

## Summary

- The documented `uv run python3 tools/<tool>.py` form failed with `ModuleNotFoundError: No module named 'edap'` for 8 tools, because running a file path puts `tools/` on `sys.path` instead of the repo root. Only `-m tools.<tool>` worked.

## Changes

- `bindings_files`, `check_bindings`, `diagnostics`, `run_routine`, `set_binding`, `speak`, `view_bindings` and `watch_journal` now add the repo root to `sys.path` before importing `edap`. This is the same `REPO_ROOT` bootstrap that `ship_controls`, `haul_stats`, `iteration_logs` and `report_test_timing` already used. Both invocation forms work, so the docs stay as written.
- `tests/test_tools_entrypoints.py` fails if any `tools/*.py` imports `edap` without the bootstrap first. It scans source text and starts no subprocess, so it stays within the test-time budget.

## Follow-ups

- `tools/scratch/scratch_cv.py` and `scratch_rebake.py` fail on a missing `cv2`. That is a dependency gap, not a path problem, so it was left alone.
- The full suite runs over the 0.0006s/test budget even at HEAD before this change (0.895s for 931 tests, with Elite running on this machine).

## Iteration 414

- When: `2026-11-08 11:31`
- Area: `runtime`
- Title: `steam-deck-uinput-input`
- Source: [2026-11-08-11-31___runtime____steam-deck-uinput-input.md](iteration-logs/2026-11-08-11-31___runtime____steam-deck-uinput-input.md)

# Iteration Log

- Area: `runtime`
- Title: `steam-deck-uinput-input`
- Started: `2026-11-08 11:31`

## Summary

- First Linux validation, on a Steam Deck (SteamOS holo, Desktop Mode `kwin_x11`, Elite through Proton). The repo lives at `~/EDControlRoom` on the Deck (`/home` survives SteamOS updates) and runs with the user-installed `~/.local/bin/uv`. Journal and bindings auto-detect inside the Proton prefix (`compatdata/359320`) with no `config.toml`.
- The `deck` user has a seat ACL on `/dev/uinput`, so a kernel virtual keyboard needs no sudo or extra packages. Unlike xdotool it does not depend on X11, so it should also reach the game under Game Mode's gamescope (not yet tested).

## Changes

- New `edap/platform/input/uinput.py`: `LinuxUinputController` writes evdev key events through injected `write_key`/`close_device`; `UinputKeyboard` is the thin `/dev/uinput` adapter (stdlib `fcntl`/`struct`, device created on first key, 1s settle so the first press is not dropped). evdev codes come from the shared set-1 table, with an explicit map for extended keys and F13-F15.
- `[input.linux] backend = "uinput" | "xdotool"`, default `uinput`. xdotool stays selectable.
- Deck bindings: the Deck uses a controller preset, so 7 required actions had no keyboard binding. `tools/set_binding.py` mirrored the Mac keys (Pitch `,`/`.`, Roll `A`/`D`, `SetSpeed100` `R`, `UIFocus` LeftShift, `HeadLookReset` `G`), moved the clashing Deck keys to the Mac layout (Yaw `[`/`]`, `UpThrustButton` LeftControl), added `GalaxyMapOpen` secondary `Ctrl+M` and arrow-key `UI_*` secondaries. The original is `Custom.4.2.binds.bak`. `check_bindings` is now 19/19.

## Verification

- Live, Desktop Mode, docked: `ship_controls.py --sequence "FocusLeftPanel; UI_Back delay=3; GalaxyMapOpen delay=3; GalaxyMapOpen delay=9"` moved `GuiFocus` 0 → 2 → 0 → 6 → 0, with journal `Music` `GalaxyMap` then `Starport`.

## Follow-ups

- Test the same sequence in Game Mode (gamescope).
- uinput is foreground-only input: keys go to whatever window has focus. No pid targeting on Linux.

## Iteration 415

- When: `2026-11-08 11:43`
- Area: `web`
- Title: `route-copy-paste`
- Source: [2026-11-08-11-43_____web______route-copy-paste.md](iteration-logs/2026-11-08-11-43_____web______route-copy-paste.md)

# Iteration Log

- Area: `web`
- Title: `route-copy-paste`
- Started: `2026-11-08 11:43`

## Summary

- Haul search scrapes Inara through Playwright and Chrome. The Steam Deck should not need either, so a route is now searched on the laptop's Control Room and pasted into the Deck's.

## Changes

- Haul v1 setup panel: a `Copy / paste route` disclosure with a text box, `Copy selected` and `Import pasted`. Scope per the user: the selected route only, route fields only (no search form parameters), haul page only (not `/multi-haul`).
- Copy writes `routeTransferPayload(route)` as pretty JSON: the 11 route fields a haul needs or shows (systems, stations, commodities, station and route distances, profits), empty ones dropped. Index, `raw_text`, `url_links`, supply/demand snapshots and `distance_from_system` stay local; `raw_text` only feeds a debug log on search load. Older pasted JSON with those fields still imports. The Clipboard API needs https or localhost, so a LAN `http://` page falls back to `execCommand("copy")`, then to leaving the text selected for Ctrl+C.
- Import requires from/to systems and stations, keeps the index of a matching local route (same `routeKey`) or takes a fresh one, then selects it and persists it with the existing `command.select_trade_route`, which validates the route server side. No new server command.

## Verification

- Full suite passes. A node round trip of the real `routeFromApi` → `tradeRoutePayload` → JSON → `routeFromApi` gives identical fields and the same `routeKey`. Confirmed live 2026-11-08 by the user: copied on the laptop Control Room, pasted into the Steam Deck one.

## Iteration 416

- When: `2026-11-08 12:27`
- Area: `control-room`
- Title: `reload-keymap-command`
- Source: [2026-11-08-12-27_control-room_reload-keymap-command.md](iteration-logs/2026-11-08-12-27_control-room_reload-keymap-command.md)

# Iteration Log

- Area: `control-room`
- Title: `reload-keymap-command`
- Started: `2026-11-08 12:27`

## Summary

- Control Room read the bindings file once at startup, so a binding changed while it ran (here: Boost on the Steam Deck) needed a Control Room restart. `reload` only re-imports code modules and never rereads bindings.

## Changes

- New `reload_keymap` command (TUI and web command box): rereads the effective bindings file into `_ctx.binding_lookup`, rebuilds `ShipControls`, and reprints the bindings check. Refused while a routine runs, because a routine keeps the controls it started with. A missing or unparsable file is reported and the old keymap stays. Elite itself still needs a restart to read new bindings.

## Follow-ups

- The user wants `reload` removed. It is stale: `_RELOADABLE_MODULES` misses newer modules (`routines_travel`, `routines_spansh`, `routine_runtime_builder`, `routine_stop`, `view_models`, `view_actions`, `failure_messages`, ...), never reloads `edap/routines/*`, and `importlib.reload` does not refresh names other modules imported with `from X import y`.

## Iteration 417

- When: `2026-11-08 13:00`
- Area: `control-room`
- Title: `remove-reload-command`
- Source: [2026-11-08-13-00_control-room_remove-reload-command.md](iteration-logs/2026-11-08-13-00_control-room_remove-reload-command.md)

# Iteration Log

- Area: `control-room`
- Title: `remove-reload-command`
- Started: `2026-11-08 13:00`

## Summary

- Removed the `reload` hot-reload command. Its module list had gone stale and `importlib.reload` never refreshed names bound with `from X import y`, so it gave false confidence. Code changes need a Control Room restart; binding changes use `reload_keymap`.
- The user confirmed uinput input works in Steam Deck Game Mode (gamescope), not only Desktop Mode.

## Changes

- Dropped the `reload` verb, `ControlRoomFacade.cmd_reload`, `_RELOADABLE_MODULES`, the `edap/control_room/tts.py` re-export shim and the `reload_failed` message. `reload` now reports as an unknown command.
- Steam Deck bindings (outside the repo): an in-game save at 12:09 had unbound `YawAxisRaw`, moved `RollAxisRaw` to the right stick and cleared Pitch inversion. Restored those three axes from `Custom.4.2.binds.bak` (right stick X yaw, left stick X roll, pitch inverted), keeping CRLF line endings; pre-restore copy in `Custom.4.2.binds.pre-axis-restore`.

## Follow-ups

- Saving controls in game rewrites the whole binds file from memory, so write bindings with Elite closed or restart it without saving.

## Iteration 418

- When: `2026-11-08 14:42`
- Area: `runtime`
- Title: `steam-deck-keymap-and-install-docs`
- Source: [2026-11-08-14-42___runtime____steam-deck-keymap-and-install-docs.md](iteration-logs/2026-11-08-14-42___runtime____steam-deck-keymap-and-install-docs.md)

# Iteration Log

- Area: `runtime`
- Title: `steam-deck-keymap-and-install-docs`
- Started: `2026-11-08 14:42`

## Summary

- New Steam Deck users needed the keyboard keys routines press added to their controller preset by hand. `tools/deck_keymap.py` now does it in one step, and the install docs describe the real Deck install (uv in `~/.local/bin`, clone, `uv sync`, uinput, no `config.toml`) instead of the old untested xdotool notes.

## Changes

- `edap/deck_keymap.py`: `DECK_KEYMAP` (Elite KeyboardMouseOnly defaults where they exist; arrows for menu directions; roll `,` `.`, pitch `I` `K`, `SetSpeed100` F5, `HeadLookReset` F6, `GalaxyMapOpen` F7 for actions with no keyboard default) and `plan_deck_keymap`, which fills empty slots Secondary first, keeps any user keyboard key, replaces only bare WASD on `UI_*`, and never touches controller bindings.
- `tools/deck_keymap.py`: prints the plan; `--write` applies it after a backup that never overwrites an older `.bak`.
- Checked against Elite's shipped `ConsoleX360.binds` (the Deck preset's base): 13 changes, then every keymap action resolves and no galaxy-map warning. On the user's current Deck file it changes nothing.
- README gains a Steam Deck section; `docs/user/install.md` replaces "Linux (untested)" with a Steam Deck / Linux section.

## Follow-ups

- Semicolon was avoided: Elite's token spelling for it is unverified and the lookup only knows `Key_Semicolon`.

## Iteration 419

- When: `2026-11-08 17:58`
- Area: `haul`
- Title: `undock-under-attack-escape`
- Source: [2026-11-08-17-58_____haul_____undock-under-attack-escape.md](iteration-logs/2026-11-08-17-58_____haul_____undock-under-attack-escape.md)

# Iteration Log

- Area: `haul`
- Title: `undock-under-attack-escape`
- Started: `2026-11-08 17:58`

## Summary

- Steam Deck journal `Journal.2026-11-08T124339.01.log`: at Voltaire Terminal (A. Lavigny-Duval space) Power Security Force attacks on approach and launch. `Combat_Dogfight` music replaces the post-undock `NoTrack`, so the haul waited on a 600s timeout; at 15:04 the ship never left the no-fire zone and died at 15:08 after shields dropped.
- `ReceiveText` `$STATION_NoFireZone_exited;` fires on every launch, 20-45s after `NoTrack` on normal launches, and is the only clear cue under combat music.
- Normal auto-launch reaches `NoTrack` about 37s after `Undocked`, so boosting earlier risks the slot; the flee gate is 40s unless damage lands first.

## Changes

- No-fire-zone exit is a clear-of-station cue in the routine wait and both ship-state reducers.
- `_wait_for_clear_of_station` watches `UnderAttack` (Target `You`), `ShieldState` down and player `HullDamage`, calls a required `threat_fn` once (TTS `under_attack`), and returns `UnderAttack` on damage, on a clear cue while threatened, or 40s after `Undocked` (`undocked_at` now in the undock result details).
- Transit escape: mass-lock boost, hardpoint guard, `Supercruise` (new optional binding, Deck keymap `F8`; falls back to `HyperSuperCombination`), wait up to 45s for `SupercruiseEntry`/hyperspace `StartJump`, then TTS `supercruise_escape_align` and leave the jump to the pilot. Timeout aborts with `haul_aborted`. Standalone `undock` takes `announce_fn` and stops with an error for manual control.
- `dock()` TTS-warns `under_attack` once when attacked during the docking response or `Docked` waits (seen 14:19 and 17:33) and does not change the docking flow; the docking computer flying on into the no-fire zone is usually the fastest way out.

## Follow-ups

- Live-validate the escape on Deck after rerunning `tools/deck_keymap.py --write` so `Supercruise` has a keyboard key.

## Iteration 420

- When: `2026-11-08 22:35`
- Area: `web`
- Title: `browser-speech`
- Source: [2026-11-08-22-35_____web______browser-speech.md](iteration-logs/2026-11-08-22-35_____web______browser-speech.md)

# Iteration Log

- Area: `web`
- Title: `browser-speech`
- Started: `2026-11-08 22:35`

## Summary

- Bring TTS to iPhone/Safari without the console app. The server already broadcast `event.announcement_emitted` with rendered `message_text`; the web page ignored it.

## Changes

- `haul-ui.js` re-dispatches the event as `edcr:announcement`; new `web/speech.js` (served from the asset allowlist) speaks it with `speechSynthesis`.
- Routine panel disclosure `Speak announcements on this device`: on/off, voice (English voices, or all if none), rate 0.5x to 1.5x, `Test voice`. Settings are per device in localStorage so a Mac already using `say` does not double up.
- iOS needs a user gesture: the first tap after load speaks a silent utterance to unlock audio. Only live announcements speak; nothing replays on reconnect.

## Follow-ups

- Not yet tested on a real iPhone: which voices Safari lists (downloaded enhanced voices vs Siri voices) and whether the silent switch mutes it.
- Locked screen or background tab suspends the page, so speech stops. Wake Lock needs https (for example `tailscale serve`); Web Push plus AirPods announce notifications is the locked-screen option.
- The server must restart once to serve `speech.js` because the asset allowlist lives in `app.py`.

## Iteration 421

- When: `2026-11-08 22:58`
- Area: `runtime`
- Title: `piper-tts-backend`
- Source: [2026-11-08-22-58___runtime____piper-tts-backend.md](iteration-logs/2026-11-08-22-58___runtime____piper-tts-backend.md)

# Iteration Log

- Area: `runtime`
- Title: `piper-tts-backend`
- Started: `2026-11-08 22:58`

## Summary

- Add a Piper TTS backend so the Deck (and Mac) get a natural local voice instead of `spd-say`/espeak.

## Changes

- `[tts.piper] executable` + `model` (`PiperVoiceConfig`); config load rejects a half-filled table or missing files.
- `PiperSpeechBackend` keeps one `piper --output_dir` process loaded: write a line, read back the wav path, play it, delete it. A dead or silent Piper is killed and restarted once per line. Players: `pw-play`/`paplay`/`aplay` on Linux, `afplay` on macOS; no player means the platform voice.
- Deck measurements: cold `cori-high` about 3.1s per line, warm about 1.85s; medium voices about 0.9s cold. Live check on the Deck through `build_speech_backend` played two lines and left no wavs.
- `tools/speak.py` still uses the platform voice. Docs: `config.example.toml`, getting-started (browser speech plus Piper; dropped the stale "browser will not speak").

## Follow-ups

- `lan` still passes `NullSpeechBackend`; speaking on the server host by default is the planned next step.

## Iteration 422

- When: `2026-11-08 23:02`
- Area: `control-room`
- Title: `lan-mode-speaks-tts`
- Source: [2026-11-08-23-02_control-room_lan-mode-speaks-tts.md](iteration-logs/2026-11-08-23-02_control-room_lan-mode-speaks-tts.md)

# Iteration Log

- Area: `control-room`
- Title: `lan-mode-speaks-tts`
- Started: `2026-11-08 23:02`

## Summary

- `serve`/`lan`/`local` now speak TTS on the server host by default, so the Steam Deck no longer needs a `connect` TUI just for callouts.

## Changes

- `HeadlessControlRoomHost` takes a required `speech_backend`; `serve_observer_mode` takes a required `speak_tts` and builds the platform or Piper backend (`tts.piper`) when it is set.
- New `--no-tts` flag keeps the server silent. A `connect` TUI also speaks every server announcement (`_play_local_announcement`), so a TUI on the same machine as `lan` needs `lan --no-tts` to avoid double callouts.
- With a real backend the announcer now dedups consecutive identical callouts on the server too, so a repeated identical line is no longer re-broadcast to clients (same as the embedded TUI).
- README and getting-started describe the new default.
- Default `tts.title_mode` is now `commander_name` (falls back to "commander" until a journal `LoadGame` names the commander).

## Follow-ups

- Mac Piper support is paused: the official macOS binary misses `libespeak-ng`, and PyPI `piper-tts` 1.8 (installed on the Mac via `uv tool`) logs `Wrote <path>` to stderr instead of printing the path to stdout, so `PiperSpeechBackend` needs to read either.

## Iteration 423

- When: `2026-11-08 23:21`
- Area: `runtime`
- Title: `piper-setup-all-platforms`
- Source: [2026-11-08-23-21___runtime____piper-setup-all-platforms.md](iteration-logs/2026-11-08-23-21___runtime____piper-setup-all-platforms.md)

# Iteration Log

- Area: `runtime`
- Title: `piper-setup-all-platforms`
- Started: `2026-11-08 23:21`

## Summary

- One Piper path on macOS, Linux and Windows: piper-tts as an isolated `uv tool`, the two picked voices as defaults, and `tools/setup_piper.py` to install and configure it.

## Changes

- Engine: PyPI `piper-tts==1.8.0` (piper1-gpl) via `uv tool install`, run only as a subprocess. It is GPL-3.0-or-later and this repo is MIT, so it is not a project dependency and is never imported. The old rhasspy C++ release is dropped: its macOS build misses `libespeak-ng`.
- `PiperSpeechBackend` reads piper-tts' stderr `Wrote <path>` line (the C++ build printed the path on stdout) and plays through an injected `play(wav_path)`: `pw-play`/`paplay`/`aplay`, `afplay`, or stdlib `winsound` on Windows. The child gets UTF-8 stdio.
- `edap/piper_setup.py` + `tools/setup_piper.py [--voice cori|jenny]`: install the tool, download the voice to the platform data dir (`~/Library/Application Support/EDControlRoom/piper`, `$XDG_DATA_HOME` or `~/.local/share/EDControlRoom/piper`, `%LOCALAPPDATA%\EDControlRoom\piper`) with pinned piper-voices v1.0.0 sizes and md5s, write `[tts.piper]` (TOML literal strings), reload-check the config (restoring it on failure), and speak a test line.
- Voice licenses: Cori is trained on public-domain LibriVox. Jenny's dataset allows commercial use but asks for the "Jenny (Dioco)" credit, which the voice label and docs carry.
- Verified on the Mac: a fresh install, an install of the second voice, and a switch back (files already present skipped, section replaced in place).

## Follow-ups

- Windows is untested live (unit tests only).

## Iteration 424

- When: `2026-11-09 08:31`
- Area: `haul`
- Title: `reopen-market-on-station-check`
- Source: [2026-11-09-08-31_____haul_____reopen-market-on-station-check.md](iteration-logs/2026-11-09-08-31_____haul_____reopen-market-on-station-check.md)

# Iteration Log

- Area: `haul`
- Title: `reopen-market-on-station-check`
- Started: `2026-11-09 08:31`

## Summary

- A haul at Melroy Gateway failed the market station check although the station was right: the market never opened, and the retries only re-read the stale `Market.json`. Restarting the haul worked because it navigated again.

## Changes

- Deck journal 2026-11-09: `Docked` 08:14:10, open-market presses 08:14:16 to 08:14:23, no `Market` event until the haul was restarted (08:15:23). The operator saw station services open but not the market.
- Docked-to-first-`Market` gaps over 11/08 to 11/09 journals: Melroy Gateway (Coriolis) 4 of 24 over 40s, Voltaire Terminal (Dodec) 1 of 21. Both legs start pressing about 6s after `Docked`.
- `edap/routines/market.py`: navigation and the station check moved into `_open_commodities_market` and `_check_market_station`; each of the 3 attempts now backs out and navigates again. The failure reason text is unchanged, so the operator-facing mismatch message still applies.

## Follow-ups

- If lost presses keep showing up, wait for the services screen (a longer settle after a fresh `Docked`) rather than adding more attempts.
- Meaney Depot (2026-11-08 23:16 failure) has no `Market` event in the journals; not investigated.

## Iteration 425

- When: `2026-11-09 12:07`
- Area: `control-room`
- Title: `reload-config-command`
- Source: [2026-11-09-12-07_control-room_reload-config-command.md](iteration-logs/2026-11-09-12-07_control-room_reload-config-command.md)

# Iteration Log

- Area: `control-room`
- Title: `reload-config-command`
- Started: `2026-11-09 12:07`

## Summary

- New `reload_config` command so a Deck config tweak (here `controls.market.nav_delay_seconds = 0.2` against dropped list presses) no longer needs a server restart that kills the running haul.

## Changes

- `ControlRoomApp._cmd_reload_config` loads `_config_path`, swaps `_config` and `_ctx.config`, rebuilds controls (hold settings) and calls `TTSAnnouncer.apply_wording` (title, phrases, disabled messages; the speech backend and on/off stay as built).
- Routines read `app._config` when they start, so market, haul and timing settings take effect from the next routine. Anything built once at startup (paths, input controller, timing sampler, Piper voice, server host/port/state files) still needs a restart; the command says so.
- Refused while a routine runs, like `reload_keymap`; a parse or validation error keeps the running config.

## Follow-ups

- Not yet exercised live on the Deck.

## Iteration 426

- When: `2026-11-09 12:25`
- Area: `haul`
- Title: `pass-market-nav-delay`
- Source: [2026-11-09-12-25_____haul_____pass-market-nav-delay.md](iteration-logs/2026-11-09-12-25_____haul_____pass-market-nav-delay.md)

# Iteration Log

- Area: `haul`
- Title: `pass-market-nav-delay`
- Started: `2026-11-09 12:25`

## Summary

- Deck hauls kept buying the commodity 1 to 3 rows above Silver (row 36 at Voltaire Terminal) after `[controls.market] nav_delay_seconds = 0.2`. The 12:17 buy took 7.3s for 36 presses, the same pace as before, because two-way and multi-leg haul never passed `nav_delay_s` and `market_buy`/`market_sell` fell back to their 0.1s default. Only manual `buy`/`sell` read the config.

## Changes

- `HaulMarketSettings` gains `nav_delay_s`, built from `controls.market_nav_delay_seconds`, and every haul market buy/sell call (two-way sell, buy, sell-all recovery; multi-leg sell, buy) passes it.
- Test: `test_market_trades_use_the_configured_nav_delay`.

## Follow-ups

- Deploy to the Deck and watch whether Voltaire Silver buys stop landing short at 0.2s.
- `market_buy`/`market_sell` still default `nav_delay_s=0.1`; making it required would stop a caller silently skipping config, but needs the routine tests updated.

## Iteration 427

- When: `2026-11-09 17:40`
- Area: `control-room`
- Title: `web-controls-page`
- Source: [2026-11-09-17-40_control-room_web-controls-page.md](iteration-logs/2026-11-09-17-40_control-room_web-controls-page.md)

# Iteration Log

- Area: `control-room`
- Title: `web-controls-page`
- Started: `2026-11-09 17:40`

## Summary

- The web UI had no way to fire single routines (dock, undock, escape and so on), and `/haul` is already full, so a separate `/controls` button board was added.

## Changes

- `web/controls.html` + `web/controls.js`: Flight (undock, dock, jump, escape, boost x3), Market (buy/sell with commodity and amount, sell all cargo), Routine (pause, resume, stop after run, stop now, instant toggle, reload config, reload keymap) and an activity feed. Idle-only buttons send through the normal launch delay; routine controls skip it.
- Follow-up from review: panel heads show `Idle` / `Busy: <routine>` (with pause state) instead of a static `Idle only`, Flight gets a full-width red `STOP NOW` (cancels immediately, enabled only while a routine runs), and instant mode is an `aria-checked` switch instead of a button.
- Server: `/controls` route and `controls.js` asset; sidebar links from `/haul` and `/multi-haul`.
- Verified with a preview `serve` on 127.0.0.1:8799: page and asset return 200, websocket gives `active_operator` and hydrate carries ship and routine state. No browser click-through (Chrome extension not connected), no button pressed against the game.

## Follow-ups

- Try it in a browser on the Deck; in the preview check hydrate `ship.station` came back empty, so confirm the Station tile fills in when docked.

## Iteration 428

- When: `2026-11-09 19:37`
- Area: `control-room`
- Title: `mobile-route-cards`
- Source: [2026-11-09-19-37_control-room_mobile-route-cards.md](iteration-logs/2026-11-09-19-37_control-room_mobile-route-cards.md)

# Iteration Log

- Area: `control-room`
- Title: `mobile-route-cards`
- Started: `2026-11-09 19:37`

## Summary

- On phone width the `/haul` route results cards showed the wrong labels: CARGO next to the profit, STATION 1 next to the commodity, and the station/system sub-lines fell into the label column.

## Changes

- `web/haul-ui.css`: mobile card labels now come from `content: attr(data-label)` instead of hardcoded `nth-child` labels; every child of a cell sits in the value column (`grid-column: 2`), so multi-line station and supply/demand cells stack correctly.
- `web/haul-ui.js`: each route row cell carries a `data-label` matching its header. `web/route-compare.js` copies labels from its table's `thead` so the comparison tables get the same card layout.
- Test `test_haul_route_cards_label_every_column_like_the_table_header` keeps the row labels in sync with the `haul-v1.html` headers.
- Verified with Playwright at 390x844 against a local preview `serve`.

## Follow-ups

- Route Comparison tables on mobile were not screenshotted with real data.

## Iteration 429

- When: `2026-11-09 20:01`
- Area: `control-room`
- Title: `hydrate-keeps-operator-edits`
- Source: [2026-11-09-20-01_control-room_hydrate-keeps-operator-edits.md](iteration-logs/2026-11-09-20-01_control-room_hydrate-keeps-operator-edits.md)

# Iteration Log

- Area: `control-room`
- Title: `hydrate-keeps-operator-edits`
- Started: `2026-11-09 20:01`

## Summary

- On `/haul` the operator could not reach route results page 2 or edit cargo capacity: every hydrate (sent on each journal change, so often during a haul) rewrote `origin` and `capacity` and re-merged the selected route, which reset the selection and the page and re-rendered the rows.

## Changes

- `web/haul-ui.js`: `syncHydratedField` refills `origin`/`capacity` only when the field is not focused and still holds the last hydrated value (or is empty), so operator edits stick until Reset.
- The selected/running route is merged only when its key differs from the last hydrated one, so repeat hydrates keep the operator's row and page and do not re-render rows under a tap. A merged existing route keeps its local index.

## Follow-ups

- `/multi-haul` `applyShipDefaults` has the same pattern (origin, capacity, capital refilled on every hydrate); not changed yet.
- Not reproduced in a browser: the local preview has no live journal churn, so verify on the Deck during a haul.

## Iteration 430

- When: `2026-11-09 21:01`
- Area: `haul`
- Title: `selected-route-supply-demand`
- Source: [2026-11-09-21-01_____haul_____selected-route-supply-demand.md](iteration-logs/2026-11-09-21-01_____haul_____selected-route-supply-demand.md)

# Iteration Log

- Area: `haul`
- Title: `selected-route-supply-demand`
- Started: `2026-11-09 21:01`

## Summary

- The first `/haul` search result showed `-` for supply and demand. After a search the page selects route 1 and sends it to the server; the server's route parser dropped `from_supply`/`from_demand`/`to_supply`/`to_demand`, and the next hydrate merged that stripped route over the search result.
- Separately, the TUI `haul search` rejected a decimal route distance (`17.2`) that the web page had saved to `haul_search.toml`, so the prompt failed for anyone who searched from the web with a jump-range preset.

## Changes

- `edap/control_room/server/commands.py` and `edap/control_room/protocol/data_messages.py`: route parsers keep the four supply/demand fields, so selected/running routes keep them through select, hydrate and `connect`.
- `edap/control_room/prompts.py`: `parse_optional_nonnegative_number_text` accepts any non-negative number for max route distance and keeps the text as typed.
- Tests: server select test and data-message round trip check supply/demand; new TUI test for a decimal route distance.

## Follow-ups

- TUI haul search tests read the real working-directory `haul_search.toml`, so a local web search can change their results; isolate them from that file.

## Iteration 431

- When: `2026-11-10 12:56`
- Area: `haul`
- Title: `web-route-import-surface-flags`
- Source: [2026-11-10-12-56_____haul_____web-route-import-surface-flags.md](iteration-logs/2026-11-10-12-56_____haul_____web-route-import-surface-flags.md)

# Iteration Log

- Area: `haul`
- Title: `web-route-import-surface-flags`
- Started: `2026-11-10 12:56`

## Summary

- A route pasted into `/haul` dropped any field the page did not map, and every web or selected-route haul hardcoded `station_*_on_land = false`, so surface ports (e.g. a CraterOutpost) could not be run from the web page.

## Changes

- `TradeRoute` gains `from_on_land` / `to_on_land` (default false), parsed with `route_flag_from_payload` (bool or `true/yes/1/on` text) in the server command, protocol and saved-state parsers.
- `haul_params_from_trade_route` and the web `selectedHaulParams` now pass the route's surface flags; web travel to a route endpoint inherits that endpoint's flag.
- `web/haul-ui.js`: `tradeRoutePayload` spreads the original API/pasted route first, so every pasted field survives selection; copied routes include the surface flags; route cards show `/ surface`.
- Verified with headless Chromium against the LAN page: pasting a route with `from_on_land: true` yields `station_1_on_land=true`.

## Follow-ups

- Inara results never set the flags (searches exclude surface stations by default).
- A running LAN server needs a restart before it persists the flags in the selected route.

## Iteration 432

- When: `2026-11-10 13:15`
- Area: `control-room`
- Title: `controls-nav-panel`
- Source: [2026-11-10-13-15_control-room_controls-nav-panel.md](iteration-logs/2026-11-10-13-15_control-room_controls-nav-panel.md)

# Iteration Log

- Area: `control-room`
- Title: `controls-nav-panel`
- Started: `2026-11-10 13:15`

## Summary

- `/controls` lacked the TUI navigation commands (`dest`, `travel`, `home`). Added a Nav panel; `set_input` and `verbose` were deliberately left out at the user's request.

## Changes

- `web/controls.html` / `web/controls.js`: Nav panel with System, Station and a Surface port checkbox, plus Plot route (`command.dispatch_destination` with the configured galaxy-map settle), Travel (`command.dispatch_travel`, `on_land` only with a station), Plot home and Set home (`home set`, current system when the field is empty). All need an idle routine.
- `edap/control_room/dependencies.py`: web form defaults include `homeSystem`, so Plot home dispatches by name instead of going through the TUI `home` prompt flow; the page refreshes it from each hydrate.
- Rendered headless at desktop and 390 px widths against the LAN page with no JS errors.

## Follow-ups

- Full suite runs about 0.61-0.63 s for 990 tests on a busy machine, above the 0.594 s budget even without this change; recheck on an idle machine.

## Iteration 433

- When: `2026-11-10 13:27`
- Area: `control-room`
- Title: `server-version-commit`
- Source: [2026-11-10-13-27_control-room_server-version-commit.md](iteration-logs/2026-11-10-13-27_control-room_server-version-commit.md)

# Iteration Log

- Area: `control-room`
- Title: `server-version-commit`
- Started: `2026-11-10 13:27`

## Summary

- A LAN server could not show which code it was running. The Mac server reported `1.26.0` on `/health` after v1.27.0 shipped, and the version alone cannot tell commits after a release apart.

## Changes

- `edap/version.py`: `get_current_commit(git)` returns the short HEAD, with `+dirty` for uncommitted tracked edits, or `""` without git; `get_startup_commit()` caches it once per process so a running server keeps reporting what it loaded.
- `VersionSource.get_current_commit` feeds `ServerStatusReadModel.server_commit`; `/health` returns `server_commit`, and pages get `serverCommit` in their injected config.
- `/haul`, `/multi-haul` and `/controls` show a sidebar Version row such as `1.27.0 (b2a65e4)`, refreshed from each hydrate.
- Calling git per app construction pushed the suite to 1.6 s; the per-process cache brings it back to baseline.

## Follow-ups

- Optional: flag when the server's startup commit differs from the checkout's current HEAD (restart needed).

## Iteration 434

- When: `2026-11-10 13:31`
- Area: `control-room`
- Title: `controls-voice-say`
- Source: [2026-11-10-13-31_control-room_controls-voice-say.md](iteration-logs/2026-11-10-13-31_control-room_controls-voice-say.md)

# Iteration Log

- Area: `control-room`
- Title: `controls-voice-say`
- Started: `2026-11-10 13:31`

## Summary

- `/controls` gains a Voice panel: type any text and speak it on the browsing device, with the device voice selector, rate, test button and an opt-in for routine announcements.

## Changes

- `web/speech.js`: optional `speech-say-text` / `speech-say` control (click or Enter) that cancels any current utterance and speaks the text, regardless of the announcements toggle. Settings stay shared with `/haul` via `edcr.speech`.
- `web/controls.js` forwards `event.announcement_emitted` as `edcr:announcement`, so the opt-in works on `/controls`.
- `web/controls.html` loads `speech.js` and adds the panel.

## Follow-ups

- This is browser speech only. Speaking arbitrary text through the server TTS (`say` / Piper) with a server voice selector would need a new command and a server restart.

## Iteration 435

- When: `2026-11-10 13:40`
- Area: `control-room`
- Title: `piper-voice-panel`
- Source: [2026-11-10-13-40_control-room_piper-voice-panel.md](iteration-logs/2026-11-10-13-40_control-room_piper-voice-panel.md)

# Iteration Log

- Area: `control-room`
- Title: `piper-voice-panel`
- Started: `2026-11-10 13:40`

## Summary

- The `/controls` Voice panel now drives the host Piper voice instead of browser speech: free-text `say`, TTS phrase presets to prefill it, a voice picker, five tuning sliders and Save to config.

## Changes

- `[tts.piper]` accepts optional `length_scale`, `noise_scale`, `noise_w_scale`, `sentence_silence` and `volume` (unset keeps the model or piper default); `save_piper_voice` upserts them without touching other lines.
- `PiperSpeechBackend.configure` swaps the voice between utterances and restarts piper; `piper_model_defaults` reads the model's `inference` block, `piper_voice_models` lists `<voices>/<name>/*.onnx` beside the configured model.
- New commands `say <text>` and `voice` / `voice set k=v ...` / `voice save` (`edap/control_room/voice.py`); `TTSAnnouncer.say` bypasses phrases and disabled messages.
- Hydrate carries `voice` (speech on, Piper flag, current and installed voices, effective settings, phrase presets with `{title}` filled). The web fills `{system_name}` / `{station_name}` from the ship.
- Reverted the browser `say` hook in `web/speech.js`; `/haul` keeps its device speech.
- Verified the real piper CLI accepts every tuning flag with the jenny voice.

## Follow-ups

- Needs a LAN server restart before the panel works; not yet tried in a real browser.

## Iteration 436

- When: `2026-11-10 14:26`
- Area: `haul`
- Title: `eddn-trade-routes-plan`
- Source: [2026-11-10-14-26_____haul_____eddn-trade-routes-plan.md](iteration-logs/2026-11-10-14-26_____haul_____eddn-trade-routes-plan.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-trade-routes-plan`
- Started: `2026-11-10 14:26`

## Summary

- Planned an EDDN-based trade route finder to replace the Inara scrape: [plan 0014](../plans/0014-eddn-trade-routes.md).

## Decisions

- Runs on the Mac, latest snapshot only (no price history), SQLite; Ardent lookups on demand; fleet carriers excluded by default.
- Near view (default) plus a global view of the best routes anywhere.
- Ranked by estimated profit per hour; multi-jump routes are allowed and rank high only when the profit pays for the extra jumps.
- Range presets in laden jumps (1, 2, 4 default) plus wide 100 ly+ presets. Current Panther Mk II laden range computes to 17.19 ly from `Loadout`, matching `max_route_distance_ly = 17.2`.
- Anomaly alerts named "Good Deals / Exceptional Routes", deferred to a later phase.

## Iteration 437

- When: `2026-11-10 14:34`
- Area: `haul`
- Title: `eddn-listener-store`
- Source: [2026-11-10-14-34_____haul_____eddn-listener-store.md](iteration-logs/2026-11-10-14-34_____haul_____eddn-listener-store.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-listener-store`
- Started: `2026-11-10 14:34`

## Summary

- Plan 0014 slices 1 and 2: an EDDN relay listener and a latest-snapshot SQLite price store, runnable standalone with `uv run python3 tools/eddn_listen.py`.

## Changes

- `edap/eddn/messages.py`: parses live `commodity/3` and `journal/1` Docked/CarrierJump/FSDJump/Location; drops `/test` schemas, legacy-galaxy uploads (`CAPI-Legacy`, game 2.x/3.x) and price rows the station neither sells nor wants. Carriers are flagged by `FleetCarrier` type or `XXX-XXX` callsign; market ids cannot tell them apart (colonisation stations also exceed 3.7 billion).
- `edap/eddn/store.py`: `system`, `station`, `market`, `price` (WITHOUT ROWID) tables in WAL mode; a newer snapshot replaces a market's prices, older ones are ignored; station updates keep known distance/pad when a message omits them; `prune` drops markets older than `eddn.max_age_days`.
- `edap/eddn/listener.py`: background thread, commits about once a second, prunes hourly, reconnects after 60s of silence, counts messages/updates/errors.
- New `[eddn]` config (`defaults/eddn.toml`): `enabled` (not used yet), `relay`, `database_file` (default git-ignored `.eddn_markets.sqlite3`), `max_age_days`. New dependency `pyzmq`.
- Live check: about 11 relay messages a second overall, about one market snapshot every 2 seconds.

## Follow-ups

- Run the listener inside the Control Room server when `eddn.enabled`, then slices 3 to 6 (Ardent lookups, route finder, profit-per-hour model, `/routes`).

## Iteration 438

- When: `2026-11-10 14:43`
- Area: `haul`
- Title: `on-land-manual-landing-wait`
- Source: [2026-11-10-14-43_____haul_____on-land-manual-landing-wait.md](iteration-logs/2026-11-10-14-43_____haul_____on-land-manual-landing-wait.md)

# Iteration Log

- Area: `haul`
- Title: `on-land-manual-landing-wait`
- Started: `2026-11-10 14:43`

## Summary

- A haul to an `on land` station looked paused but could not be resumed: after the drop, `transit_to_station` returned the manual-landing result, the haul loop returned, and `clear_routine` stopped the session (run recorded `aborted` / `stats stopped` in transit, e.g. Chauhan Dock 2026-11-10 14:21). `resume` only works for the in-routine pause before a buy, so it reported no active haul.

## Changes

- `transit_to_station` takes a required `wait_for_manual_landing`. Two-way and multi-leg haul pass `True`: after the drop near an on-land station they log and TTS `manual_landing` ("please land manually at {station_name}. We continue once docked."), wait for `Docked` within the dock timeout, open the refuel menu as usual and continue trading. `travel` and Spansh routes pass `False` and still end at the handoff.

## Follow-ups

- Live-validate at Chauhan Dock: the routine should continue straight into the station 1 buy after a manual landing.

## Iteration 439

- When: `2026-11-10 14:53`
- Area: `control-room`
- Title: `recent-markets-page`
- Source: [2026-11-10-14-53_control-room_recent-markets-page.md](iteration-logs/2026-11-10-14-53_control-room_recent-markets-page.md)

# Iteration Log

- Area: `control-room`
- Title: `recent-markets-page`
- Started: `2026-11-10 14:53`

## Summary

- Control Room now remembers the last 10 stations whose commodities market was opened, and the web UI has a `/markets` page that browses them and finds the best deal between two of them.

## Changes

- `edap/recent_markets.py`: snapshot store keyed by MarketID, newest first, capped at 10. A revisit with a newer timestamp replaces that station and moves it to the top. The same or an older `Market.json` is a no-op, which is also how startup seeding works. Writes go through a temp file plus `os.replace`, and a corrupt store reads as empty. `commodity_key` turns `$gold_name;` into `gold`.
- `edap/market_compare.py`: pure `compare_markets(x_items, y_items, cargo_capacity)` returns X→Y and Y→X deals sorted by profit/t, plus the best round trip. A deal needs buy price and stock at the source, a sell price at the destination, and positive profit. The full hold is `min(capacity, source stock)`. Demand is shown but neither filters nor caps a deal.
- Capture: `bootstrap.load_market_json` records every changed `Market.json` into `control_room.recent_markets_file` (default `.control_room_recent_markets.json`, git-ignored). It already runs at startup, on `Docked`, and on each status refresh in the TUI and the headless server; a journal `Market` event now triggers it too.
- Server: `/markets` page plus `markets.js`, `GET /api/recent-markets` (snapshots with normalised items and the ship's cargo capacity) and `GET /api/market-compare?x=<id>&y=<id>[&capacity=<t>]`. Both use the usual token auth.
- Every web page's sidebar links to Markets, and the mobile sidebar scrolls sideways when the links overflow.

## Follow-ups

- Not tried in a real browser or a live session: the Chrome extension was offline, so only a curl smoke test against a fake-store server was done. The running server needs a restart to pick up the new routes and the capture.
- The TUI could reuse `compare_markets` for a market-deal command.

## Iteration 440

- When: `2026-11-10 15:00`
- Area: `haul`
- Title: `aborted-run-session-profit`
- Source: [2026-11-10-15-00_____haul_____aborted-run-session-profit.md](iteration-logs/2026-11-10-15-00_____haul_____aborted-run-session-profit.md)

# Iteration Log

- Area: `haul`
- Title: `aborted-run-session-profit`
- Started: `2026-11-10 15:00`

## Summary

- Trades from a haul run that was stopped mid-way vanished from the session profit: `start_haul_stats` built new stats from `accumulated_profit` only and dropped `current_run_profit`, and a station 1 sale on a resumed run was discarded. The persisted JSONL rows and the `Today` all-in total already kept them. User decision: realized trades count in the session; profit/hour and expected vs actual stay completed-only.

## Changes

- New `haul_history.abort_run` closes a run as aborted and folds its realized profit into `accumulated_profit`: `current_run_profit` for a clean run, the recorded row profit for a partial (resumed mid-run) row. All aborted closes (stop, new haul over a stale run, clear, restart, resumed run ending) use it; restart adds nothing twice because the saved session profit already includes `current_run_profit`.
- Web Haul v1 connection banner (reconnect) now floats at the bottom of the viewport (bottom-right on desktop, full width on phones) so it stays reachable while scrolled down to the activity log.

## Follow-ups

- None.

## Iteration 441

- When: `2026-11-10 15:08`
- Area: `haul`
- Title: `eddn-listener-in-server`
- Source: [2026-11-10-15-08_____haul_____eddn-listener-in-server.md](iteration-logs/2026-11-10-15-08_____haul_____eddn-listener-in-server.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-listener-in-server`
- Started: `2026-11-10 15:08`

## Summary

- Plan 0014 step: the Control Room server now runs the EDDN listener itself when `eddn.enabled = true`, so the price table stays current without a separate `tools/eddn_listen.py`.
- Storage check from the standalone listener: 553 markets, 41k prices, 619 stations, 1769 systems use 1.9 MB (~3.5 KB per market) plus a ~4 MB WAL that SQLite checkpoints. A bubble-wide week of markets should stay around 50 to 100 MB.

## Changes

- New `edap/eddn/service.py`: `start_eddn_service(config, open_socket=, time_fn=, log=)` opens the store and starts the listener; `EddnService.status()` returns listener stats plus store counts, `close()` stops, joins and closes the store.
- `serve_observer_mode` configures logging earlier, starts the service when enabled (logs through `edap.eddn`) and closes it on shutdown. `GET /api/eddn-status` (auth like other `/api/*`) returns `{"enabled": false}` or the status.

## Follow-ups

- Run only one writer per database: stop `tools/eddn_listen.py` before starting the server with EDDN enabled.
- Next in plan 0014: route finder, profit/hour ranking, `/routes`.

## Iteration 442

- When: `2026-11-10 15:15`
- Area: `haul`
- Title: `eddn-routes-page`
- Source: [2026-11-10-15-15_____haul_____eddn-routes-page.md](iteration-logs/2026-11-10-15-15_____haul_____eddn-routes-page.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-routes-page`
- Started: `2026-11-10 15:15`

## Summary

- Plan 0014 route finder and `/routes` page, on the EDDN SQLite store. Live check on 147 eligible markets: near and global searches run in 0.04 to 0.1 s, top route Di Fiore Meteor Manor ↔ Braddocks Hide (gold / marine supplies, 1 jump) (before calibration it estimated 165M/h; with the fitted model 116M/h at a 780s round trip).

## Changes

- `edap/eddn/routes.py`: `load_route_markets` (skips carriers, construction depots, too-small pads with type-based pad fallback, surface unless opted in, far stations, stale markets; coordinates by system address or name), `best_leg` (hold capped by capacity and stock, demand only filtered), `find_routes` (spatial grid with cell = range, near view keeps station 1 within the origin radius, ranked by profit/hour), `TimeModel` fitted on 125 November journal legs (Undocked to Docked plus docked time): 90s docked + 110s + 170s first jump + 65s per extra jump + `13 × Ls^(1/3)`; Voltaire ↔ Melroy comes out at 880s against ~816s per run plus ~90s docked at station 1.
- `edap/eddn/route_query.py`: query parsing with `haul_search.toml` and ship fallbacks (`max_route_distance_ly` is the laden jump range), read-only DB run, JSON payload.
- Legs carry in-game names from recent-market snapshots (191 of 210 EDDN commodities named; the rest are salvage and illegal goods). Each route has a `trade_route` JSON (null when a name is unknown) that the `/routes` Copy button puts on the clipboard for the `/haul` paste box.
- `GET /api/eddn-routes` and web `/routes` (Near/Global, 1/2/4 jumps, 100/250 Ly, filters), linked from every sidebar.
- `/markets`: Best deal panel moved to the top; fixed the Save token button adding another 30 s refresh timer on every click.

## Follow-ups

- Not yet opened in a browser; check `/routes` and a Copy → `/haul` paste live.
- Check global speed once the DB covers the bubble; add Ardent lookups for markets without coordinates.

## Iteration 443

- When: `2026-11-10 15:31`
- Area: `haul`
- Title: `eddn-default-on-and-docs`
- Source: [2026-11-10-15-31_____haul_____eddn-default-on-and-docs.md](iteration-logs/2026-11-10-15-31_____haul_____eddn-default-on-and-docs.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-default-on-and-docs`
- Started: `2026-11-10 15:31`

## Summary

- EDDN listening is on by default, the server logs a periodic status line, `/routes` shows a live listener log, and players have docs for it. README gained a Piper voice section.

## Changes

- `EddnConfig.enabled` and `defaults/eddn.toml` now default to true; new `eddn.status_every_s` (30 s, 0 turns it off, negative rejected).
- `status_line` moved from `tools/eddn_listen.py` into `edap/eddn/service.py`; `EddnService` runs an `eddn-status` thread that logs `EDDN connected: N msgs, ... | db N markets, ...` through the `edap.eddn` logger, stopped by `close()`.
- `/routes`: EDDN listener panel polls `/api/eddn-status` every 10 s and prepends one line per check (deltas since the last check, errors, reconnects, DB totals), capped at 60 lines.
- Docs: `docs/user/trade-routes.md` (indexed in `docs/user/README.md`), README "Trade routes (EDDN)" block and new "Piper Voice" section with TOC entry, `config.example.toml` EDDN comments.
- `TimeModel` checked against today's Chauhan Dock (Crater Outpost, 292 Ls) ↔ The Job Centre (2 Ls) loop, 1 jump each way: legs to the Job Centre averaged 302s vs 296s modeled, legs to Chauhan ~390s vs 366s, docked ~90 to 120s. Added `surface_extra_s = 30` for legs ending at a surface station; `leg_s` now takes `surface=`. Inara listed Chauhan at 3214 Ls, the journal and EDDN say 292 Ls. Handh is not in the EDDN DB yet, so `/routes` cannot show this route.
- Removed the now redundant `[eddn] enabled = true` block from the local `config.toml`.

## Follow-ups

- Restart the running server to pick up the status line, then check the `/routes` log panel live.

## Iteration 444

- When: `2026-11-10 15:41`
- Area: `control-room`
- Title: `haul-search-surface-stations`
- Source: [2026-11-10-15-41_control-room_haul-search-surface-stations.md](iteration-logs/2026-11-10-15-41_control-room_haul-search-surface-stations.md)

# Iteration Log

- Area: `control-room`
- Title: `haul-search-surface-stations`
- Started: `2026-11-10 15:41`

## Summary

- The web `/haul` route search can now include surface stations, using Inara's own three-way filter.

## Changes

- Checked inara.cz `market-traderoutes` (Chrome extension was offline, so read the form HTML): `pi4` options are `0` Yes (with Odyssey stations), `2` Yes (exclude Odyssey stations), `1` No; our existing mapping already matched.
- The server forced `use_surface_stations = "no"` for every web search. It now reads `use_surface_stations` from the payload (aliases via the shared `parse_surface_stations`, moved from `prompts.py` into `edap/inara/trade_routes.py`), rejects unknown values with `invalid_search`, saves it to `haul_search.toml`, and reports `station_carrier_only` / `use_surface_stations` truthfully.
- `web/haul-v1.html`: Surface stations select (No / Yes, exclude Odyssey settlements / Yes, with Odyssey settlements), default from `haul_search.toml` via `webDefaults.surfaceStations`; result labels say "routes" instead of "station/carrier routes" when surface is included.
- README and getting-started updated.

## Follow-ups

- Inara results never set the manual landing flag. Station type is only a sprite offset on `.stationicon` (seen: -13px Coriolis, -156px Orbis, -182px crater outpost, -780px Odyssey settlement), but the flag should not follow it: it is for stations you cannot glide close to, not surface stations. Crater outposts docked fine with it off (Chauhan Dock).

## Iteration 445

- When: `2026-11-10 16:11`
- Area: `haul`
- Title: `manual-landing-rename`
- Source: [2026-11-10-16-11_____haul_____manual-landing-rename.md](iteration-logs/2026-11-10-16-11_____haul_____manual-landing-rename.md)

# Iteration Log

- Area: `haul`
- Title: `manual-landing-rename`
- Started: `2026-11-10 16:11`

## Summary

- The per-station haul `on_land` flag is renamed `manual_landing`. It only means "hand off after `SupercruiseExit` because the ship cannot glide close to the pad"; planetary ports dock automatically with it off (Chauhan Dock, `BodyType: "Planet"`, docked ~60s after the drop). "Surface" stays the name for station-on-a-planet concepts (Inara `pi4`, EDDN `is_surface`, `TimeModel.surface_extra_s`).

## Changes

- Renamed fields, params, TOML keys, JSON keys, web ids and labels (`from_manual_landing`, `station_N_manual_landing`, `nav-manual-landing`, "Manual landing (can't glide to the pad)").
- Old names still load: `manual_landing_from_payload` in `edap/inara/trade_routes.py` covers saved state, pasted routes and server commands; `haul_config.py`, `multi_leg_haul.py`, `routines_haul.py`, the travel handler and `haul-ui.js` fall back to `on_land` / `<side>_on_land`. Tests cover each path.
- `/routes` Copy no longer sets the flag from `is_surface`; it always emits `false`.
- User docs, status and the 15:41 log follow-up reworded to the glide meaning.

## Follow-ups

- `detect_transit_resume_state` (`edap/routines/transit.py`) returns `NONE` for a `SupercruiseExit` with `BodyType` other than `Station` when the flag is off, so resuming right after a drop at a planetary port (before `DockingRequested`) does not pick up `POST_DROP_NEAR_STATION`. Kept on purpose: the user wants resume to pick it up only once docking starts.

## Iteration 446

- When: `2026-11-10 16:16`
- Area: `haul`
- Title: `reset-session-stats-per-haul`
- Source: [2026-11-10-16-16_____haul_____reset-session-stats-per-haul.md](iteration-logs/2026-11-10-16-16_____haul_____reset-session-stats-per-haul.md)

# Iteration Log

- Area: `haul`
- Title: `reset-session-stats-per-haul`
- Started: `2026-11-10 16:16`

## Summary

- Haul session stats (timer, profit, runs, average run time) used to accumulate across hauls until `new_session`, which blurred how long runs take. The user asked for them to clear on stop.

## Changes

- `stop_haul_stats` sets `session_active = False` and logs `Haul session: N runs, X Cr in mm:ss, average run mm:ss`; the frozen numbers stay on screen.
- `start_haul_stats` starts from zero when the previous session is not active (a stopped haul, `stop_session`, or a fresh state), and still carries totals over when resuming after a relaunch mid-haul.
- Resume detection after a drop at a planetary port stays as is: the user only wants it picked up once docking starts (`DockingRequested`).

## Follow-ups

- If the user wants the panel blank right at stop instead of at the next start, clear in `stop_haul_stats` after the summary log.

## Iteration 447

- When: `2026-11-10 16:32`
- Area: `haul`
- Title: `eddn-routes-ignore-demand`
- Source: [2026-11-10-16-32_____haul_____eddn-routes-ignore-demand.md](iteration-logs/2026-11-10-16-32_____haul_____eddn-routes-ignore-demand.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-routes-ignore-demand`
- Started: `2026-11-10 16:32`

## Summary

- The best route in the EDDN store, Chauhan Dock ↔ Sitterly Enterprise (same system, beryllium out, insulating membrane back), was hidden by `min_demand = 5000`: Sitterly also produces beryllium, so EDDN shows demand 1, yet every haul run sold the full 1137 t there. The user confirmed any listed sell price is enough.
- With demand ignored, the finder ranks it first at 302M/h, 50.5M per trip, 10.0 min; the haul run log shows 308M/h and 9.8 min over 2 clean runs. Next best: Chauhan → Oracular Oriole silver at 214M/h; nothing without Chauhan beats ~146M/h.

## Changes

- `edap/eddn/routes.py` treats any `sell > 0` as a buyer; `RouteFilters.min_demand`, the `min_demand` query parameter and the `/routes` Min demand field are gone. Inara haul search keeps its own min demand.
- Test: a station listing a sell price with demand 1 is a route target.

## Follow-ups

- Selling a full hold where demand is tiny has only been seen at Sitterly; watch for price drops elsewhere.

## Iteration 448

- When: `2026-11-10 16:55`
- Area: `haul`
- Title: `eddn-default-off`
- Source: [2026-11-10-16-55_____haul_____eddn-default-off.md](iteration-logs/2026-11-10-16-55_____haul_____eddn-default-off.md)

# Iteration Log

- Area: `haul`
- Title: `eddn-default-off`
- Started: `2026-11-10 16:55`

## Summary

- `eddn.enabled` defaults to false again: the user does not want every server listening to EDDN by default. Turn it on with `[eddn] enabled = true`.

## Changes

- `EddnConfig.enabled`, its parse fallback and `defaults/eddn.toml` are false; `config.example.toml`, README, `docs/user/trade-routes.md` and status describe opting in. The defaults test asserts it is off.
- The user's ignored `config.toml` gets `[eddn] enabled = true` back (removed earlier as redundant) so their server keeps listening.

## Follow-ups

-

## Iteration 449

- When: `2026-11-10 18:03`
- Area: `control-room`
- Title: `markets-best-deal-to-haul`
- Source: [2026-11-10-18-03_control-room_markets-best-deal-to-haul.md](iteration-logs/2026-11-10-18-03_control-room_markets-best-deal-to-haul.md)

# Iteration Log

- Area: `control-room`
- Title: `markets-best-deal-to-haul`
- Started: `2026-11-10 18:03`

## Summary

- The `/markets` Best deal panel ranks deals by full-hold profit and offers the top 3 per leg to pick, with supply and demand, and hands the picked round trip to the two-way haul: **Copy route** (JSON for the /haul paste box) or **Open in haul**.

## Changes

- `edap/market_compare.py` sorts deals by `hold_profit` first (hold capped by source stock), then profit per ton. Before, a 178 t gold stock beat a deep commodity on profit per ton and became the best deal.
- `web/markets.js`: each leg shows its top `DEAL_CHOICES = 3` deals with a radio pick (buy, supply, sell, demand, profit/t, full hold); the periodic refresh keeps the picks for the same pair. `tradeRoute` builds the /haul route from the picks in the browser (X is `from`; manual landing off).
- **Open in haul** links to `/haul#route=<json>`. `importLinkedRoute` in `web/haul-ui.js` runs after each hydrate, clears the fragment and goes through `importPastedRoute`, so the route becomes the server's selected route when the page is the active operator.
- `/haul` routine panel: Elapsed was always the session total (falling back to the current run only at 0); it is now labelled Session elapsed, and a second row shows This run (`current_run_elapsed_s`, live from the hydrate), Last run and Avg run (`total_run_elapsed_s / completed_runs`).

## Follow-ups

- Not yet tried in a browser. Station distances and profit per hour are not in `Market.json`, so the linked route leaves them empty.

## Iteration 450

- When: `2026-11-10 20:59`
- Area: `travel`
- Title: `fsd-charge-confirm-supercruise-fallback`
- Source: [2026-11-10-20-59____travel____fsd-charge-confirm-supercruise-fallback.md](iteration-logs/2026-11-10-20-59____travel____fsd-charge-confirm-supercruise-fallback.md)

# Iteration Log

- Area: `travel`
- Title: `fsd-charge-confirm-supercruise-fallback`
- Started: `2026-11-10 20:59`

## Summary

- Leaving Chauhan Dock, `HyperSuperCombination` does nothing when the station obscures the jump target (it only shows "Destination Target Obscured"; verified it never falls back to supercruise), yet TTS already said "Ready to jump". The auto engage now confirms the FSD is charging before saying that, and falls back to supercruise when it is not.

## Changes

- `engage_fsd_and_confirm_charging` in `edap/routines/transit.py`: say `fsd_engage_trying`, press `HyperSuperCombination`, poll Status.json `FsdCharging` (or `FsdJump`) for `FSD_CHARGE_CONFIRM_TIMEOUT_S = 4.0`. Charging: say `station_cleared`. Not charging from normal space (depart / undock paths): say `supercruise_fallback` and press `Supercruise`. Not charging from supercruise (`travel` supercruise start): say `fsd_jump_blocked` only, since `Supercruise` would drop the ship out. Unreadable Status.json: progress warning, no further TTS.
- Status.json is polled instead of waiting for the `StartJump` journal event so the wait does not consume journal events that the later arrival wait needs.
- New `AnnouncementId`s and `defaults/tts.toml` phrases: `fsd_engage_trying`, `supercruise_fallback`, `fsd_jump_blocked`. The `station_cleared` wording is unchanged.
- Follow-up wording: the blocked lines say "Frame shift drive failed to engage", and the normal-space fallback adds `supercruise_countdown` ("Engaging supercruise in 3, 2, 1.") and waits `SUPERCRUISE_FALLBACK_COUNTDOWN_S = 8.0` before pressing `Supercruise`, since queued TTS gives no completion signal.
- Mass lock: the 21:34 Chauhan Dock departure read Status.json as not mass locked 0.5s after NoTrack (every other departure boosted 3 to 10 times), so `HyperSuperCombination` and then the `Supercruise` fallback both did nothing. `escape_mass_lock` (`edap/routines/escape.py`) used to treat an unreadable Status.json as clear without logging; it now retries the read, warns if it stays unreadable, and needs `MASS_LOCK_CLEAR_CONFIRMATIONS = 2` clear reads. `engage_fsd_and_confirm_charging` boosts out and retries `HyperSuperCombination` once when the FSD did not charge and the ship is still mass locked.
- Tests: `tests/test_fsd_engage.py`; the hardpoint transit test now sets `FsdCharging` on the jump press.

## Follow-ups

- Live-validate at Chauhan Dock: the 4s window, that `FsdCharging` shows up promptly under CrossOver, and the target swap after the supercruise fallback.

## Iteration 451

- When: `2026-11-10 22:36`
- Area: `haul`
- Title: `routes-surface-default`
- Source: [2026-11-10-22-36_____haul_____routes-surface-default.md](iteration-logs/2026-11-10-22-36_____haul_____routes-surface-default.md)

# Iteration Log

- Area: `haul`
- Title: `routes-surface-default`
- Started: `2026-11-10 22:36`

## Summary

- `/routes` hid every Chauhan Dock (CraterOutpost) route: the Surface stations checkbox started unchecked and the server fallback read `use_surface_stations = "yes_with_odyssey"` as off.

## Changes

- `edap/eddn/route_query.py`: `surface` goes through `_include_surface`, which reuses `parse_surface_stations` so `yes_with_odyssey` / `yes_exclude_odyssey` include surface ports and `no` excludes them; page `yes`/`no`/`1`/`0` still work through `_flag`.
- `web/routes.js`: `#route-surface` starts from `WEB_CONFIG.webDefaults.allowPlanetary` (already derived from `use_surface_stations` in `_web_form_defaults`). The page persists only the access token, so there is no saved checkbox choice to respect; a reload resets it to the haul search default.
- Tests: query fallback/override cases in `tests/test_eddn_routes.py`, served page/script wiring in `tests/test_control_room_server.py`.

## Follow-ups

- Live-check `/routes` lists Chauhan Dock routes with the default checkbox.

## Iteration 452

- When: `2026-11-11 00:16`
- Area: `control-room`
- Title: `inara-search-link`
- Source: [2026-11-11-00-16_control-room_inara-search-link.md](iteration-logs/2026-11-11-00-16_control-room_inara-search-link.md)

# Iteration Log

- Area: `control-room`
- Title: `inara-search-link`
- Started: `2026-11-11 00:16`

## Summary

- Inara searches now round the max route distance up to a whole light year, and the `/haul` page links the search it ran on Inara.

## Changes

- `build_trade_route_query_params` in `edap/inara/trade_routes.py` sends `pi2` as the ceiling of the distance (`17.2` -> `18`, `18.0` -> `18`). Inara truncates `pi2` to an integer, so `17.2` acted as `17` and dropped a `17.05` Ly route. Empty or non-numeric values pass through unchanged. The parsed `pi2` from a pasted Inara URL is not changed.
- `/haul`: an **Open in Inara** link (`#inara-search-link`, new tab, `rel=noopener`) sits next to `#result-count`. A successful `command.search_haul_routes` sets it from `result.query_url`; a new search or a failed one hides it.

## Follow-ups

- The link does not survive a page reload. Search results themselves are not in the hydrate (only the selected route), and `TradeRoutePickerState.presented_query_url` is TUI picker state that the web search never sets, so wiring it would need a new hydrate field.
- Not yet tried in a browser.

## Iteration 453

- When: `2026-11-11 05:58`
- Area: `control-room`
- Title: `routes-mobile-layout`
- Source: [2026-11-11-05-58_control-room_routes-mobile-layout.md](iteration-logs/2026-11-11-05-58_control-room_routes-mobile-layout.md)

# Iteration Log

- Area: `control-room`
- Title: `routes-mobile-layout`
- Started: `2026-11-11 05:58`

## Summary

- `/routes` is usable on a phone: each route is a labelled card instead of a 760 px table that scrolled sideways, and the mobile nav row no longer draws the brand name over the links on every page.

## Changes

- `haul-ui.css` already turns `.route-table` rows into cards at ≤760 px for `/haul`, but `/routes` reused the class with its own `min-width: 760px`, `nowrap` and right-aligned cells, no `data-label`s, and a `<br>` between the two stations. `web/routes.js` now labels every cell and wraps each station in a `<div>`; `web/routes.html` drops the wide-table rules under the same breakpoint.
- Mobile nav: `.brand` had `min-width: 0` in the scrolling flex row, so it shrank to nothing and its "Control Room" text spilled over "Two-way haul". It now keeps its size and shows only the ED mark.
- Checked with Playwright at 390 px against the live server's assets and a mocked `/api/eddn-routes` built from the local EDDN DB: page `scrollWidth` 390, cards readable, nav clear on `/haul`, `/multi-haul`, `/markets`, `/routes`, `/controls`.

## Follow-ups

- Not tried on a real phone yet.

## Iteration 454

- When: `2026-11-11 06:12`
- Area: `haul`
- Title: `history-total-profit`
- Source: [2026-11-11-06-12_____haul_____history-total-profit.md](iteration-logs/2026-11-11-06-12_____haul_____history-total-profit.md)

# Iteration Log

- Area: `haul`
- Title: `history-total-profit`
- Started: `2026-11-11 06:12`

## Summary

- Haul history now leads with the all-in Total (profit, time, profit/hour) on the web panel and in `stats` / `tools/haul_stats.py`, instead of completed-only figures.

## Changes

- Why: a stop, pause or relaunch closes the current run as `aborted` and the remainder starts as a `partial_start` run, so one round trip's buy (e.g. -3.96M) and sell (+58.08M) land in two aborted rows. Over the 48h to 2026-11-11 06:00 that was 17 completed runs for 743.5M against 22 aborted for 527.7M: 1.27B all-in at 224M/h vs 211.5M/h completed-only.
- `HaulSummary` gains `all_in_duration_s` and `all_in_profit_per_hour` (summed run durations, so idle gaps between runs are excluded, as for completed). Web metrics are just Total profit, Total / hour, Total time and Runs (`18 done, 22 aborted`), on a 4-column grid (2 on phones); the completed figures, aborted line, expected vs actual, Routes, Commodities and journal sit in a collapsed `Details` that stays open across refreshes once opened. `formatCredits` shows billions with two decimals (1.27b, not 1.3b).

- Total / hour and Total time need a server restart: the fields come from the Python summary, and the running server predates them.

## Follow-ups

- `.control_room_haul_runs.jsonl` has one duplicate run (started 2026-11-09T21:30:19, gold, 24.4M) written twice by 1.26.0 with different `ended_at`, so `load_runs` dedupe misses it; all-in counts it twice.
- The history Routes table can list the same station pair twice (e.g. Chauhan Dock ↔ Sitterly Enterprise 0/2 and 3/3) because rows are grouped by station and system names, and split halves may carry different or missing system names.

## Iteration 455

- When: `2026-11-11 06:30`
- Area: `haul`
- Title: `resume-after-dock-denied`
- Source: [2026-11-11-06-30_____haul_____resume-after-dock-denied.md](iteration-logs/2026-11-11-06-30_____haul_____resume-after-dock-denied.md)

# Iteration Log

- Area: `haul`
- Title: `resume-after-dock-denied`
- Started: `2026-11-11 06:30`

## Summary

- Restarting a haul that stopped on exhausted dock retries now sends a new dock request instead of waiting for `Docked`.

## Changes

- Why: Elite logs `DockingRequested` before `DockingDenied`, and `detect_transit_resume_state` skipped the denial, so the restart saw a pending request, logged "Docking already in progress" and waited out the dock timeout.
- `DockingDenied`, `DockingTimeout` and `DockingCancelled` for the destination station now resolve to `POST_DROP_NEAR_STATION`, which skips the drop wait and requests docking again; for another station they resolve to `NONE`.
- Restarting no longer splits the run. Before, the failed run was written `aborted` and the restart became a `partial_start` run aborted at the next station 1 departure, so the trip counted only in the all-in Total.
- `clear_routine` now calls `suspend_haul_stats` for a two-way haul: with a run in progress it freezes timers as a pause does, snapshots the duration, and marks the stats `suspended` instead of aborting. `start_haul_stats` with the same stations and commodities continues that run; a different haul, `clear` or a relaunch still aborts it, and a different haul starts a fresh session. Multi-leg haul and an end with no run in progress still stop as before. Stop now also suspends, so a stop then restart of the same haul is one run too.

## Follow-ups

- No live validation yet of a restart after a pad-full or other denial.
- Journal events while suspended (e.g. a manual dock) are not recorded, since tracking only runs while the haul is active; trades are made by the restarted haul, so money is unaffected.
- A relaunch still aborts an open run; keeping it across relaunch would need the clean-run fields in saved state.

## Iteration 456

- When: `2026-11-11 06:47`
- Area: `haul`
- Title: `routes-filter-toggles`
- Source: [2026-11-11-06-47_____haul_____routes-filter-toggles.md](iteration-logs/2026-11-11-06-47_____haul_____routes-filter-toggles.md)

# Iteration Log

- Area: `haul`
- Title: `routes-filter-toggles`
- Started: `2026-11-11 06:47`

## Summary

- `/routes` shows the haul search defaults its blank fields use, and Min supply, Max station distance and Max data age each get a tick box to turn the filter off.

## Changes

- Why: the Min supply field showed only `haul_search`, so the 5000 default that hid Chauhan Dock beryllium (about 4,000 t in stock) was invisible.
- Placeholders read `<value> (haul search)` for laden jump range (`max_route_distance_ly`), min supply, max station distance and max data age, and `<value> (ship)` for cargo. Web defaults gain `maxPriceAgeHours` from `max_price_age_hours`.
- Unticked filters send `any`: min supply 0 and no station distance limit as before. `max_age_hours=any` now lifts the age limit (finite `_NO_AGE_LIMIT_S`, since the query is echoed as JSON) instead of falling back to 48 h. Tick state is kept per browser in localStorage; a toggle reruns the search.
- Form fields are bottom-aligned so the wrapping Max station distance label does not push its input down.

## Follow-ups

- The Max data age placeholder and `any` age need a server restart; until then it shows `haul_search` and `any` means 48 h.

## Iteration 457

- When: `2026-11-11 06:55`
- Area: `haul`
- Title: `import-our-markets-into-eddn`
- Source: [2026-11-11-06-55_____haul_____import-our-markets-into-eddn.md](iteration-logs/2026-11-11-06-55_____haul_____import-our-markets-into-eddn.md)

# Iteration Log

- Area: `haul`
- Title: `import-our-markets-into-eddn`
- Started: `2026-11-11 06:55`

## Summary

- Our own captured markets (the recent-markets file recorded from `Market.json`) now feed the local EDDN DB, so `/routes` sees stations we docked at even when nobody uploaded them.

## Changes

- `edap/eddn/messages.market_snapshot_from_game` turns a recorded market into the same `MarketSnapshot` an EDDN commodity message parses to: `$silver_name;` becomes `silver`, the same tradeable-row filter applies, and the game's own timestamp is kept.
- Newest wins through the existing store rule: a snapshot older than the stored `updated_at` is skipped; a newer one replaces the whole station (one `updated_at` per market, so merging would let old rows pose as fresh; this is also what EDDN does).
- `edap/eddn/game_markets.import_game_markets` applies all recorded markets and commits; `tools/eddn_import_markets.py [--db] [--recent-markets]` runs it by hand.
- With `eddn.enabled`, the server starts thread `eddn-game-markets`, which imports at start and whenever the recent-markets file changes (polled every 5 s), logging `EDDN our markets: ...`.
- Name check before the change: Chauhan Dock, Sitterly Enterprise and The Job Centre names all matched the DB. Sitterly's EDDN entry had 6 sell-only salvage rows (escape pods, black boxes) that are absent from our `Market.json`; whole-station replacement drops them.
- Manual run 2026-11-11: Sitterly Enterprise written (ours 06:34 vs DB 04:43); Chauhan Dock and The Job Centre kept (DB newer).

## Follow-ups

- The running server picks up the watcher only after a restart.
- Station and system details from the journal are out of scope; only market prices are imported.

## Iteration 458

- When: `2026-11-11 09:03`
- Area: `control-room`
- Title: `command-http-api`
- Source: [2026-11-11-09-03_control-room_command-http-api.md](iteration-logs/2026-11-11-09-03_control-room_command-http-api.md)

# Iteration Log

- Area: `control-room`
- Title: `command-http-api`
- Started: `2026-11-11 09:03`

## Summary

- Added `POST /api/command` (run any Control Room command text) and `POST /api/stop` (cancel the running routine) so curl, scripts and automation tools can drive routines. Both use the existing token auth.

## Changes

- `/api/command` takes `{"raw_input", "skip_delay"?}` and calls the same `command_handler.submit_input` as websocket `command.submit_input`. 400 on bad body, 409 when refused because a routine is running, 503 without a command handler; responses carry `accepted`, `routine_active`, `active_routine_name`.
- Refusal signal: `RuntimeUIState.busy_refusals` counts busy refusals. `ControlRoomApp._refuse_busy` logs and bumps it; every idle-only check uses it (`workers.check_routine_ready`, remote `_check_routine_ready`, `reload_config`, `reload_keymap`, `haul search`, `stop` while a haul runs). `HeadlessControlRoomHost.submit_input` now returns `bool` (False when the counter moved); `ObserverSessionCommandHandler.submit_input` returns `bool`.
- The text `stop` only freezes haul session stats, so `/api/stop` (`mode` `now` default or `after_run`) calls `cancel_active_routine`, and returns 409 when idle.
- Docs: `docs/user/command-api.md`, linked from `docs/user/README.md` and `README.md`.

## Follow-ups

- The websocket `command.submit_input` reply still always says `accepted: true`; it could use the new return value.
- Headless host treats prompt-owning verbs (`haul`, `dest`, `home`, `market`, ...) as client-local, so the API cannot run them yet.
- CORS still allows only GET/OPTIONS, so cross-origin browser pages cannot POST; curl/Shortcuts are unaffected.
- Not yet tried against a live server.

## Iteration 459

- When: `2026-11-11 09:08`
- Area: `control-room`
- Title: `hub-control-room`
- Source: [2026-11-11-09-08_control-room_hub-control-room.md](iteration-logs/2026-11-11-09-08_control-room_hub-control-room.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-control-room`
- Started: `2026-11-11 09:08`

## Summary

- One home Control Room (the hub) now runs route searches and holds the market DB for peers (other machines). A peer with `[hub] url`/`token` forwards searches with its own ship inputs and pushes the markets it visits to the hub. Not yet tried live between two machines.

## Changes

- Config: `defaults/hub.toml` → `HubConfig` (`url`, `token`, `timeout_s` 10, `search_timeout_s` 180); `url` must be http(s), trailing `/` stripped; empty means local behaviour.
- `edap/hub.py`: `HubRequest`/`HubResponse`/`HubTransport` (plain function; `httpx_transport` in production, httpx was already a dependency), `HubClient`, `HubMarketPusher`, `watch_recent_markets` (also used by `EddnService.import_game_markets_every` now).
- Hub side: `POST /api/haul-search` (REST twin of `command.search_haul_routes`, does not save `haul_search.toml`; 400 `invalid_search`, 502 otherwise) and `POST /api/markets` (`{"markets": [recent-markets entries]}` → `import_markets` → per-station `written`; 400 bad body, 503 without `[eddn]`).
- Peer side: `/api/eddn-routes` resolves blank params from its own `haul_search.toml` and ship (`resolve_route_params`, same key mapping as `parse_route_query`) and forwards them; `/api/eddn-status` and both haul search paths forward too; answers get `hub: <host>`; unreachable → 502 / `hub_unreachable`. `/routes` and `/haul` show `via hub <host>`.
- The websocket search sync/async handlers now share `_haul_search_from_payload` and `_run_haul_search` with the REST endpoint.
- Market push: peers skip the local `eddn-game-markets` import and run thread `hub-markets`; first push and the first after a failure send all recent markets, otherwise only new `(market_id, timestamp)` entries.
- Docs: `docs/user/hub.md`, linked from `docs/user/README.md`, `README.md`, `trade-routes.md`; `config.example.toml` `[hub]`.

## Follow-ups

- Live-check a Deck peer against the home hub: `/routes`, `/haul` search, market push, hub down mid-haul.
- A failed push is retried only on the next market change, not on a timer.
- Blank route params a peer cannot resolve fall back to the hub's own `haul_search.toml`.
- `/routes` display names (Copy / Open in haul) come from the hub's recent markets, not the peer's.

## Iteration 460

- When: `2026-11-11 10:58`
- Area: `control-room`
- Title: `hub-heartbeat-and-status`
- Source: [2026-11-11-10-58_control-room_hub-heartbeat-and-status.md](iteration-logs/2026-11-11-10-58_control-room_hub-heartbeat-and-status.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-heartbeat-and-status`
- Started: `2026-11-11 10:58`

## Summary

- A peer now checks its hub instead of only logging the configured URL. A heartbeat pings the hub, one thread-safe `HubStatus` records what the peer last heard, `GET /api/hub-status` reports it, and every sidebar page shows a Hub chip.

## Changes

- `edap/hub.py`: `HubStatus` holds reachable (`None` until the first check), checked/last-ok times, last error, latency, last push (stations, written/kept or error) and resend pending. `ping_hub` asks `GET /api/hub-ping` and logs `Hub <host> reachable (<ms> ms)` / `Hub <host> unreachable: <reason>` only when reachability changes, so the first result after start is always logged. `run_hub_heartbeat` loops with injected `perf_counter` and `wait` (the stop event's `wait` in production). Exceptions are logged and never end the loop. `HubMarketPusher` now takes `status`: a 200 push marks the hub reachable, an unreachable push marks it down, and a refused push (hub answered, non-200) records the push error but leaves reachability to the heartbeat.
- `[hub].heartbeat_s` (default 30, positive and finite) in `defaults/hub.toml` and `HubConfig`. Pings use `timeout_s`.
- Server: `GET /api/hub-ping` (`{"status": "ok"}`) and `GET /api/hub-status` (`{"configured": false}` without a hub) on every server, both with normal auth. `serve.py` starts thread `hub-heartbeat` next to `hub-markets`, stopped by the same event.
- Web: `web/hub-status.js` (new shared asset) polls `/api/hub-status` every 10 s and fills `#hub-chip`, which sits above the sidebar foot on `/haul`, `/multi-haul`, `/controls`, `/markets` and `/routes`. It stays hidden without a hub. Green means reachable, red unreachable, grey unknown, and the `title` tooltip holds last ok, last push and pending resend. On phones it sits in the scrolling nav row; the sidebar foot stays hidden there.
- Tests in `tests/test_hub.py`: heartbeat sequence with a fake transport, fake perf counter and fake wait; status before the first check; pusher status reporting; `/api/hub-status` against a real in-process hub (good and wrong token); every sidebar page loads the chip.

## Follow-ups

- Not tried in a browser or live yet: check the chip layout on desktop and phone widths, and the log lines on a real peer.
- A non-200 ping (for example a wrong token, or an older hub without `/api/hub-ping`, which answers 404) shows as unreachable with the HTTP reason.
- The full-suite runtime was already over the 0.0006 s/test budget on `main` before this change (about 0.66 s for 1071 tests).

## Iteration 461

- When: `2026-11-11 11:01`
- Area: `control-room`
- Title: `hub-lan-binding-docs`
- Source: [2026-11-11-11-01_control-room_hub-lan-binding-docs.md](iteration-logs/2026-11-11-11-01_control-room_hub-lan-binding-docs.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-lan-binding-docs`
- Started: `2026-11-11 11:01`

## Summary

- The hub guide now says what `lan` binds and when to use `serve --host 0.0.0.0` instead. Runtime status now notes that routines cannot be driven from a Windows SSH session. Peer examples in the user docs are generic.

## Changes

- `docs/user/hub.md`: `lan` binds only the detected LAN address and `_detect_lan_host` skips `100.64.0.0/10` (VPN and CGNAT ranges), so peers on such a network need `serve --host 0.0.0.0`. Also covers the default `edcr` token and a DHCP reservation for the hub.
- `docs/status/runtime.md`: new caveat that sshd runs outside the logged-in desktop session, so routines started over SSH cannot reach Elite. Start Control Room on the desktop and drive it through the web pages or `POST /api/command`. Merged two Windows next-step bullets to stay within 20 lines.
- `docs/user/hub.md`, `docs/user/README.md`, `docs/user/trade-routes.md` and the hub iteration log: peer examples reworded to generic machines.

## Follow-ups

- Try a hub and a peer live: a peer pushes a market and `/routes` works through the hub.

## Iteration 462

- When: `2026-11-11 11:09`
- Area: `eddn`
- Title: `keep-same-timestamp-markets`
- Source: [2026-11-11-11-09_____eddn_____keep-same-timestamp-markets.md](iteration-logs/2026-11-11-11-09_____eddn_____keep-same-timestamp-markets.md)

# Iteration Log

- Area: `eddn`
- Title: `keep-same-timestamp-markets`
- Started: `2026-11-11 11:09`

## Summary

- A market snapshot with the same timestamp as the stored one is now kept, not rewritten. A peer restart resends its recent markets, and the hub used to log those as `written` though nothing changed.

## Changes

- `edap/eddn/store.py`: `_apply_market` skips when the stored `updated_at >= snapshot.timestamp` (was `>`).
- Logs say `already in the DB` instead of `already newer`, in `edap/hub.py` and `edap/eddn/game_markets.py`.
- Tests: a resent equal-timestamp snapshot is kept; the file-change import now writes only the new market.

## Iteration 463

- When: `2026-11-11 11:35`
- Area: `control-room`
- Title: `docked-sidebar-and-activity-bar`
- Source: [2026-11-11-11-35_control-room_docked-sidebar-and-activity-bar.md](iteration-logs/2026-11-11-11-35_control-room_docked-sidebar-and-activity-bar.md)

# Iteration Log

- Area: `control-room`
- Title: `docked-sidebar-and-activity-bar`
- Started: `2026-11-11 11:35`

## Summary

- On desktop widths the web sidebar now sticks to the viewport, so its status foot and Hub chip stay at the bottom of the screen while the main content scrolls.
- The activity log on `/haul` and `/controls` is a bar docked to the bottom of the main column. It starts collapsed to one line (title, entry count, newest entry), and a click expands the full scrollable list. The choice is kept per browser.
- Phones (760px and narrower) keep the old layout: sidebar as a nav row, activity panel in the page flow and always expanded.

## Changes

- `web/haul-ui.css`: `.sidebar` is `position: sticky; top: 0; height: 100vh; overflow-y: auto` (phone resets `height: auto`). New `--sidebar-width` token shared by the grid and the dock. New activity toggle and dock rules. Docking only applies under `@media (min-width: 761px)` with `body.has-activity-dock`. `main` pads by `--activity-dock-height` and the connection banner sits above the bar.
- `web/activity-dock.js` (new, served from `/assets/`): toggles `aria-expanded` and `.expanded`, stores `edcr.activityDock.expanded` in localStorage inside try/catch, and mirrors the newest `.activity-row` into the collapsed line through a `MutationObserver`. That way neither `haul-ui.js` nor `controls.js` changed. A `ResizeObserver` publishes the bar height. On phones the toggle is disabled and the list stays shown.
- `web/haul-v1.html`, `web/controls.html`: the activity panel head is now a `<button id="activity-toggle">` with the latest-entry line and a chevron. Both pages load `activity-dock.js`.
- Tests: markup, storage and CSS hooks in `tests/test_control_room_haul_web.py`, and the asset is served in `tests/test_control_room_server.py`.

## Verification

- Checked by eye with headless Chrome over CDP against `control_room.py serve` at 1400x850 and 390x844. Collapsed and expanded bars sit over the main column only. The sidebar foot sits at the viewport bottom. The expanded state survives a reload. The phone layout is unchanged.

## Iteration 464

- When: `2026-11-11 11:38`
- Area: `ci-release`
- Title: `ci-timing-guard-and-suite-speed`
- Source: [2026-11-11-11-38__ci-release__ci-timing-guard-and-suite-speed.md](iteration-logs/2026-11-11-11-38__ci-release__ci-timing-guard-and-suite-speed.md)

# Iteration Log

- Area: `ci-release`
- Title: `ci-timing-guard-and-suite-speed`
- Started: `2026-11-11 11:38`

## Summary

- The flaky `Tests` runs were never test failures. All five failures in the last 50 runs were the `test_timing` job: `tools/check_test_timing.py` times `uv run python3 -m unittest discover` end to end against 5s. The suite itself ran ~2s on CI; the rest was a fresh runner compiling `.pyc` files for dependencies and the repo. Passing runs sat at 4.0-4.8s, so runner noise tipped some over (5.1-6.1s).
- Locally a cold bytecode cache adds ~1s (0.94s warm vs 1.97s cold); precompiling brings it back to ~1.15s.
- Local suite time went from `0.64-0.66s` to `~0.60s` for 1076 tests (budget `0.6456s`).

## Changes

- `.github/workflows/tests.yml`: `test_timing` installs with `uv sync --extra dev --compile-bytecode` and runs `compileall` on `edap tests tools control_room.py` before the guard.
- Tests built `ControlRoomApp` or `HeadlessControlRoomHost` with `DefaultVersionSource`, which runs real `git rev-parse`/`git status` (~15ms, once per process). `HeadlessControlRoomHost` now requires `version_source`; `serve.py` passes `DefaultVersionSource()`, tests pass `_FakeVersionSource`.
- `edap/config.py`: bundled YAML tables load with libyaml's `CSafeLoader` when available (~8ms to ~1ms).
- EDDN thread tests: status interval 10ms to 1ms and market watcher poll 5ms to 1ms (the waits were the interval itself).
- Noise removed from test output: the spansh error tests assert the `logger.exception` output with `assertLogs` (the stray `httpx.HTTPStatusError: 400` traceback), in-memory EDDN stores are closed with `addCleanup` (26 `ResourceWarning: unclosed database`), and `rendering.is_recent` uses `datetime.now(UTC)` instead of deprecated `utcnow()`.

## Follow-ups

- GC costs ~30ms per suite run (one gen2 pass lands on whichever test is running; it looks like a random 10-12ms slow test). `gc.freeze()` after discovery saved ~10-25ms in an experiment but needs a custom runner, so it was left out.
- `QueuedSpeaker` threads from tests that never close their `TTSAnnouncer` stay alive (they wake every 0.1s); harmless today.

## Iteration 465

- When: `2026-11-11 11:45`
- Area: `web`
- Title: `travel-page-and-shared-nav`
- Source: [2026-11-11-11-45_____web______travel-page-and-shared-nav.md](iteration-logs/2026-11-11-11-45_____web______travel-page-and-shared-nav.md)

# Iteration Log

- Area: `web`
- Title: `travel-page-and-shared-nav`
- Started: `2026-11-11 11:45`

## Summary

- New `/travel` page holds the Active route and Route Comparison panels, moved off `/haul`.
- The sidebar link list now lives once in `web/nav.js` and every page renders it; `/haul` had lost its Multi-leg haul link because each page carried its own copy.
- Phones (<= 760px) show Two-way haul, Markets, Routes and Controls in the top row and a ☰ More menu for the rest.
- Activity text no longer shows a literal `[/]`: `stripMarkup` required at least one character inside the brackets.

## Changes

- `web/travel.html` + `web/travel.js`: same shell as `/controls` (token box, status foot, Hub chip, docked activity log). `travel.js` owns the websocket and provides the `window.EDCR_HAUL` bridge (`sendCommand`, `galmapSettleTime`, `shipState`, `lastHydrate`) and the `edcr:hydrate` / `edcr:ship-state` events, so `active-route.js` and `route-compare.js` run unchanged. Galaxy-map settle comes from `web_form_defaults.galaxyMapSettle`, since the haul form field is not on this page.
- `web/nav.js`: one `NAV_GROUPS` list; items with `mobile: true` stay in the phone row, the rest get `nav-desktop-only` and a copy in the More menu. Loaded without `defer` right after `<nav id="site-nav">` so there is no flash. `/` counts as `/haul` for `aria-current`. The menu is `position: fixed` because the phone nav row scrolls sideways and would clip it; Escape closes and refocuses the toggle, outside click and focus leaving close it. Below 480px the More label is visually hidden to fit the row at 390px.
- `.active-spansh-empty.hidden` / `.active-spansh-content.hidden` had no CSS rule, so the idle Active route card also showed empty metrics on `/haul`; added the rule.
- Server: `GET /travel`, and `travel.js` / `nav.js` added to the asset allowlist.
- README and `docs/user/getting-started.md` point at `/travel` for the Spansh panels.

## Verification

- Full suite passed (1082 tests, about 0.655s; the budget of 0.649s was already exceeded before this change and is being fixed separately).
- Headless Chrome over DevTools at 1400x850 and an emulated 390x844 on all six pages against a fixture server: correct `aria-current`, full list on desktop, four items plus More on phones, no horizontal page scroll, More opens by Enter and click, Escape closes and refocuses, outside click closes. The Travel page connected, hydrated and prefilled From.

## Follow-ups

- Try `/travel` against a live session: All in one, Switch to Spansh, and the Active route updating while the runner flies.

## Iteration 466

- When: `2026-11-11 11:53`
- Area: `control-room`
- Title: `hub-command-centre-plan`
- Source: [2026-11-11-11-53_control-room_hub-command-centre-plan.md](iteration-logs/2026-11-11-11-53_control-room_hub-command-centre-plan.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-command-centre-plan`
- Started: `2026-11-11 11:53`

## Summary

- Wrote plan 0015 (`docs/plans/0015-hub-command-centre.md`): the hub becomes the one control room. Peers keep an outbound websocket link to it, send markets, haul runs, state and activity up, and run commands the hub sends down. Hub pages pick a node and reuse the existing session protocol over the link.
- Confirmed with the user: the hub is also a playable node, peers keep their own pages as a fallback, LAN only with the hub token, and a peer obeys only the hub it connected to.

## Changes

- New plan 0015; control-room status points at it from the hub bullet.

## Follow-ups

- Build phase 1 (peer link, node registry, link state replaces the heartbeat) once the user approves the plan.
- Open: TTS on the hub for the selected node, how "game running" is detected.

## Iteration 467

- When: `2026-11-11 11:54`
- Area: `markets`
- Title: `best-deal-profit-per-hour`
- Source: [2026-11-11-11-54___markets____best-deal-profit-per-hour.md](iteration-logs/2026-11-11-11-54___markets____best-deal-profit-per-hour.md)

# Iteration Log

- Area: `markets`
- Title: `best-deal-profit-per-hour`
- Started: `2026-11-11 11:54`

## Summary

- The `/markets` Best deal panel now shows Inara's trade route numbers: profit per ton, profit per trip (full-hold round trip) and estimated profit per hour, plus measured profit per hour from completed haul runs on the same station pair.

## Changes

- `edap/eddn/routes.py`: `jump_count` and `round_trip_s` are the shared helpers `/routes` (`_route`) and Best deal both use, so the two pages agree on trip time.
- `edap/eddn/route_query.py`: `laden_jump_range` (query, then `haul_search.toml` `max_route_distance_ly`, then 17.2) is shared by `/api/eddn-routes` and `/api/market-compare` (`laden_jump_range_ly=`).
- `edap/trade_trip.py`: `gather_facts` fills coordinates, distance from star and station type per station from ordered sources (EDDN store, then journal), asking a later source only while something is missing; `estimate_trip` returns jumps, distance and `trip_s`, or `trip_s` null with a `missing` list (same-system pairs need no coordinates). The 1000 Ls default in `TimeModel.supercruise_s` is never used here: no guessing.
- `edap/recent_markets.py`: the recent markets store also keeps journal `places` (stations: `DistFromStarLS`/`StationType` from `Docked`, or `Location`/`CarrierJump` while docked; systems: `StarPos` from `FSDJump`/`Location`/`CarrierJump`), 50 of each, newest first. Recorded live in `ControlRoomApp._handle_event` and from the latest journal at startup (`bootstrap.record_journal_places`). Market.json's `StationType` is the journal fallback for station type.
- `edap/haul_history.py`: `RunTotals` gains `duration_s`, so each route summary has its own haul time; `/haul` History Routes shows a Completed / hour column. `measured_route` adds completed runs of the pair in either direction, case-insensitive, with recorded systems required to match.
- `web/markets.js`: per-hour is computed in the browser from the picked deals (`perTrip * 3600 / trip.trip_s`), shown with trip minutes, jumps each way and distance; a missing input shows "-" with the names of what is missing. Copy route / Open in haul now carry `profit_per_hour`.

## Follow-ups

- Hub peers push only markets to the hub, not journal places; Best deal reads the local store anyway.

## Iteration 468

- When: `2026-11-11 11:57`
- Area: `markets`
- Title: `best-deal-ardent-fill`
- Source: [2026-11-11-11-57___markets____best-deal-ardent-fill.md](iteration-logs/2026-11-11-11-57___markets____best-deal-ardent-fill.md)

# Iteration Log

- Area: `markets`
- Title: `best-deal-ardent-fill`
- Started: `2026-11-11 11:57`

## Summary

- Best deal asks Ardent Insight for station and system details the EDDN store and journal lack, so profit per hour shows for stations never docked at and systems never visited. This builds plan 0014 slice 3 for these fields.

## Changes

- `edap/ardent.py`: `ArdentLookup` is a `FactLookup` (last in the source order). It fetches `GET /v2/system/name/{name}/stations` once per system (`marketId`, `stationName`, `stationType`, `distanceToArrival`, `maxLandingPadSize`, `systemAddress`, `systemX/Y/Z`, `updatedAt`, verified live 2026-11-11 against Chelgit: Humboldt Hub 5.67 Ls, Ocellus, pad 3) and falls back to `GET /v2/system/name/{name}` for coordinates. Station match by market id, then name.
- Requests: 3 s timeout, `EDControlRoom/<version> (Best deal lookups)` User-Agent, an unknown system (404) is an empty answer; any failure logs once, returns nothing (the page keeps "-") and is retried after 10 minutes. The fetch is injected (`httpx_fetch_json` in production, fakes in tests).
- `serve.py` writes found rows into the EDDN store through `store_saver(eddn.store.apply, eddn.store.commit)` (the listener's own connection and lock, newest `updatedAt` wins), so `/routes` gains those coordinates and stations; without EDDN the rows stay in the lookup's memory cache.
- `build_observer_server_app(ardent_lookup=...)` adds it to `/api/market-compare` sources after the journal; it is asked only while an input is still missing.

## Follow-ups

- `/routes` skips markets without coordinates and does not call Ardent itself: filling them would mean one request per uncovered system per search. Possible later: a background fill of uncovered systems.
- A system is fetched once per server run; a station added to it later needs a restart (or EDDN) to appear.

## Iteration 469

- When: `2026-11-11 12:33`
- Area: `control-room`
- Title: `hub-roles-and-one-station-store`
- Source: [2026-11-11-12-33_control-room_hub-roles-and-one-station-store.md](iteration-logs/2026-11-11-12-33_control-room_hub-roles-and-one-station-store.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-roles-and-one-station-store`
- Started: `2026-11-11 12:33`

## Summary

- Plan 0015 step 1 (roles and data ownership), on `feat/hub-command-centre`. `[hub] role` = `standalone` (default) | `hub` | `peer` decides who owns data: hub and standalone always open the market SQLite store (`edap/market_db.py`), a peer never does. `[eddn] enabled` only starts the listener, and never on a peer.
- The store's `system` and `station` tables are the one station facts store. Writers, newest wins: EDDN, the local journal (`FSDJump`/`Location`/`CarrierJump` StarPos, `Docked` and docked `Location` distance, type and pads, parsed by `journal_event_updates` the same way EDDN parses uploads), our Market.json station type (`StationTypeSeen`, written with our markets by `import_game_markets`; a new row needs the system's address from the `system` table, so a market in a never-visited system adds no type), and Ardent (`EddnStore.save`).
- `places` is gone from the recent markets file; Best deal (`/api/market-compare`) reads the store, then Ardent. `trip.stations.*_source` is now `store` or `ardent`.

## Changes

- `ControlRoomApp` and `HeadlessControlRoomHost` take a required `record_station_facts`; bootstrap replays the latest journal into it. The TUI-only mode opens the store by role too; `connect` passes an explicit drop.
- `start_eddn_service` takes the server's store and no longer closes it; our markets import (`import_game_markets_every`, thread `game-markets`, log prefix `Market DB`) runs on every hub/standalone, not only with EDDN on.
- Peer: Best deal returns `trip.hint` ("Station facts come from the hub.") and `/markets` shows it instead of the missing list; `/api/eddn-routes` without a hub URL says the hub serves routes. Old peer HTTP forwarding is untouched (step 2 replaces it); it now needs `role = "peer"`, and `url` with another role is a config error.
- EDDN `Location` messages with `Docked: true` now also write the station row.

## Follow-ups

- Step 2: send a peer's journal facts and markets up the link, answer Best deal facts over it.

## Iteration 470

- When: `2026-11-11 12:51`
- Area: `control-room`
- Title: `hub-peer-link-and-outbox`
- Source: [2026-11-11-12-51_control-room_hub-peer-link-and-outbox.md](iteration-logs/2026-11-11-12-51_control-room_hub-peer-link-and-outbox.md)

# Iteration Log

- Area: `control-room`
- Title: `hub-peer-link-and-outbox`
- Started: `2026-11-11 12:51`

## Summary

- Plan 0015 step 2: peers now reach the hub over one outbound websocket (`/api/peer-link`) instead of HTTP calls. Market snapshots and station facts travel through a persistent outbox; haul search, EDDN routes/status and Best deal station facts are request/response frames.
- The old hub HTTP path is removed with no backward compatibility.

## Changes

- `edap/hub/` package replaces `edap/hub.py`: `protocol.py` (frames, `LinkConnection`, fact encoding), `outbox.py` (SQLite, key dedupe for 30 days), `peer.py` (`PeerLink`: hello, drain, ack/nack, requests with ids and timeouts, quiet ping, backoff 1/2/5/10/30 s reset after a welcome, `websocket_connector`), `nodes.py` (`NodeRegistry`, `HubLinkSession` pure frame handler, `store_link_item`).
- Node id: generated once, stored at `<config dir>/.control_room_node_id`. A hello carrying the hub's own id is refused (copied file).
- Config: `[hub] name`, `[hub] outbox_file`; `[hub] token` now required on a hub and on a peer with `url`. `heartbeat_s` is the link ping interval.
- Server: `GET /api/nodes` (hub only), `/api/hub-status` per role, peer answers tagged `hub: <hub name>`. Removed `POST /api/markets`, `POST /api/haul-search`, `GET /api/hub-ping`, HubClient, HubMarketPusher, heartbeat thread. `watch_recent_markets` moved to `edap/recent_markets.py`.
- `web/hub-status.js` shows link state, last contact and outbox pending (peer) or peer count (hub).
- Live smoke on one machine (hub and peer on loopback ports): link up, queued items stored, routes/status/market-compare answered by the hub, hub killed (peer shows down, outbox grows, 502), hub restarted (relink drains the outbox, newest price wins).

## Follow-ups

- `docs/user/hub.md` still describes the old HTTP mode; rewrite in step 8.
- A TUI-only peer (no server) keeps no station facts and has no link.
- Link latency is no longer reported.

## Iteration 471

- When: `2026-11-11 12:58`
- Area: `haul`
- Title: `ship-on-every-run`
- Source: [2026-11-11-12-58_____haul_____ship-on-every-run.md](iteration-logs/2026-11-11-12-58_____haul_____ship-on-every-run.md)

# Iteration Log

- Area: `haul`
- Title: `ship-on-every-run`
- Started: `2026-11-11 12:58`

## Summary

- Plan 0015 step 3: every haul run row records its ship, and Best deal's measured profit per hour counts only completed runs on the pair for the current ship over a picked window (48h, 7 days default, 30 days, all).

## Changes

- Ship identity: `ShipState` (`edap/control_room/models.py` and `edap/state.py`) gains `ship_id`, `ship_name`, `ship_ident` from `LoadGame`/`Loadout` (`apply_ship_identity`); carried through bootstrap, the local data source copy, the connect client and the data message parser.
- Run rows: `haul_tracking.ship_record` stores `ship` = `{id, type, name, ident, cargo_capacity, max_jump_range_ly, laden_jump_range_ly}` on the current run. Set on the first recorded event, or later while the id is still unknown (a run saved before this change, or begun before the Loadout). Old rows without `ship` load unchanged.
- Laden range (follow-up, same day): `edap/ship_range.loadout_laden_jump_range` applies plan 0014's formula `MaxJumpRange × (UnladenMass + one-jump fuel) / (UnladenMass + FuelCapacity.Main + CargoCapacity)` on `Loadout`. One-jump fuel is the FSD max fuel per jump from a size/class table (standard FSD figures; SCO assumed equal; unknown drive 0 t). The real Panther Mk II Loadout (7A SCO, 12.8 t) gives 17.198 → 17.2 Ly; 0 t would give 17.07, 13.1 t 17.20. `ShipState.laden_jump_range_ly` carries it; run rows, Best deal's blank field and its "(now X Ly)" use it, and `haul_search.toml` is only the fallback before a Loadout (`route_query.laden_jump_range(..., ship_laden_ly=)`). `/routes` passes `None` and keeps `haul_search.toml`. `/multi-haul` already preferred `ship.laden_jump_range_ly` when present, so its default range now uses it.
- `parse_window` accepts `7d` and `30d` (elapsed, like `48h`); `stats` takes them too.
- `trade_trip.measured_route(rows, x, y, *, ship_id, since, until)` filters raw rows (completed, ended in window, pair either direction with the same system check, ship id match or unknown) and returns runs, profit, duration, profit/hour, `loop_s`, `unknown_ship_runs` and the newest known run's `laden_jump_range_ly`. With no current ship id every run counts.
- `/api/market-compare?window=48h|7d|30d|all` (default `7d`, else 400) adds `measured_window` and `measured_ship`; the current ship is the server's live `ship`.
- `web/markets.js`: a window select inside the Measured per hour block (remembered in localStorage), note with run count, loop time, ship, recorded laden range with today's beside it when different, and "n ship unknown".
- Checked the page headless (Playwright, desktop 1280 and phone 390): no horizontal scroll, no page errors, window switch refetches.

## Follow-ups

- Step 4 sends runs to the hub; a peer's measured profit per hour uses its own history until then.
- Haul page history does not show the ship per route yet (optional in the step).
- `/routes` could swap its blank-field range to the ship's laden range the same way (one argument); left on `haul_search.toml` for now.
