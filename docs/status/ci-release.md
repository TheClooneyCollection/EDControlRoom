# CI and Release Status
## Current
- `dev -> main` promotion now authenticates through the installed GitHub App via `BOT_APP_ID` and `BOT_APP_PRIVATE_KEY`, then explicitly dispatches `Tests` on the promotion branch after updating the standing PR.
- PR `#13` showed the expected bot-PR behavior: the promotion workflow created or updated the PR from `GITHUB_TOKEN`, so normal `pull_request` workflows did not fire on that PR even though CodeQL still produced a dynamic run on `refs/pull/13/head`.
- A repo-wide `workflow_run` notifier posts to Discord via `DISCORD_WEBHOOK_URL` whenever any workflow other than the notifier itself completes with `failure`.
- Workflow YAML changes are expected to be locally parse-validated before push so GitHub does not become the first syntax check.
- Tests run on `pull_request` and on `push` only for `main`.
- `release-please` owns release PR generation on `main`.
- `dev -> main` promotion PRs are maintained from `promote-dev-to-main--generated-iteration-archive`, rebuilt from `dev` with the generated iteration archive layered on top.
## Caveats
- The promotion workflow now depends on the GitHub App being installed on `EDControlRoom` and on repo secrets `BOT_APP_ID` plus `BOT_APP_PRIVATE_KEY` being present and valid.
## Next
- Live-check one intentionally failing or naturally failing Actions run to confirm the Discord payload, webhook permissions, and self-exclusion behavior.
- Live-check the promotion workflow once merged by watching app-authenticated branch recreation, PR update behavior, explicit test dispatch, and whether GitHub now attaches `pull_request` checks to the promotion PR.
