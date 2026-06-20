from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class FailedStep:
    name: str


@dataclass(frozen=True)
class FailedJob:
    name: str
    url: str
    failed_step: FailedStep | None


@dataclass(frozen=True)
class NotificationContext:
    repository: str
    workflow_name: str
    workflow_url: str
    branch_name: str
    commit_sha: str
    actor: str
    run_id: str
    workflow_link: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post GitHub Actions workflow failures to Discord.",
    )
    parser.add_argument("--github-token")
    parser.add_argument("--discord-webhook-url")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-url", required=True)
    parser.add_argument("--branch-name", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--jobs-json-file")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Discord payload JSON instead of posting it.",
    )
    return parser.parse_args(argv)


def fetch_jobs_json(*, repository: str, run_id: str, github_token: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    api_request = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with request.urlopen(api_request) as response:
        return json.loads(response.read().decode("utf-8"))


def load_jobs_json(args: argparse.Namespace) -> dict[str, Any]:
    if args.jobs_json_file:
        return json.loads(Path(args.jobs_json_file).read_text(encoding="utf-8"))
    if not args.github_token:
        raise ValueError("--github-token is required unless --jobs-json-file is provided.")
    return fetch_jobs_json(
        repository=args.repository,
        run_id=args.run_id,
        github_token=args.github_token,
    )


def first_failed_job(jobs_payload: dict[str, Any], *, repository: str, run_id: str, workflow_url: str) -> FailedJob:
    jobs = jobs_payload.get("jobs", [])
    if not isinstance(jobs, list):
        jobs = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("conclusion") != "failure":
            continue
        job_id = job.get("id")
        job_url = str(job.get("html_url") or "")
        if not job_url and job_id is not None:
            job_url = f"https://github.com/{repository}/actions/runs/{run_id}/job/{job_id}"
        if not job_url:
            job_url = workflow_url
        failed_step = None
        steps = job.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if step.get("conclusion") == "failure":
                    failed_step = FailedStep(name=str(step.get("name") or "Unknown"))
                    break
        return FailedJob(
            name=str(job.get("name") or "Unknown"),
            url=job_url,
            failed_step=failed_step,
        )
    return FailedJob(name="Unknown", url=workflow_url, failed_step=None)


def find_workflow_file_link(*, repo_root: Path, repository: str, workflow_name: str, fallback_url: str) -> str:
    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return fallback_url
    for path in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith("name:"):
                break
            candidate = stripped.partition(":")[2].strip().strip("'\"")
            if candidate == workflow_name:
                rel_path = path.relative_to(repo_root).as_posix()
                return f"https://github.com/{repository}/blob/main/{rel_path}"
            break
    return fallback_url


def build_notification_context(args: argparse.Namespace) -> NotificationContext:
    repo_root = Path(args.repo_root).resolve()
    workflow_link = find_workflow_file_link(
        repo_root=repo_root,
        repository=args.repository,
        workflow_name=args.workflow_name,
        fallback_url=args.workflow_url,
    )
    return NotificationContext(
        repository=args.repository,
        workflow_name=args.workflow_name,
        workflow_url=args.workflow_url,
        branch_name=args.branch_name,
        commit_sha=args.commit_sha,
        actor=args.actor,
        run_id=args.run_id,
        workflow_link=workflow_link,
    )


def build_discord_payload(ctx: NotificationContext, failed_job: FailedJob) -> dict[str, object]:
    step_name = failed_job.failed_step.name if failed_job.failed_step is not None else "Unknown"
    commit_short = ctx.commit_sha[:7]
    content = "\n".join(
        [
            "🚨 **GitHub Actions workflow failed**",
            "",
            f"**Job:** [{failed_job.name}]({failed_job.url})",
            f"**Step:** [{step_name}]({failed_job.url})",
            "",
            f"**Repository:** [{ctx.repository}](https://github.com/{ctx.repository})",
            f"**Workflow:** [{ctx.workflow_name}]({ctx.workflow_link})",
            f"**Branch:** [`{ctx.branch_name}`](https://github.com/{ctx.repository}/tree/{ctx.branch_name})",
            f"**Commit:** [`{commit_short}`](https://github.com/{ctx.repository}/commit/{ctx.commit_sha})",
            f"**Author:** [{ctx.actor}](https://github.com/{ctx.actor})",
            f"**Run:** {ctx.workflow_url}",
        ]
    )
    return {"content": content, "flags": 4}


def post_to_discord(*, webhook_url: str, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode("utf-8")
    webhook_request = request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(webhook_request) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Discord webhook request failed with HTTP {exc.code}: {response_body}"
        ) from exc
    if status_code < 200 or status_code >= 300:
        raise RuntimeError(
            f"Discord webhook request failed with HTTP {status_code}: {response_body}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    webhook_url = args.discord_webhook_url or ""
    if not webhook_url and not args.dry_run:
        print("DISCORD_WEBHOOK_URL is not configured for this run; skipping notification.")
        return 0

    jobs_payload = load_jobs_json(args)
    ctx = build_notification_context(args)
    failed_job = first_failed_job(
        jobs_payload,
        repository=ctx.repository,
        run_id=ctx.run_id,
        workflow_url=ctx.workflow_url,
    )
    payload = build_discord_payload(ctx, failed_job)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    post_to_discord(webhook_url=webhook_url, payload=payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
