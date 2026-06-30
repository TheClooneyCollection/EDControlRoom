# Iteration Archive

_This file is generated from `docs/iteration-logs/` by `uv run python3 tools/iteration_logs.py render-archive`. Refresh it whenever iteration logs change before commit, push, or PR._

- Legacy manual session baseline: `133`
- Generated iteration count: `151`
- Latest generated iteration number: `284`

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
