"""Authenticated, synchronous Wine input transport. Never posts host keyboard events."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Protocol
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import tempfile
from threading import RLock
from time import monotonic, sleep

from edap.config import WineHelperConfig, validate_wine_helper
from .base import InputTargetState
from .scancodes import resolve_scancode


class HelperProcess(Protocol):
    def wait(self, timeout: float) -> object: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...


class HelperError(RuntimeError):
    """A helper protocol or application failure; never a reason to launch another helper."""


class FocusFailed(HelperError):
    """The helper could not make Elite the Win32 foreground; no key was sent."""


FOCUS_ATTEMPTS = 3
FOCUS_RETRY_S = 0.1
FOCUS_FAILED_MESSAGE = "wine helper couldn't focus Elite inside the CrossOver bottle (focus_failed); no keys were sent."


class BurstAborted(RuntimeError):
    """Transport recovery reset held keys; the interrupted burst must not be replayed."""


def load_or_create_token(path: Path) -> str:
    """Publish a complete private token atomically, without replacing an existing token."""
    path = path.expanduser()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        token = secrets.token_hex(32)
        fd, temporary = tempfile.mkstemp(prefix='.wine-token-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='ascii') as handle:
                handle.write(token + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            os.unlink(temporary)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r', encoding='ascii') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise RuntimeError(f"wine helper token file must be an owner-only regular file (0600): {path}")
        token = handle.read(130).strip()
    if not re.fullmatch(r'[0-9a-fA-F]{64}', token):
        raise RuntimeError(f"wine helper token file must contain a 64-character hex token: {path}")
    return token


def check_crossover_match(wine_path: str, bottle: str, process_table: str) -> None:
    configured = str(Path(wine_path).expanduser()).split('.app/', 1)[0] + '.app'
    for line in process_table.splitlines():
        if 'winewrapper.exe' not in line.lower():
            continue
        # CrossOver wrapper command lines include --bottle NAME (possibly quoted).
        match = re.search(r'--bottle(?:=|\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))', line)
        if match is None or next(value for value in match.groups() if value is not None) != bottle:
            continue
        app = re.search(r'(/[^\n]*?\.app)/Contents/', line)
        if app and app.group(1).strip('"\'') != configured:
            raise RuntimeError(
                f"CrossOver app mismatch for bottle {bottle!r}: configured {configured}, "
                f"running {app.group(1)}; use the wine_path of the running CrossOver app."
            )


class WineHelperClient:
    def __init__(self, config: WineHelperConfig, *,
                 connect: Callable[[str, int, float], BinaryIO],
                 sleeper: Callable[[float], None], clock: Callable[[], float],
                 popen: Callable[[list[str]], HelperProcess],
                 process_table: Callable[[], str], read_token: Callable[[Path], str]) -> None:
        self.config = config
        self._connect = connect
        self._sleep = sleeper
        self._clock = clock
        self._popen = popen
        self._process_table = process_table
        self._read_token = read_token
        self._token = ''
        self._closed = True
        self._stream: BinaryIO | None = None
        self._process: HelperProcess | None = None
        self._lock = RLock()
        self.target = InputTargetState(platform='macos', mode='wine_helper', process_name=config.process_name)

    @property
    def connected(self) -> bool:
        return not self._closed and self._stream is not None

    def _exchange(self, op: str, **fields: object) -> dict:
        if self._stream is None:
            raise OSError('helper connection is closed')
        self._stream.write((json.dumps({'op': op, **fields}) + '\n').encode('utf-8'))
        self._stream.flush()
        line = self._stream.readline(65537)
        if not line:
            raise OSError('helper disconnected')
        if len(line) > 65536 or not line.endswith(b'\n'):
            raise HelperError('wine helper invalid reply; check input.wine_helper.port')
        try:
            reply = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise HelperError('wine helper invalid reply; check input.wine_helper.port') from exc
        if not isinstance(reply, dict) or not isinstance(reply.get('ok'), bool):
            raise HelperError('wine helper invalid reply; check input.wine_helper.port')
        if not reply['ok']:
            if reply.get('error') == 'focus_failed':
                raise FocusFailed(FOCUS_FAILED_MESSAGE)
            raise HelperError(f"wine helper {reply.get('error', 'bad_request')}: {reply.get('detail', '')}")
        return reply

    def _disconnect(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass

    def _handshake(self) -> None:
        try:
            hello = self._exchange('hello', token=self._token, protocol=1)
            if type(hello.get('protocol')) is not int or hello['protocol'] != 1:
                raise HelperError('wine helper protocol mismatch; expected protocol 1')
            if not isinstance(hello.get('helper_version'), str):
                raise HelperError('wine helper invalid hello reply')
            target = self._exchange('target', process=self.config.process_name)
            self._exchange('release_all')
            try:
                hwnd, pid = int(target['hwnd'], 0), int(target['pid'])
                if hwnd <= 0 or pid <= 0:
                    raise ValueError()
            except (KeyError, TypeError, ValueError) as exc:
                raise HelperError('wine helper invalid target reply') from exc
            self.target = InputTargetState(platform='macos', mode='wine_helper', pid=pid, hwnd=hwnd,
                                           process_name=self.config.process_name,
                                           helper_version=hello['helper_version'])
        except BaseException:
            self._disconnect()
            raise

    def _open(self) -> None:
        self._stream = self._connect('127.0.0.1', self.config.port, self.config.request_timeout_s)
        self._handshake()

    def start(self) -> InputTargetState:
        with self._lock:
            if self._stream is not None:
                return self.target
            validate_wine_helper(self.config, selected=True)
            self._token = self._read_token(self.config.token_file)
            # Only a refused connection allows launch. An occupied but invalid port never does.
            try:
                self._stream = self._connect('127.0.0.1', self.config.port, self.config.request_timeout_s)
            except ConnectionRefusedError:
                if self.config.launch == 'manual':
                    raise self._unreachable() from None
            except OSError as exc:
                raise self._unreachable() from exc
            else:
                try:
                    self._handshake()
                except OSError as exc:
                    raise self._unreachable() from exc
                self._closed = False
                return self.target
            check_crossover_match(self.config.wine_path, self.config.bottle, self._process_table())
            self._process = self._popen([
                str(Path(self.config.wine_path).expanduser()), '--bottle', self.config.bottle,
                self.config.helper_path, '--port', str(self.config.port), '--token', self._token,
                '--log', r'C:\edap\helper.log', '--max-hold-s', str(self.config.max_hold_s),
            ])
            deadline = self._clock() + self.config.startup_timeout_s
            try:
                while True:
                    try:
                        self._open()
                        self._closed = False
                        return self.target
                    except ConnectionRefusedError:
                        if self._clock() >= deadline:
                            raise self._unreachable() from None
                        self._sleep(min(.05, max(0, deadline - self._clock())))
            except BaseException:
                self._disconnect()
                self._stop_process()
                raise

    def _unreachable(self) -> RuntimeError:
        return RuntimeError(f'wine helper not reachable on 127.0.0.1:{self.config.port}; check helper launch and input.wine_helper configuration (no foreground fallback).')

    def _request(self, op: str, **fields: object) -> dict:
        if self._closed:
            raise RuntimeError("wine helper client is closed; select wine_helper to reconnect")
        try:
            return self._exchange(op, **fields)
        except OSError as exc:
            self._disconnect()
            try:
                self._open()  # Exactly once; handshake releases all keys before reporting failure.
            except (OSError, RuntimeError) as recovery:
                raise BurstAborted(f'{self._unreachable()} Interrupted input burst aborted; reconnect failed: {recovery}') from exc
            raise BurstAborted('wine helper transport failed; reconnected and released all keys; interrupted input burst aborted (not replayed).') from exc
        except FocusFailed:
            raise  # A refused focus or key-down sent nothing, so the connection stays usable.
        except HelperError:
            # Invalid replies can leave the result of a key-down unknown. Disconnect releases it.
            self._disconnect()
            raise

    @staticmethod
    def _keys(key: str, modifier: str | None) -> list[tuple[int, bool]]:
        keys = ([resolve_scancode(modifier, modifier=True)] if modifier else []) + [resolve_scancode(key)]
        if any(scan == 0x38 for scan, _ in keys):
            raise ValueError('wine helper refuses Alt scan code 0x38')
        return keys

    def _focus(self) -> None:
        for attempt in range(FOCUS_ATTEMPTS):
            try:
                self._request('focus')
                return
            except FocusFailed:
                if attempt == FOCUS_ATTEMPTS - 1:
                    raise
                self._sleep(FOCUS_RETRY_S)

    def _key(self, code: tuple[int, bool], down: bool) -> None:
        self._request('key', scan=code[0], ext=code[1], down=down)

    def press_key(self, key: str, modifier: str | None = None) -> None:
        keys = self._keys(key, modifier)
        with self._lock:
            self._focus()
            try:
                for code in keys:
                    self._key(code, True)
            except BaseException:
                self._release_after_failure()
                raise

    def _release_after_failure(self) -> None:
        if self._stream is not None:
            try:
                self._exchange('release_all')
            except (OSError, RuntimeError):
                self._disconnect()

    def release_key(self, key: str, modifier: str | None = None) -> None:
        keys = self._keys(key, modifier)
        with self._lock:
            try:
                for code in reversed(keys):
                    self._key(code, False)
            except BaseException:
                self._release_after_failure()
                raise

    def tap_key(self, key: str, modifier: str | None, hold_s: float) -> None:
        keys = self._keys(key, modifier)
        with self._lock:
            self._focus()
            pressed: list[tuple[int, bool]] = []
            failed = False
            try:
                for code in keys:
                    pressed.append(code)
                    self._key(code, True)
                if hold_s > 0:
                    self._sleep(hold_s)
            except BaseException:
                failed = True
                raise
            finally:
                if failed:
                    self._release_after_failure()
                else:
                    try:
                        for code in reversed(pressed):
                            self._key(code, False)
                    except BaseException:
                        self._release_after_failure()
                        raise

    def status(self) -> dict:
        with self._lock:
            return self._request('status')

    def release_all(self) -> None:
        with self._lock:
            self._request('release_all')

    def _stop_process(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        try:
            process.wait(timeout=self.config.request_timeout_s)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=self.config.request_timeout_s)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self.config.request_timeout_s)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            try:
                if self._stream is not None:
                    self._exchange('release_all')
                    if self.config.launch == 'managed':
                        self._exchange('bye')
            finally:
                self._disconnect()
                self._stop_process()


def build_wine_helper(config: WineHelperConfig) -> WineHelperClient:
    def connect(host: str, port: int, timeout: float) -> BinaryIO:
        connection = socket.create_connection((host, port), timeout=timeout)
        stream = connection.makefile('rwb')
        connection.close()  # makefile keeps the descriptor until the stream closes.
        return stream

    def process_table() -> str:
        return subprocess.run(['ps', '-axo', 'pid=,command='], check=True, capture_output=True, text=True).stdout

    return WineHelperClient(config, connect=connect, sleeper=sleep, clock=monotonic,
                            popen=subprocess.Popen, process_table=process_table, read_token=load_or_create_token)
