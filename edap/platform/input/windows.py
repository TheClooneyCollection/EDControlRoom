from __future__ import annotations

from collections.abc import Callable
import ctypes
from ctypes import wintypes
from time import sleep as _default_sleep

from edap.timing import TimingSampler

from .base import (
    DEFAULT_AUTO_TARGET_PROCESS_NAME,
    InputController,
    InputTargetState,
)


from .scancodes import KEY_CODES, MODIFIER_KEYCODES, EXTENDED_KEYS


KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1


ULONG_PTR = ctypes.c_size_t


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput),
    ]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", InputUnion)]


SenderFn = Callable[[int, bool], None]
WindowSenderFn = Callable[[int, int, bool], None]
SleeperFn = Callable[[float], None]
PidFinderFn = Callable[[str], int | None]
PidWindowFinderFn = Callable[[int], int | None]


def _is_windows_available() -> bool:
    return hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32")


def _send_input(scan_code: int, is_key_up: bool) -> None:
    if not _is_windows_available():
        raise RuntimeError("Windows SendInput backend is unavailable on this platform.")

    flags = KEYEVENTF_SCANCODE
    if scan_code in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if is_key_up:
        flags |= KEYEVENTF_KEYUP

    input_union = InputUnion()
    input_union.ki = KeyBdInput(0, scan_code & 0xFF, flags, 0, 0)
    event = Input(INPUT_KEYBOARD, input_union)
    ctypes.set_last_error(0)
    sent = ctypes.windll.user32.SendInput(1, ctypes.pointer(event), ctypes.sizeof(event))
    if sent != 1:
        error_code = ctypes.get_last_error()
        if error_code:
            raise OSError(
                error_code,
                f"SendInput failed for scan code 0x{scan_code:02X} (WinError {error_code}).",
            )
        raise OSError(f"SendInput failed for scan code 0x{scan_code:02X}.")


def _make_default_sender() -> SenderFn:
    def sender(scan_code: int, down: bool) -> None:
        _send_input(scan_code, not down)

    return sender


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
GW_OWNER = 4
MAPVK_VSC_TO_VK_EX = 3


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _iter_process_entries() -> list[PROCESSENTRY32W]:
    if not _is_windows_available():
        return []
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        found = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        items: list[PROCESSENTRY32W] = []
        while found:
            copy = PROCESSENTRY32W()
            ctypes.pointer(copy)[0] = entry
            items.append(copy)
            found = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        return items
    finally:
        kernel32.CloseHandle(snapshot)


def _find_pid_by_process_name(process_name: str) -> int | None:
    wanted = process_name.strip().lower()
    for entry in _iter_process_entries():
        if entry.szExeFile.lower() == wanted:
            return int(entry.th32ProcessID)
    return None


def _window_is_candidate(hwnd: int) -> bool:
    user32 = ctypes.windll.user32
    if not user32.IsWindowVisible(hwnd):
        return False
    if user32.GetWindow(hwnd, GW_OWNER):
        return False
    return True


def _find_hwnd_for_pid(pid: int) -> int | None:
    if not _is_windows_available():
        return None
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_windows(hwnd: int, _lparam: int) -> bool:
        if not _window_is_candidate(hwnd):
            return True
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if int(window_pid.value) == pid:
            found.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(enum_windows, 0)
    return found[0] if found else None


def _make_default_window_sender() -> WindowSenderFn:
    def sender(hwnd: int, scan_code: int, down: bool) -> None:
        if not _is_windows_available():
            raise RuntimeError("Windows window-message backend is unavailable on this platform.")
        user32 = ctypes.windll.user32
        scan_low = scan_code & 0xFF
        vk_code = user32.MapVirtualKeyW(scan_low, MAPVK_VSC_TO_VK_EX)
        if vk_code == 0:
            raise RuntimeError(f"Unable to map scan code 0x{scan_code:02X} to a virtual key.")
        lparam = 1 | (scan_low << 16)
        if scan_code in EXTENDED_KEYS:
            lparam |= 1 << 24
        message = WM_KEYDOWN
        if not down:
            message = WM_KEYUP
            lparam |= 1 << 30
            lparam |= 1 << 31
        if not user32.PostMessageW(hwnd, message, vk_code, lparam):
            error_code = ctypes.get_last_error()
            if error_code:
                raise OSError(error_code, f"PostMessageW failed for hwnd 0x{hwnd:X}.")
            raise OSError(f"PostMessageW failed for hwnd 0x{hwnd:X}.")

    return sender


class WindowsInputController(InputController):
    def __init__(
        self,
        *,
        sender: SenderFn | None = None,
        window_sender: WindowSenderFn | None = None,
        pid_finder: PidFinderFn | None = None,
        pid_window_finder: PidWindowFinderFn | None = None,
        sleeper: SleeperFn | None = None,
        timing_sampler: TimingSampler,
    ) -> None:
        self._sender = sender if sender is not None else _make_default_sender()
        self._window_sender = window_sender if window_sender is not None else _make_default_window_sender()
        self._pid_finder = pid_finder if pid_finder is not None else _find_pid_by_process_name
        self._pid_window_finder = pid_window_finder if pid_window_finder is not None else _find_hwnd_for_pid
        self._sleeper = sleeper if sleeper is not None else _default_sleep
        self._timing_sampler = timing_sampler
        self._target = InputTargetState(platform="windows", mode="foreground")

    def press_key(self, key: str, modifier: str | None = None) -> None:
        keycode, mod_keycode = self._resolve(key, modifier)
        if mod_keycode is not None:
            self._dispatch_scan_code(mod_keycode, True)
        self._dispatch_scan_code(keycode, True)

    def release_key(self, key: str, modifier: str | None = None) -> None:
        keycode, mod_keycode = self._resolve(key, modifier)
        self._dispatch_scan_code(keycode, False)
        if mod_keycode is not None:
            self._dispatch_scan_code(mod_keycode, False)

    def tap_key(self, key: str, modifier: str | None = None, hold_s: float = 0.0) -> None:
        keycode, mod_keycode = self._resolve(key, modifier)
        if mod_keycode is not None:
            self._dispatch_scan_code(mod_keycode, True)
        self._dispatch_scan_code(keycode, True)
        if hold_s > 0:
            sampled_hold_s = self._timing_sampler.sample_hold(hold_s)
            self._sleeper(sampled_hold_s)
        self._dispatch_scan_code(keycode, False)
        if mod_keycode is not None:
            self._dispatch_scan_code(mod_keycode, False)

    def type_text(self, text: str, char_delay_s: float = 0.05) -> None:
        special = {"\n": "enter", "\r": "return", "\t": "tab", "\x1b": "esc"}
        shifted = {
            "!": "1",
            "@": "2",
            "#": "3",
            "$": "4",
            "%": "5",
            "^": "6",
            "&": "7",
            "*": "8",
            "(": "9",
            ")": "0",
            "_": "-",
            "+": "=",
            "{": "[",
            "}": "]",
            "|": "\\",
            ":": ";",
            '"': "'",
            "<": ",",
            ">": ".",
            "?": "/",
            "~": "`",
        }
        for char in text:
            if char in special:
                self.tap_key(special[char])
            elif char == " ":
                self.tap_key("space")
            elif char.lower() in KEY_CODES:
                self.tap_key(char.lower(), modifier="left_shift" if char.isupper() else None)
            elif char in shifted:
                self.tap_key(shifted[char], modifier="left_shift")
            else:
                raise ValueError(f"Unsupported character for Windows input: {char!r}")
            if char_delay_s > 0:
                sampled_delay_s = self._timing_sampler.sample_typing_delay(char_delay_s)
                self._sleeper(sampled_delay_s)

    def current_target(self) -> InputTargetState:
        return self._target

    def set_foreground_target(self) -> InputTargetState:
        self._target = InputTargetState(platform="windows", mode="foreground")
        return self._target

    def set_pid_target(self, pid: int) -> InputTargetState:
        if pid <= 0:
            raise ValueError("pid must be a positive integer")
        self._target = InputTargetState(platform="windows", mode="pid", pid=pid)
        return self._target

    def set_hwnd_target(self, hwnd: int) -> InputTargetState:
        if hwnd <= 0:
            raise ValueError("hwnd must be a positive integer")
        self._target = InputTargetState(platform="windows", mode="hwnd", hwnd=hwnd)
        return self._target

    def auto_target(
        self,
        process_name: str = DEFAULT_AUTO_TARGET_PROCESS_NAME,
        *,
        prefer: str = "pid",
    ) -> InputTargetState:
        pid = self._pid_finder(process_name)
        if pid is None:
            raise RuntimeError(f"No process matched {process_name!r}.")
        if prefer == "hwnd":
            hwnd = self._pid_window_finder(pid)
            if hwnd is None:
                raise RuntimeError(f"No top-level window matched pid {pid}.")
            self._target = InputTargetState(
                platform="windows",
                mode="hwnd",
                hwnd=hwnd,
                pid=pid,
                process_name=process_name,
            )
            return self._target
        self._target = InputTargetState(
            platform="windows",
            mode="pid",
            pid=pid,
            process_name=process_name,
        )
        return self._target

    def _dispatch_scan_code(self, scan_code: int, down: bool) -> None:
        target = self._target
        if target.mode == "foreground":
            self._sender(scan_code, down)
            return
        if target.mode == "hwnd":
            if target.hwnd is None:
                raise RuntimeError("HWND-targeted input requires a window handle.")
            self._window_sender(target.hwnd, scan_code, down)
            return
        if target.mode == "pid":
            if target.pid is None:
                raise RuntimeError("PID-targeted input requires a process id.")
            hwnd = self._pid_window_finder(target.pid)
            if hwnd is None:
                raise RuntimeError(f"No top-level window matched pid {target.pid}.")
            self._window_sender(hwnd, scan_code, down)
            return
        raise RuntimeError(f"Unsupported input target mode: {target.mode}")

    def _resolve(self, key: str, modifier: str | None) -> tuple[int, int | None]:
        normalized = key.lower()
        if normalized not in KEY_CODES:
            raise ValueError(f"Unsupported key: {key}")

        mod_keycode = None
        if modifier is not None:
            normalized_mod = modifier.lower()
            mod_keycode = MODIFIER_KEYCODES.get(normalized_mod)
            if mod_keycode is None:
                raise ValueError(f"Unsupported modifier: {modifier}")

        return KEY_CODES[normalized], mod_keycode
