from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from edcr.control_room.server.log_files import log_server_to_file, log_uvicorn_to_files, rotating_file_handler


class ServerLogFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._loggers = [logging.getLogger(name) for name in ("", "uvicorn", "uvicorn.access")]
        self._saved = [(logger.handlers[:], logger.level) for logger in self._loggers]
        logging.getLogger().setLevel(logging.INFO)

    def tearDown(self) -> None:
        for logger, (handlers, level) in zip(self._loggers, self._saved):
            for handler in logger.handlers:
                if handler not in handlers:
                    handler.close()
            logger.handlers[:] = handlers
            logger.setLevel(level)

    def test_server_lines_and_access_lines_go_to_their_own_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            server_log = Path(temp_dir) / "logs" / "server.log"
            access_log = Path(temp_dir) / "logs" / "access.log"
            # uvicorn's own loggers do not propagate to the root, as its logging config sets them.
            logging.getLogger("uvicorn").propagate = False
            logging.getLogger("uvicorn.access").propagate = False
            try:
                log_uvicorn_to_files(log_server_to_file(server_log), access_log)

                logging.getLogger("edcr.hub").warning("Inara access check detected in headless mode")
                logging.getLogger("uvicorn.error").error("Exception in ASGI application")
                logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:0", "GET", "/api/x", "1.1", 200)
                for handler in logging.getLogger().handlers + logging.getLogger("uvicorn.access").handlers:
                    handler.flush()
            finally:
                logging.getLogger("uvicorn").propagate = True
                logging.getLogger("uvicorn.access").propagate = True

            server_text = server_log.read_text(encoding="utf-8")
            access_text = access_log.read_text(encoding="utf-8")
            self.assertIn("WARNING edcr.hub: Inara access check detected in headless mode", server_text)
            self.assertIn("ERROR uvicorn.error: Exception in ASGI application", server_text)
            self.assertNotIn("GET /api/x", server_text)
            self.assertIn('INFO uvicorn.access: 1.2.3.4:0 - "GET /api/x HTTP/1.1" 200', access_text)

    def test_no_paths_write_no_files(self) -> None:
        before = logging.getLogger().handlers[:]
        log_uvicorn_to_files(log_server_to_file(None), None)
        self.assertEqual(logging.getLogger().handlers, before)
        self.assertEqual(logging.getLogger("uvicorn.access").handlers, self._saved[2][0])

    def test_file_rotates_and_keeps_the_backup_count(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "server.log"
            logger = logging.getLogger("test.server_log_files.rotate")
            logger.propagate = False
            handler = rotating_file_handler(path, max_bytes=200, backup_count=2)
            logger.addHandler(handler)
            try:
                for index in range(20):
                    logger.warning("line %02d %s", index, "x" * 40)
            finally:
                logger.removeHandler(handler)
                handler.close()

            self.assertEqual(sorted(p.name for p in Path(temp_dir).iterdir()),
                             ["server.log", "server.log.1", "server.log.2"])
            self.assertIn("line 19", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
