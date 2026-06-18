from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from edap.binding_lookup import BindingLookup, load_binding_lookup
from edap.config import AppConfig, DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG_PATH, load_config

if TYPE_CHECKING:
    from edap.platform.input.base import InputController
    from edap.platform.paths.base import GamePaths
    from edap.platform.screen.base import ScreenCapture


@dataclass(frozen=True)
class LoadedConfig:
    config: AppConfig
    config_path: str
    used_example_config_fallback: bool


@dataclass(frozen=True)
class ResolvedPath:
    configured: dict[str, object]
    auto_detected: dict[str, object]
    effective: dict[str, object]

    @property
    def effective_path(self) -> Path | None:
        path = self.effective.get("path")
        return Path(path) if isinstance(path, str) and path else None

    def cli_source_status(self) -> str:
        configured_status = self.configured.get("status")
        effective_status = self.effective.get("status")
        effective_source = self.effective.get("source")

        if configured_status == "ok":
            return "configured"
        if configured_status == "missing":
            return "configured_missing"
        if configured_status == "invalid":
            return "configured_invalid"
        if effective_status == "ok" and effective_source == "auto_detected":
            return "auto_detected"
        if self.auto_detected.get("status") == "unsupported":
            return "unsupported_platform"
        return "auto_detect_not_found"


@dataclass(frozen=True)
class RuntimeContext:
    config: AppConfig
    game_paths: GamePaths | None
    journal: ResolvedPath
    bindings: ResolvedPath
    input_controller: InputController | None
    screen_capture: ScreenCapture | None
    binding_lookup: BindingLookup | None = None
    config_path: Path = DEFAULT_CONFIG_PATH
    used_example_config_fallback: bool = False


def build_game_paths(platform_name: str) -> GamePaths | None:
    from edap.platform.paths.factory import build_game_paths as _build_game_paths

    return _build_game_paths(platform_name)


def build_input_controller(platform_name: str) -> InputController | None:
    from edap.platform.input.factory import build_input_controller as _build_input_controller

    return _build_input_controller(platform_name)


def build_screen_capture(platform_name: str) -> ScreenCapture | None:
    from edap.platform.screen.factory import build_screen_capture as _build_screen_capture

    return _build_screen_capture(platform_name)


def load_config_with_fallback(path: Path | str = DEFAULT_CONFIG_PATH) -> LoadedConfig:
    config_path = str(path)
    try:
        config = load_config(config_path)
        return LoadedConfig(
            config=config,
            config_path=config_path,
            used_example_config_fallback=False,
        )
    except FileNotFoundError:
        if config_path == str(DEFAULT_CONFIG_PATH) and EXAMPLE_CONFIG_PATH.exists():
            fallback_path = str(EXAMPLE_CONFIG_PATH)
            return LoadedConfig(
                config=load_config(fallback_path),
                config_path=fallback_path,
                used_example_config_fallback=True,
            )
        raise


def build_runtime_context(
    config: AppConfig,
    *,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    used_example_config_fallback: bool = False,
    actions: Iterable[str] | None = None,
    include_screen_capture: bool = False,
) -> RuntimeContext:
    game_paths = build_game_paths(config.runtime.platform)
    journal = resolve_journal_path(config, game_paths=game_paths)
    bindings = resolve_bindings_path(config, game_paths=game_paths)

    binding_lookup = None
    effective_bindings_path = bindings.effective_path
    if actions is not None and effective_bindings_path is not None and effective_bindings_path.exists():
        binding_lookup = load_binding_lookup(effective_bindings_path, actions=list(actions))

    return RuntimeContext(
        config=config,
        config_path=Path(config_path),
        used_example_config_fallback=used_example_config_fallback,
        game_paths=game_paths,
        journal=journal,
        bindings=bindings,
        input_controller=build_input_controller(config.runtime.platform),
        screen_capture=build_screen_capture(config.runtime.platform) if include_screen_capture else None,
        binding_lookup=binding_lookup,
    )


def resolve_journal_path(config: AppConfig, *, game_paths: GamePaths | None = None) -> ResolvedPath:
    game_paths = game_paths if game_paths is not None else build_game_paths(config.runtime.platform)
    configured = _configured_path_report(config.paths.journal_dir, kind="journal directory")
    auto_detected = _autodetected_path_report(game_paths, kind="journal")
    effective = _effective_path_report(configured, auto_detected)
    return ResolvedPath(configured=configured, auto_detected=auto_detected, effective=effective)


def resolve_bindings_path(config: AppConfig, *, game_paths: GamePaths | None = None) -> ResolvedPath:
    game_paths = game_paths if game_paths is not None else build_game_paths(config.runtime.platform)
    configured = _configured_path_report(config.paths.bindings_file, kind="bindings file")
    auto_detected = _autodetected_path_report(game_paths, kind="bindings")
    effective = _effective_path_report(configured, auto_detected)
    return ResolvedPath(configured=configured, auto_detected=auto_detected, effective=effective)


def legacy_path_summary(path: ResolvedPath) -> dict[str, object]:
    return {
        "configured": path.configured.get("path"),
        "configured_status": path.configured.get("status"),
        "auto_detected": path.auto_detected.get("selected_path", path.auto_detected.get("path")),
        "auto_detected_status": path.auto_detected.get("status"),
        "effective": path.effective.get("path"),
        "effective_status": path.effective.get("status"),
    }


def _configured_path_report(path: Path | None, *, kind: str) -> dict[str, object]:
    if path is None:
        return {
            "path": None,
            "status": "not_configured",
            "reason": f"no explicit {kind} configured",
        }

    if not path.exists():
        return {
            "path": str(path),
            "status": "missing",
            "reason": f"configured {kind} path does not exist",
        }

    if kind == "journal directory" and not path.is_dir():
        return {
            "path": str(path),
            "status": "invalid",
            "reason": "configured journal path exists but is not a directory",
        }

    if kind == "bindings file" and not path.is_file():
        return {
            "path": str(path),
            "status": "invalid",
            "reason": "configured bindings path exists but is not a file",
        }

    return {
        "path": str(path),
        "status": "ok",
        "reason": f"using configured {kind}",
    }


def _autodetected_path_report(game_paths: GamePaths | None, *, kind: str) -> dict[str, Any]:
    describe_name = "describe_journal_discovery" if kind == "journal" else "describe_bindings_discovery"
    if game_paths is not None and hasattr(game_paths, describe_name):
        report = getattr(game_paths, describe_name)()
        return dict(report)

    detected_path = None
    if game_paths is not None:
        detected_path = (
            game_paths.default_journal_dir() if kind == "journal" else game_paths.default_bindings_file()
        )

    if detected_path is None:
        return {
            "path": None,
            "status": "unsupported",
            "reason": "platform backend did not provide auto-detection details",
        }

    return {
        "path": str(detected_path),
        "status": "ok",
        "reason": "auto-detected default path",
    }


def _effective_path_report(
    configured: dict[str, object],
    auto_detected: dict[str, object],
) -> dict[str, object]:
    if configured["status"] == "ok":
        return {
            "path": configured["path"],
            "status": "ok",
            "source": "configured",
            "reason": configured["reason"],
        }

    auto_detected_path = auto_detected.get("selected_path", auto_detected.get("path"))
    auto_detected_status = auto_detected.get("status", "unsupported")
    if auto_detected_status == "ok" and auto_detected_path:
        return {
            "path": auto_detected_path,
            "status": "ok",
            "source": "auto_detected",
            "reason": auto_detected.get("reason", "auto-detected default path"),
        }

    if configured["status"] in {"missing", "invalid"}:
        return {
            "path": configured["path"],
            "status": configured["status"],
            "source": "configured",
            "reason": configured["reason"],
        }

    return {
        "path": None,
        "status": auto_detected_status,
        "source": "auto_detected",
        "reason": auto_detected.get("reason", "no path available"),
    }
