from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from edap.iteration_logs import (
    AREA_WIDTH,
    LEGACY_SESSION_BASELINE,
    build_iteration_log_filename,
    create_iteration_log,
    next_iteration_number,
    pad_area,
    parse_iteration_log_filename,
    render_iteration_archive,
)


class IterationLogNamingTests(unittest.TestCase):
    def test_pad_area_centers_short_names(self) -> None:
        self.assertEqual(pad_area("ci"), "_____ci_____")
        self.assertEqual(pad_area("docs"), "____docs____")
        self.assertEqual(pad_area("control-room"), "control-room")

    def test_pad_area_rejects_too_long_name(self) -> None:
        with self.assertRaisesRegex(ValueError, str(AREA_WIDTH)):
            pad_area("very-long-area")

    def test_build_and_parse_filename_round_trip(self) -> None:
        filename = build_iteration_log_filename(
            timestamp="2026-06-11-13-45",
            area="docs",
            title="iteration-log-migration",
        )
        parsed = parse_iteration_log_filename(filename)

        self.assertEqual(filename, "2026-06-11-13-45_____docs_____iteration-log-migration.md")
        self.assertEqual(parsed.timestamp, "2026-06-11-13-45")
        self.assertEqual(parsed.area, "docs")
        self.assertEqual(parsed.title, "iteration-log-migration")
        self.assertEqual(parsed.display_timestamp, "2026-06-11 13:45")


class IterationLogWorkflowTests(unittest.TestCase):
    def test_create_iteration_log_scaffold_and_next_number(self) -> None:
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp)
            created = create_iteration_log(
                logs_dir=logs_dir,
                timestamp="2026-06-11-13-45",
                area="docs",
                title="iteration-log-migration",
            )

            self.assertTrue(created.exists())
            self.assertEqual(created.name, "2026-06-11-13-45_____docs_____iteration-log-migration.md")
            self.assertIn("- Area: `docs`", created.read_text(encoding="utf-8"))
            self.assertEqual(
                next_iteration_number(logs_dir=logs_dir, baseline=LEGACY_SESSION_BASELINE),
                LEGACY_SESSION_BASELINE + 2,
            )

    def test_render_iteration_archive_numbers_logs_from_baseline(self) -> None:
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp)
            first = logs_dir / "2026-06-11-13-45_____docs_____iteration-log-migration.md"
            first.write_text("# Iteration Log\n\nFirst body.\n", encoding="utf-8")
            second = logs_dir / "2026-06-11-13-50______ci______timing-threshold-follow-up.md"
            second.write_text("# Iteration Log\n\nSecond body.\n", encoding="utf-8")

            archive = render_iteration_archive(
                logs_dir=logs_dir,
                baseline=LEGACY_SESSION_BASELINE,
            )

            self.assertIn("- Legacy manual session baseline: `133`", archive)
            self.assertIn("- Generated iteration count: `2`", archive)
            self.assertIn("- Latest generated iteration number: `135`", archive)
            self.assertIn("## Iteration 134", archive)
            self.assertIn("## Iteration 135", archive)
            self.assertIn("- Area: `docs`", archive)
            self.assertIn("- Area: `ci`", archive)
            self.assertIn("First body.", archive)
            self.assertIn("Second body.", archive)
