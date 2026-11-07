from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep

from edap.bindings import read_bindings
from edap.capture import build_capture_layout
from edap.config import AppConfig
from edap.runtime import RuntimeContext, build_runtime_context, legacy_path_summary
from edap.state import get_latest_journal_log, read_ship_state


@dataclass(frozen=True)
class DiagnosticsOptions:
    capture_screen: bool = False
    send_test_key: bool = False
    test_key: str = "space"
    test_modifier: str | None = None
    hold_s: float = 0.0
    delay_s: float = 0.0
    repeat: int = 1


def run_diagnostics(config: AppConfig, options: DiagnosticsOptions) -> dict[str, object]:
    runtime = build_runtime_context(config, include_screen_capture=options.capture_screen)
    try:
        effective_journal_dir = runtime.journal.effective_path
        effective_bindings_file = runtime.bindings.effective_path

        result: dict[str, object] = {
            "platform": config.runtime.platform,
            "debug": config.runtime.debug,
            "controls": {
                "start_hotkey": config.controls.start_hotkey,
                "stop_hotkey": config.controls.stop_hotkey,
                "scanner_mode": config.controls.scanner_mode,
                "minimum_action_hold_seconds": config.controls.minimum_action_hold_seconds,
                "continuous_action_hold_seconds": config.controls.continuous_action_hold_seconds,
            },
            "paths": {
                "journal": {
                    "configured": runtime.journal.configured,
                    "auto_detected": runtime.journal.auto_detected,
                    "effective": runtime.journal.effective,
                },
                "bindings": {
                    "configured": runtime.bindings.configured,
                    "auto_detected": runtime.bindings.auto_detected,
                    "effective": runtime.bindings.effective,
                },
                "legacy_summary": {
                    "journal": legacy_path_summary(runtime.journal),
                    "bindings": legacy_path_summary(runtime.bindings),
                },
            },
            "options": asdict(options),
            "capture_layout": build_capture_layout(config.screen).to_dict(),
        }

        if effective_journal_dir and effective_journal_dir.exists():
            latest_log = get_latest_journal_log(effective_journal_dir)
            result["latest_log"] = str(latest_log) if latest_log else None
            if latest_log:
                ship_state = read_ship_state(latest_log)
                result["ship_state"] = ship_state.to_dict()

        if effective_bindings_file and effective_bindings_file.exists():
            try:
                bindings, missing = read_bindings(effective_bindings_file)
            except Exception as exc:
                result["bindings_result"] = {
                    "status": "error",
                    "path": str(effective_bindings_file),
                    "error": str(exc),
                }
            else:
                result["bindings_result"] = {
                    "status": "ok",
                    "path": str(effective_bindings_file),
                    "resolved_count": len(bindings),
                    "missing_count": len(missing),
                }
                result["bindings"] = {name: binding.to_dict() for name, binding in sorted(bindings.items())}
                result["missing_bindings"] = missing
        else:
            result["bindings_result"] = {
                "status": "not_available",
                "path": str(effective_bindings_file) if effective_bindings_file else None,
                "reason": runtime.bindings.effective["reason"],
            }

        if options.capture_screen:
            result["screen_capture"] = run_screen_capture_diagnostic(config, runtime)

        if options.send_test_key:
            result["input_test"] = run_input_diagnostic(config, options, runtime)

        if runtime.input_controller is not None:
            try:
                result["input_status"] = runtime.input_controller.input_status()
            except (RuntimeError, OSError) as exc:
                result["input_status"] = {"status": "error", "error": str(exc)}
        return result
    finally:
        if runtime.input_controller is not None:
            runtime.input_controller.close()


def run_screen_capture_diagnostic(config: AppConfig, runtime: RuntimeContext | None = None) -> dict[str, object]:
    runtime = runtime or build_runtime_context(config, include_screen_capture=True)
    if runtime.screen_capture is None:
        runtime = build_runtime_context(config, include_screen_capture=True)
    screen_capture = runtime.screen_capture
    if screen_capture is None:
        return {"status": "unsupported"}

    capture_layout = build_capture_layout(config.screen)
    base_bounds = capture_layout.base_bounds
    image = screen_capture.capture_region(
        base_bounds.left,
        base_bounds.top,
        base_bounds.right,
        base_bounds.bottom,
    )

    output_path = config.screen.capture_debug_path
    saved_path = None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        saved_path = str(output_path)

    return {
        "status": "ok",
        "mode": capture_layout.mode,
        "reference_width": capture_layout.reference_width,
        "reference_height": capture_layout.reference_height,
        "captured_bounds": base_bounds.to_dict(),
        "width": getattr(image, "width", base_bounds.width),
        "height": getattr(image, "height", base_bounds.height),
        "saved_path": saved_path,
    }


def run_input_diagnostic(
    config: AppConfig,
    options: DiagnosticsOptions,
    runtime: RuntimeContext | None = None,
) -> dict[str, object]:
    try:
        runtime = runtime or build_runtime_context(config)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    input_controller = runtime.input_controller
    if input_controller is None:
        return {"status": "unsupported"}

    try:
        if options.delay_s > 0:
            sleep(options.delay_s)
        for _ in range(max(1, options.repeat)):
            input_controller.tap_key(
                options.test_key,
                modifier=options.test_modifier,
                hold_s=options.hold_s,
            )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    return {
        "status": "ok",
        "test_key": options.test_key,
        "test_modifier": options.test_modifier,
        "hold_s": options.hold_s,
        "delay_s": options.delay_s,
        "repeat": options.repeat,
    }
