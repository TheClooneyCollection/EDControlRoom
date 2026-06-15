# CI and Release Status
## Current
- `main` is now the rolling-update branch, and stable features or releases are identified with tags instead of `dev -> main` promotion.
- The legacy `.github/workflows/promote-dev-to-main.yml` automation has been removed; release/process automation now centers on `main`, tags, and `release-please`.
- A repo-wide `workflow_run` notifier posts to Discord via `DISCORD_WEBHOOK_URL` whenever any workflow other than the notifier itself completes with `failure`.
- Workflow YAML changes are expected to be locally parse-validated before push so GitHub does not become the first syntax check.
- Tests run on `pull_request` and on `push` only for `main`.
- `release-please` owns release PR generation on `main`.
## Caveats
- Historical iteration logs and generated archives still mention the old promotion path because they are retained as chronology, not current policy.
## Next
- Live-check one intentionally failing or naturally failing Actions run to confirm the Discord payload, webhook permissions, and self-exclusion behavior.
- Remove or refresh any remaining non-historical promotion references if they surface in future docs or automation changes.
