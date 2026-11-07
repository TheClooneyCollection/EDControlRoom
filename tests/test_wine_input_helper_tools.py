"""Operator build/install flows, with no Wine launch or real bottle access."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.build_wine_input_helper import build_helper, ROOT
from tools.install_wine_input_helper import install_helper


class WineHelperToolsTests(unittest.TestCase):
    def test_operator_builds_executable_with_selected_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build" / "helper.exe"
            commands = []

            def compile_exe(argv, *, check):
                self.assertTrue(check)
                commands.append(argv)
                output.write_bytes(b"MZ fake executable")

            result = build_helper("mingw-on-path", output, runner=compile_exe)
            self.assertEqual(result.read_bytes(), b"MZ fake executable")
            self.assertEqual(commands, [[
                "mingw-on-path", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(ROOT / "tools/wine_input_helper/edap_input_helper.c"),
                "-o", str(output), "-lws2_32", "-luser32",
            ]])

    def test_compiler_failure_is_reported_to_operator(self):
        def fail(argv, *, check):
            raise subprocess.CalledProcessError(1, argv)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.CalledProcessError):
                build_helper("missing", Path(directory) / "helper.exe", runner=fail)

    def test_operator_installs_and_updates_only_selected_fake_bottle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bottles = root / "Bottles"
            drive = bottles / "Test" / "drive_c"
            drive.mkdir(parents=True)
            source = root / "helper.exe"
            source.write_bytes(b"MZ version one")
            destination = install_helper("Test", bottles, source, copy=shutil.copy2)
            self.assertEqual(destination, (drive / "edap" / "edap_input_helper.exe").resolve())
            self.assertEqual(destination.read_bytes(), source.read_bytes())
            source.write_bytes(b"MZ version two")
            install_helper("Test", bottles, source, copy=shutil.copy2)
            self.assertEqual(destination.read_bytes(), b"MZ version two")
            self.assertEqual(list(drive.iterdir()), [drive / "edap"])

    def test_install_refuses_missing_bottle_source_and_path_traversal(self):
        def forbidden_copy(source, target):
            self.fail("invalid install must not copy")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "missing.exe"
            for name in ("", ".", "..", "../Test", "a/b", "a\\b", "Test"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    install_helper(name, root, source, copy=forbidden_copy)
            (root / "Test" / "drive_c").mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                install_helper("Test", root, source, copy=forbidden_copy)
            self.assertFalse((root / "Test" / "drive_c" / "edap").exists())

    def test_install_refuses_destination_redirected_outside_bottle(self):
        def forbidden_copy(source, target):
            self.fail("redirected install must not copy")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            drive = root / "Test" / "drive_c"
            drive.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            try:
                (drive / "edap").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(ValueError):
                install_helper("Test", root, root / "helper.exe", copy=forbidden_copy)
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
