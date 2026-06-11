from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

AREA_WIDTH = len("control-room")
LEGACY_SESSION_BASELINE = 133

_AREA_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TITLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class IterationLogName:
    timestamp: str
    area: str
    area_field: str
    title: str
    filename: str

    @property
    def display_timestamp(self) -> str:
        return f"{self.timestamp[:10]} {self.timestamp[11:13]}:{self.timestamp[14:16]}"


def pad_area(area: str) -> str:
    if not _AREA_RE.fullmatch(area):
        raise ValueError(
            "area must be lowercase kebab-case using only a-z, 0-9, and '-'"
        )
    if len(area) > AREA_WIDTH:
        raise ValueError(
            f"area '{area}' is too long; maximum width is {AREA_WIDTH} characters"
        )
    return area.center(AREA_WIDTH, "_")


def normalize_area_field(area_field: str) -> str:
    if len(area_field) != AREA_WIDTH:
        raise ValueError(
            f"area field '{area_field}' must be exactly {AREA_WIDTH} characters wide"
        )
    area = area_field.strip("_")
    if not area:
        raise ValueError("area field must contain a non-empty area slug")
    if pad_area(area) != area_field:
        raise ValueError(
            f"area field '{area_field}' is not a valid centered form of '{area}'"
        )
    return area


def build_iteration_log_filename(*, timestamp: str, area: str, title: str) -> str:
    if not _TITLE_RE.fullmatch(title):
        raise ValueError(
            "title must be lowercase kebab-case using only a-z, 0-9, and '-'"
        )
    return f"{timestamp}_{pad_area(area)}_{title}.md"


def parse_iteration_log_filename(filename: str) -> IterationLogName:
    if not filename.endswith(".md"):
        raise ValueError(f"invalid iteration log filename: {filename}")
    stem = filename[:-3]
    minimum_length = 16 + 1 + AREA_WIDTH + 1 + 1
    if len(stem) < minimum_length:
        raise ValueError(f"invalid iteration log filename: {filename}")
    timestamp = stem[:16]
    if not _TIMESTAMP_RE.fullmatch(timestamp):
        raise ValueError(f"invalid iteration log filename: {filename}")
    if stem[16] != "_":
        raise ValueError(f"invalid iteration log filename: {filename}")
    area_field = stem[17 : 17 + AREA_WIDTH]
    if stem[17 + AREA_WIDTH] != "_":
        raise ValueError(f"invalid iteration log filename: {filename}")
    title = stem[18 + AREA_WIDTH :]
    if not _TITLE_RE.fullmatch(title):
        raise ValueError(f"invalid iteration log filename: {filename}")
    return IterationLogName(
        timestamp=timestamp,
        area=normalize_area_field(area_field),
        area_field=area_field,
        title=title,
        filename=filename,
    )


def iter_iteration_log_paths(logs_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in logs_dir.glob("*.md")
        if path.is_file() and path.name != "README.md"
    )


def next_iteration_number(*, logs_dir: Path, baseline: int = LEGACY_SESSION_BASELINE) -> int:
    return baseline + len(iter_iteration_log_paths(logs_dir)) + 1


def create_iteration_log(
    *,
    logs_dir: Path,
    timestamp: str,
    area: str,
    title: str,
) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    filename = build_iteration_log_filename(timestamp=timestamp, area=area, title=title)
    path = logs_dir / filename
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        "\n".join(
            [
                "# Iteration Log",
                "",
                f"- Area: `{area}`",
                f"- Title: `{title}`",
                f"- Started: `{timestamp[:10]} {timestamp[11:13]}:{timestamp[14:16]}`",
                "",
                "## Summary",
                "",
                "-",
                "",
                "## Changes",
                "",
                "-",
                "",
                "## Follow-ups",
                "",
                "-",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def render_iteration_archive(
    *,
    logs_dir: Path,
    baseline: int = LEGACY_SESSION_BASELINE,
) -> str:
    paths = iter_iteration_log_paths(logs_dir)
    latest_iteration = baseline + len(paths)
    lines = [
        "# Iteration Archive",
        "",
        (
            "_This file is generated from `docs/iteration-logs/` by "
            "`uv run python3 tools/iteration_logs.py render-archive`. Refresh it when "
            "work lands on `main` or when preparing a release, not on every feature branch._"
        ),
        "",
        f"- Legacy manual session baseline: `{baseline}`",
        f"- Generated iteration count: `{len(paths)}`",
        f"- Latest generated iteration number: `{latest_iteration}`",
        "",
    ]
    for offset, path in enumerate(paths, start=1):
        parsed = parse_iteration_log_filename(path.name)
        iteration_number = baseline + offset
        relative_path = path.name
        lines.extend(
            [
                f"## Iteration {iteration_number}",
                "",
                f"- When: `{parsed.display_timestamp}`",
                f"- Area: `{parsed.area}`",
                f"- Title: `{parsed.title}`",
                f"- Source: [{relative_path}](iteration-logs/{relative_path})",
                "",
                path.read_text(encoding="utf-8").rstrip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
