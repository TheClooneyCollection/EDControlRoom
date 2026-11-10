from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import tomllib
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
PACKAGE_NAME = "EDControlRoom"
REPOSITORY_OWNER = "TheClooneyCollection"
REPOSITORY_NAME = "EDControlRoom"
PROJECT_DISPLAY_NAME = "EDControlRoom"
LATEST_RELEASE_API_URL = (
    f"https://api.github.com/repos/{REPOSITORY_OWNER}/{REPOSITORY_NAME}/releases/latest"
)


@dataclass(frozen=True)
class GitHubRelease:
    tag_name: str
    name: str
    html_url: str
    published_at: str

    @property
    def version(self) -> str:
        return normalize_version(self.tag_name)

    @property
    def display_name(self) -> str:
        return self.tag_name.strip() or self.name.strip() or "latest release"


def normalize_version(value: str) -> str:
    return value.strip().removeprefix("v").strip()


def display_version(value: str) -> str:
    normalized = normalize_version(value)
    return f"v{normalized}" if normalized else "unknown version"


def _version_key(value: str) -> tuple[int, ...] | None:
    normalized = normalize_version(value)
    if not normalized:
        return None
    core = re.split(r"[-+]", normalized, maxsplit=1)[0]
    parts = core.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    key = tuple(int(part) for part in parts)
    if not key:
        return None
    return key


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_key = _version_key(candidate)
    current_key = _version_key(current)
    if candidate_key is None or current_key is None:
        return False
    width = max(len(candidate_key), len(current_key))
    return candidate_key + (0,) * (width - len(candidate_key)) > current_key + (0,) * (width - len(current_key))


def _load_version_from_pyproject() -> str:
    with PYPROJECT_PATH.open("rb") as handle:
        raw = tomllib.load(handle)
    project = raw.get("project", {})
    if not isinstance(project, dict):
        return "0.0.0"
    value = project.get("version", "0.0.0")
    return str(value).strip() or "0.0.0"


def get_current_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return _load_version_from_pyproject()


def run_git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=2,
        check=True,
    ).stdout.strip()


def get_current_commit(git: Callable[[list[str]], str]) -> str:
    """Short HEAD commit of the checkout, with +dirty when tracked files have uncommitted edits."""
    try:
        commit = git(["rev-parse", "--short", "HEAD"])
        dirty = git(["status", "--porcelain", "--untracked-files=no"])
    except (OSError, subprocess.SubprocessError):
        return ""
    return f"{commit}+dirty" if commit and dirty else commit


@cache
def get_startup_commit() -> str:
    """The checkout commit when this process first asked, so a running server keeps reporting what it loaded."""
    return get_current_commit(run_git)


def fetch_latest_github_release(*, timeout: float = 1.5) -> GitHubRelease | None:
    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{REPOSITORY_NAME}/{get_current_version()}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    tag_name = str(payload.get("tag_name", "")).strip()
    html_url = str(payload.get("html_url", "")).strip()
    if not tag_name or not html_url:
        return None
    return GitHubRelease(
        tag_name=tag_name,
        name=str(payload.get("name", "")).strip(),
        html_url=html_url,
        published_at=str(payload.get("published_at", "")).strip(),
    )
