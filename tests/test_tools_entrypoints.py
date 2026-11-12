import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"


class ToolEntrypointsTests(unittest.TestCase):
    def test_tools_importing_edcr_add_repo_root_first_so_file_path_runs_work(self) -> None:
        # `uv run python3 tools/foo.py` puts tools/ on sys.path, not the repo root.
        missing = []
        for path in sorted(TOOLS_DIR.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            first_edcr = min(
                (index for index in (source.find("\nfrom edcr"), source.find("\nimport edcr")) if index >= 0),
                default=None,
            )
            if first_edcr is None:
                continue
            if "sys.path.insert(0, str(REPO_ROOT))" not in source[:first_edcr]:
                missing.append(path.name)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
