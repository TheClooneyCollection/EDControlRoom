from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib import error
from unittest.mock import patch

from tools.discord_workflow_failure_notify import (
    NotificationContext,
    build_discord_payload,
    find_workflow_file_link,
    first_failed_job,
    main,
    post_to_discord,
)


class _FakeResponse:
    def __init__(self, *, status_code: int = 204, body: str = "") -> None:
        self._status_code = status_code
        self._body = body

    def getcode(self) -> int:
        return self._status_code

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def close(self) -> None:
        return None

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class DiscordWorkflowFailureNotifyTests(unittest.TestCase):
    def test_first_failed_job_picks_first_failing_job_and_step(self) -> None:
        failed_job = first_failed_job(
            {
                "jobs": [
                    {"name": "lint", "conclusion": "success"},
                    {
                        "name": "unittest",
                        "conclusion": "failure",
                        "html_url": "https://example.invalid/job/2",
                        "steps": [
                            {"name": "setup", "conclusion": "success"},
                            {"name": "run tests", "conclusion": "failure"},
                        ],
                    },
                ]
            },
            repository="TheClooneyCollection/EDControlRoom",
            run_id="123",
            workflow_url="https://example.invalid/run/123",
        )

        self.assertEqual(failed_job.name, "unittest")
        self.assertEqual(failed_job.url, "https://example.invalid/job/2")
        self.assertIsNotNone(failed_job.failed_step)
        self.assertEqual(failed_job.failed_step.name, "run tests")

    def test_build_discord_payload_includes_expected_links(self) -> None:
        payload = build_discord_payload(
            NotificationContext(
                repository="TheClooneyCollection/EDControlRoom",
                workflow_name="Tests",
                workflow_url="https://github.com/TheClooneyCollection/EDControlRoom/actions/runs/123",
                branch_name="main",
                commit_sha="abcdef1234567890",
                actor="nicholasclooney",
                run_id="123",
                workflow_link="https://github.com/TheClooneyCollection/EDControlRoom/blob/main/.github/workflows/tests.yml",
            ),
            first_failed_job(
                {
                    "jobs": [
                        {
                            "name": "unittest",
                            "conclusion": "failure",
                            "html_url": "https://example.invalid/job/2",
                            "steps": [
                                {"name": "run tests", "conclusion": "failure"},
                            ],
                        }
                    ]
                },
                repository="TheClooneyCollection/EDControlRoom",
                run_id="123",
                workflow_url="https://example.invalid/run/123",
            ),
        )

        self.assertEqual(payload["flags"], 4)
        content = str(payload["content"])
        self.assertIn("**Workflow:** [Tests](", content)
        self.assertIn("`abcdef1`", content)
        self.assertIn("**Step:** [run tests](", content)

    def test_find_workflow_file_link_scans_repo_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            workflow_dir = repo_root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "tests.yml").write_text(
                "name: Tests\non:\n  workflow_dispatch:\n",
                encoding="utf-8",
            )

            link = find_workflow_file_link(
                repo_root=repo_root,
                repository="TheClooneyCollection/EDControlRoom",
                workflow_name="Tests",
                fallback_url="https://example.invalid/run/123",
            )

        self.assertEqual(
            link,
            "https://github.com/TheClooneyCollection/EDControlRoom/blob/main/.github/workflows/tests.yml",
        )

    def test_post_to_discord_raises_with_response_body_on_http_error(self) -> None:
        def fake_urlopen(_request):
            raise error.HTTPError(
                url="https://discord.invalid/webhook",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=_FakeResponse(body='{"message":"bad"}'),
            )

        with self.assertRaisesRegex(RuntimeError, 'HTTP 400: {"message":"bad"}'):
            with patch(
                "tools.discord_workflow_failure_notify.request.urlopen",
                new=fake_urlopen,
            ):
                post_to_discord(
                    webhook_url="https://discord.invalid/webhook",
                    payload={"content": "hello", "flags": 4},
                )

    def test_main_dry_run_prints_payload_from_jobs_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            jobs_path = temp_path / "jobs.json"
            jobs_path.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "name": "unittest",
                                "conclusion": "failure",
                                "html_url": "https://example.invalid/job/2",
                                "steps": [
                                    {"name": "run tests", "conclusion": "failure"},
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            workflow_dir = temp_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "tests.yml").write_text("name: Tests\n", encoding="utf-8")

            with patch("sys.stdout.write") as stdout_write:
                exit_code = main(
                    [
                        "--jobs-json-file",
                        str(jobs_path),
                        "--dry-run",
                        "--repo-root",
                        str(temp_path),
                        "--run-id",
                        "123",
                        "--workflow-name",
                        "Tests",
                        "--workflow-url",
                        "https://example.invalid/run/123",
                        "--branch-name",
                        "main",
                        "--commit-sha",
                        "abcdef1234567890",
                        "--repository",
                        "TheClooneyCollection/EDControlRoom",
                        "--actor",
                        "nicholasclooney",
                    ]
                )

        self.assertEqual(exit_code, 0)
        printed = "".join(call.args[0] for call in stdout_write.call_args_list)
        self.assertIn('"flags": 4', printed)
        self.assertIn("GitHub Actions workflow failed", printed)
