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
