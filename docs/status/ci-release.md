# CI and Release Status
## Current
- `main` is now the rolling-update branch, and stable features or releases are identified with tags instead of `dev -> main` promotion.
- The legacy `.github/workflows/promote-dev-to-main.yml` automation has been removed; release/process automation now centers on `main`, semantic version tags, and manual GitHub release publishing.
- Same-repo PR activity now runs `.github/workflows/sync-iteration-archive.yml`, which regenerates and commits `docs/iteration-archive.md` onto the PR branch when iteration logs changed.
- Pull requests still need `tools/iteration_logs.py validate` plus a rendered-archive diff check in `Tests` so stale archive drift fails visibly if the sync workflow cannot update the branch.
- A repo-wide `workflow_run` notifier posts to Discord via `DISCORD_WEBHOOK_URL` whenever any workflow other than the notifier itself completes with `failure`.
- PR `#17` confirmed the notifier trigger still fires after a `Tests` failure; the notifier now includes the first failed job and failed step at the top of the Discord message and suppresses link previews with `flags: 4`.
- Workflow YAML changes are expected to be locally parse-validated before push so GitHub does not become the first syntax check.
- Tests run on `pull_request` and on `push` only for `main`.
- Release prep is manual: prepare the release commit, run the full suite, tag `vX.Y.Z`, and publish the GitHub release directly.
## Caveats
- Historical iteration logs and generated archives still mention the old promotion path because they are retained as chronology, not current policy.
## Next
- Live-check the next failing Actions run to confirm the job/step lookup and markdown link rendering match the local proof-of-concept.
- Live-check the next same-repo PR update to confirm the archive sync workflow pushes the refreshed `docs/iteration-archive.md` before the `Tests` guard runs.
- Remove or refresh any remaining non-historical promotion or legacy release-automation references if they surface in future docs or automation changes.
