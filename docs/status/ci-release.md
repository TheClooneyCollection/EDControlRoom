# CI and Release Status
## Current
- Tests run on `pull_request` and on `push` only for `main`.
- `release-please` owns release PR generation on `main`.
- `dev -> main` promotion PRs are maintained from `promote-dev-to-main--generated-iteration-archive`, rebuilt from `dev` with the generated iteration archive layered on top.
## Caveats
- Bot-authored promotion PRs need `PROMOTION_PR_TOKEN` or `RELEASE_PLEASE_TOKEN` if you want normal PR CI; `GITHUB_TOKEN` is fallback-only.
## Next
- Live-check the promotion workflow once merged by watching branch recreation, archive refresh, and PR update behavior.
