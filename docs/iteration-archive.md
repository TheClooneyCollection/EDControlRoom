# Iteration Archive

_This file is generated from `docs/iteration-logs/` by `uv run python3 tools/iteration_logs.py render-archive`. Refresh it whenever iteration logs change before commit, push, or PR._

- Legacy manual session baseline: `133`
- Generated iteration count: `82`
- Latest generated iteration number: `215`

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
