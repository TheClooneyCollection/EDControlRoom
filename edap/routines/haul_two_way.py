from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from edap.actions import ActionDispatchResult
from edap.cargo_manifest import cargo_item_matches_commodity, commodity_name_key
from edap.routines._base import RoutineResult
from edap.routines.callbacks import ProgressCallback
from edap.routines.haul_support import (
    HaulRuntime,
    read_cargo_json,
    read_last_cargo_capacity,
    sellable_cargo,
)
from edap.routines.market import market_buy, market_sell
from edap.routines.transit import (
    depart_system_to_route,
    is_manual_landing_result,
    read_market_station,
    transit_to_station,
    undock_and_route_to_system,
    wait_for_arrival_or_approach_event,
)
from edap.state import get_latest_journal_log, read_ship_state
from edap.status import read_status
from edap.tts import AnnouncementId


_read_cargo_json = read_cargo_json
_read_last_cargo_capacity = read_last_cargo_capacity
_read_market_station = read_market_station
_sellable_cargo = sellable_cargo
_is_manual_landing_result = is_manual_landing_result
_wait_for_arrival_or_approach_event = wait_for_arrival_or_approach_event


def _inventory_has_commodity(inventory: list[dict], commodity: str) -> bool:
    if not commodity:
        return False
    return any(
        item.get("Count", 0) > 0
        and cargo_item_matches_commodity(item, commodity)
        for item in inventory
    )


def _inventory_commodity_count(inventory: list[dict], commodity: str) -> int:
    if not commodity:
        return 0
    total = 0
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        if cargo_item_matches_commodity(item, commodity):
            total += max(0, int(count))
    return total


def _inventory_item_matches(item: dict, commodity: str) -> bool:
    return cargo_item_matches_commodity(item, commodity)


def _inventory_item_display_name(item: dict) -> str:
    return str(item.get("Name_Localised") or item.get("Name") or "unknown commodity")


def _wrong_buy_commodity_from_inventory(inventory: list[dict], expected_commodity: str) -> str:
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)) or count <= 0:
            continue
        if _inventory_item_matches(item, expected_commodity):
            continue
        return _inventory_item_display_name(item)
    return ""


def _unexpected_cargo_before_buy(inventory: list[dict], expected_commodity: str) -> list[str]:
    unexpected: list[str] = []
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)) or count <= 0:
            continue
        if _inventory_item_matches(item, expected_commodity):
            continue
        unexpected.append(f"{int(count)}t {_inventory_item_display_name(item)}")
    return unexpected


def _sellable_cargo_targets(inventory: list[dict]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for item in _sellable_cargo(inventory):
        target = _inventory_item_display_name(item)
        key = commodity_name_key(target)
        if not key or key in seen:
            continue
        targets.append(target)
        seen.add(key)
    return targets


def _inventory_used_capacity(inventory: list[dict]) -> int:
    used = 0
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        used += max(0, int(count))
    return used


def _inventory_has_full_commodity_load(
    inventory: list[dict],
    *,
    commodity: str,
    cargo_capacity: int | None,
) -> bool | None:
    if not commodity:
        return False
    if cargo_capacity is None or cargo_capacity <= 0:
        return None
    commodity_count = _inventory_commodity_count(inventory, commodity)
    used_capacity = _inventory_used_capacity(inventory)
    return commodity_count >= cargo_capacity and used_capacity == commodity_count


def _status_cargo_count(journal_dir: Path) -> int | None:
    try:
        status = read_status(journal_dir)
    except Exception:
        return None
    if status is None or status.cargo is None:
        return None
    return int(status.cargo)


def _stale_cargo_state_before_buy(journal_dir: Path) -> int | None:
    status_count = _status_cargo_count(journal_dir)
    if status_count is None or status_count <= 0:
        return None
    if _sellable_cargo(_read_cargo_json(journal_dir)):
        return None
    return status_count


class Phase(Enum):
    AT_STATION_1_SELL = auto()
    AT_STATION_1_BUY = auto()
    UNDOCK_STATION_1 = auto()
    DEPART_STATION_1_SYSTEM = auto()
    TRANSIT_TO_STATION_2 = auto()
    AT_STATION_2_SELL = auto()
    AT_STATION_2_BUY = auto()
    UNDOCK_STATION_2 = auto()
    DEPART_STATION_2_SYSTEM = auto()
    TRANSIT_TO_STATION_1 = auto()


@dataclass(frozen=True)
class StationLeg:
    index: int
    station: str
    system: str
    buy_commodity: str
    sell_commodity: str
    on_land: bool = False

    @property
    def label(self) -> str:
        return f"station {self.index} ({self.station})" if self.station else f"station {self.index}"


@dataclass(frozen=True)
class TwoWayHaulRoute:
    station_1: StationLeg
    station_2: StationLeg


@dataclass
class _HaulCtx:
    runtime: HaulRuntime
    station_1: StationLeg
    station_2: StationLeg
    wrong_buy_count: int = 0


def _detect_start_phase(
    journal_dir: Path,
    *,
    station_1: StationLeg,
    station_2: StationLeg,
    progress_fn: ProgressCallback,
) -> Phase | RoutineResult:
    ship_status = "unknown"
    current_station = ""
    current_system = ""
    log_path = get_latest_journal_log(journal_dir)
    if log_path is not None:
        try:
            state = read_ship_state(log_path)
        except Exception:
            state = None
        if state is not None:
            current_station = str(state.station or "")
            current_system = str(state.location or "")
            status = str(state.status or "")
            if status == "in_station":
                ship_status = "docked"
            elif status in {"in_space", "in_undocking", "starting_docking", "in_docking"}:
                ship_status = "normal_space"
            elif status in {"in_supercruise", "starting_hyperspace", "starting_supercruise"}:
                ship_status = "supercruise"

    inventory = _read_cargo_json(journal_dir)
    has_station_1_cargo = _inventory_has_commodity(inventory, station_1.buy_commodity)
    has_station_2_cargo = _inventory_has_commodity(inventory, station_2.buy_commodity)
    cargo_capacity = _read_last_cargo_capacity(journal_dir)
    has_full_station_1_cargo = _inventory_has_full_commodity_load(
        inventory,
        commodity=station_1.buy_commodity,
        cargo_capacity=cargo_capacity,
    )
    has_full_station_2_cargo = _inventory_has_full_commodity_load(
        inventory,
        commodity=station_2.buy_commodity,
        cargo_capacity=cargo_capacity,
    )
    market_station, market_system = _read_market_station(journal_dir)

    if ship_status in {"docked", "unknown"}:
        if not current_station and market_station:
            current_station = market_station
        if not current_system and market_system:
            current_system = market_system
        if current_station:
            ship_status = "docked"

    progress_fn(
        "Two-way phase detect: "
        f"status={ship_status}, station={current_station!r}, system={current_system!r}, "
        f"has_station_1_cargo={has_station_1_cargo}, has_station_2_cargo={has_station_2_cargo}, "
        f"full_station_1_cargo={has_full_station_1_cargo}, full_station_2_cargo={has_full_station_2_cargo}"
    )

    if ship_status == "unknown":
        return Phase.AT_STATION_1_SELL

    current_station_lower = current_station.lower()
    station_1_lower = station_1.station.lower()
    station_2_lower = station_2.station.lower()
    current_system_lower = current_system.lower()
    station_1_system_lower = station_1.system.lower()
    station_2_system_lower = station_2.system.lower()

    if ship_status == "docked":
        if current_station_lower == station_1_lower:
            if has_station_2_cargo:
                return Phase.AT_STATION_1_SELL
            if has_full_station_1_cargo:
                return Phase.UNDOCK_STATION_1
            if not station_1.buy_commodity:
                return Phase.UNDOCK_STATION_1
            return Phase.AT_STATION_1_BUY
        if current_station_lower == station_2_lower:
            if has_station_1_cargo:
                return Phase.AT_STATION_2_SELL
            if has_full_station_2_cargo:
                return Phase.UNDOCK_STATION_2
            if not station_2.buy_commodity:
                return Phase.UNDOCK_STATION_2
            return Phase.AT_STATION_2_BUY
        return _error_routine_result(
            f"Docked at unknown station {current_station!r}, expected {station_1.station!r} or {station_2.station!r}"
        )

    if current_system_lower and station_1_system_lower and current_system_lower == station_1_system_lower:
        if has_station_2_cargo:
            return Phase.TRANSIT_TO_STATION_1
        if has_full_station_1_cargo and ship_status == "normal_space":
            return Phase.DEPART_STATION_1_SYSTEM
        if ship_status == "normal_space":
            return Phase.DEPART_STATION_1_SYSTEM
        if not has_station_1_cargo and station_1.buy_commodity:
            return Phase.TRANSIT_TO_STATION_1
        return Phase.TRANSIT_TO_STATION_2

    if current_system_lower and station_2_system_lower and current_system_lower == station_2_system_lower:
        if has_station_1_cargo:
            return Phase.TRANSIT_TO_STATION_2
        if has_full_station_2_cargo and ship_status == "normal_space":
            return Phase.DEPART_STATION_2_SYSTEM
        if ship_status == "normal_space":
            return Phase.DEPART_STATION_2_SYSTEM
        if not has_station_2_cargo and station_2.buy_commodity:
            return Phase.TRANSIT_TO_STATION_2
        return Phase.TRANSIT_TO_STATION_1

    if has_station_1_cargo:
        return Phase.TRANSIT_TO_STATION_2
    if has_station_2_cargo:
        return Phase.TRANSIT_TO_STATION_1
    return Phase.AT_STATION_1_SELL


def _run_market_sell(
    ctx: _HaulCtx,
    *,
    leg: StationLeg,
    next_phase: Phase,
) -> tuple[RoutineResult, Phase]:
    runtime = ctx.runtime
    if not leg.sell_commodity:
        runtime.progress_fn(f"No sell commodity configured for {leg.label} - skipping sell.")
        return (
            RoutineResult(
                action="market_sell",
                dispatch=ActionDispatchResult(
                    action="market_sell",
                    status="ok",
                    reason="no sell commodity configured",
                ),
            ),
            next_phase,
        )
    if not _sellable_cargo(_read_cargo_json(runtime.journal_dir)):
        runtime.progress_fn(f"Cargo hold empty - skipping {leg.label} sell.")
        return (
            RoutineResult(
                action="market_sell",
                dispatch=ActionDispatchResult(
                    action="market_sell",
                    status="ok",
                    reason="cargo hold empty",
                ),
            ),
            next_phase,
        )
    runtime.progress_fn(f"Selling {leg.sell_commodity} at {leg.label} (MAX)...")
    runtime.announce_fn(AnnouncementId.SELLING_CARGO, commodity_name=leg.sell_commodity)
    result = market_sell(
        runtime.controls,
        runtime.watcher,
        market_path=runtime.market_path,
        target=leg.sell_commodity,
        amount="MAX",
        step_delay_s=runtime.timing.step_delay_s,
        max_hold_s=runtime.timing.max_hold_s,
        buy_hold_segments=runtime.market.buy_hold_segments,
        sell_quantity_restore_taps=runtime.market.sell_quantity_restore_taps,
        sell_quantity_restore_tap_delay_s=runtime.market.sell_quantity_restore_tap_delay_s,
        trade_timeout_s=runtime.timing.trade_timeout_s,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
        announce_fn=runtime.announce_fn,
        critical_level_multiplier=runtime.market.critical_level_multiplier,
    )
    if result.dispatch.status != "ok":
        return result, next_phase
    # market_sell finishes with UI_Back x2, which returns us to the station
    # services menu. The next phase (buy) immediately presses UI_Select to
    # re-enter station services, and that select can land on stale UI if the
    # menu has not finished redrawing. Settle here, on the sell side, because
    # the gap exists only when we just came out of the menu - resume paths
    # that drop straight into AT_STATION_*_BUY do not need it.
    if runtime.timing.post_sell_settle_s > 0:
        runtime.sleeper(runtime.timing.post_sell_settle_s)
    return result, next_phase


def _run_market_buy(
    ctx: _HaulCtx,
    *,
    leg: StationLeg,
    next_phase: Phase,
) -> tuple[RoutineResult, Phase]:
    runtime = ctx.runtime
    if not leg.buy_commodity:
        runtime.progress_fn(f"No buy commodity configured for {leg.label} - skipping buy.")
        return (
            RoutineResult(
                action="market_buy",
                dispatch=ActionDispatchResult(
                    action="market_buy",
                    status="ok",
                    reason="no buy commodity configured",
                ),
            ),
            next_phase,
        )
    starting_inventory = _read_cargo_json(runtime.journal_dir)
    unexpected_cargo = _unexpected_cargo_before_buy(starting_inventory, leg.buy_commodity)
    if unexpected_cargo:
        sell_result = _sell_all_cargo_before_buy(
            ctx,
            leg=leg,
            inventory=starting_inventory,
            cargo_summary=unexpected_cargo,
        )
        if sell_result.dispatch.status != "ok":
            return sell_result, next_phase
        remaining_unexpected_cargo = _unexpected_cargo_before_buy(
            _read_cargo_json(runtime.journal_dir),
            leg.buy_commodity,
        )
        if remaining_unexpected_cargo:
            reason = (
                f"Cannot buy {leg.buy_commodity} at {leg.label}: cargo hold still contains "
                f"non-haul cargo ({', '.join(remaining_unexpected_cargo)}) after sell-all recovery. "
                "Clear or sell that cargo manually, then resume haul."
            )
            runtime.progress_fn(f"Error: {reason}")
            runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
            return _error_routine_result(reason), next_phase
        runtime.progress_fn("Unrelated cargo sold; retrying intended buy.")
    stale_cargo_count = _stale_cargo_state_before_buy(runtime.journal_dir)
    if stale_cargo_count is not None:
        reason = (
            f"Cannot buy {leg.buy_commodity} at {leg.label}: the cargo hold already reports "
            f"{stale_cargo_count}t loaded, but Elite did not report what cargo it is. "
            "Cargo data may be stale; relog or reopen the cargo/market screen, then resume haul."
        )
        runtime.progress_fn(f"Error: {reason}")
        runtime.announce_fn(AnnouncementId.HAUL_CARGO_STATE_STALE, cargo_count=stale_cargo_count)
        return _error_routine_result(reason), next_phase
    while True:
        runtime.progress_fn(f"Buying {leg.buy_commodity} at {leg.label} (MAX)...")
        runtime.announce_fn(AnnouncementId.BUYING_CARGO, commodity_name=leg.buy_commodity)
        result = market_buy(
            runtime.controls,
            runtime.watcher,
            market_path=runtime.market_path,
            target=leg.buy_commodity,
            amount="MAX",
            step_delay_s=runtime.timing.step_delay_s,
            max_hold_s=runtime.timing.max_hold_s,
            buy_hold_segments=runtime.market.buy_hold_segments,
            trade_timeout_s=runtime.timing.trade_timeout_s,
            time_fn=runtime.time_fn,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
            announce_fn=runtime.announce_fn,
            critical_level_multiplier=runtime.market.critical_level_multiplier,
        )
        wrong_commodity = _wrong_buy_commodity_after_buy(runtime.journal_dir, leg.buy_commodity, result)
        if not wrong_commodity:
            if result.dispatch.status != "ok":
                return result, next_phase
            return result, next_phase

        ctx.wrong_buy_count += 1
        runtime.progress_fn(
            f"Wrong cargo bought at {leg.label}: {wrong_commodity!r}; "
            f"expected {leg.buy_commodity!r}. Selling wrong cargo "
            f"(mistake {ctx.wrong_buy_count}/2)."
        )
        sell_result = _sell_wrong_buy_cargo(ctx, wrong_commodity)
        if sell_result.dispatch.status != "ok":
            return sell_result, next_phase
        if ctx.wrong_buy_count >= 2:
            reason = (
                "Wrong cargo bought twice during haul buy recovery; "
                f"last wrong cargo {wrong_commodity!r}, expected {leg.buy_commodity!r}."
            )
            runtime.progress_fn(f"Error: {reason}")
            runtime.announce_fn(AnnouncementId.HAUL_WRONG_CARGO_ABORTED)
            return _error_routine_result(reason), next_phase
        runtime.progress_fn("Wrong cargo sold; retrying intended buy.")


def _sell_all_cargo_before_buy(
    ctx: _HaulCtx,
    *,
    leg: StationLeg,
    inventory: list[dict],
    cargo_summary: list[str],
) -> RoutineResult:
    runtime = ctx.runtime
    targets = _sellable_cargo_targets(inventory)
    if not targets:
        reason = (
            f"Cannot buy {leg.buy_commodity} at {leg.label}: cargo hold already contains "
            f"non-haul cargo ({', '.join(cargo_summary)}), but none of it can be sold automatically. "
            "Clear that cargo manually, then resume haul."
        )
        runtime.progress_fn(f"Error: {reason}")
        runtime.announce_fn(
            AnnouncementId.HAUL_UNRELATED_CARGO_LOADED,
            cargo_summary=", ".join(cargo_summary),
        )
        runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
        return _error_routine_result(reason)

    runtime.progress_fn(
        f"Cargo hold contains non-haul cargo before buying {leg.buy_commodity} at {leg.label}: "
        f"{', '.join(cargo_summary)}. Selling all sellable cargo before retrying."
    )
    runtime.announce_fn(
        AnnouncementId.HAUL_UNRELATED_CARGO_LOADED,
        cargo_summary=", ".join(cargo_summary),
    )
    runtime.announce_fn(AnnouncementId.SELLING_ALL_CARGO)
    for target in targets:
        runtime.progress_fn(f"Selling cargo before buy recovery: {target} (MAX)...")
        result = _sell_cargo_target(ctx, target)
        if result.dispatch.status != "ok":
            return result
        if runtime.timing.post_sell_settle_s > 0:
            runtime.sleeper(runtime.timing.post_sell_settle_s)
    return RoutineResult(
        action="market_sell",
        dispatch=ActionDispatchResult(
            action="market_sell",
            status="ok",
            reason="sold cargo before buy recovery",
        ),
    )


def _wrong_buy_commodity_after_buy(
    journal_dir: Path,
    expected_commodity: str,
    result: RoutineResult,
) -> str:
    inventory_wrong_commodity = _wrong_buy_commodity_from_inventory(
        _read_cargo_json(journal_dir),
        expected_commodity,
    )
    if inventory_wrong_commodity:
        return inventory_wrong_commodity
    if (result.details or {}).get("phase") != "wrong_item":
        return ""
    wrong_commodity = str((result.details or {}).get("wrong_commodity", "")).strip()
    if wrong_commodity and commodity_name_key(wrong_commodity) != commodity_name_key(expected_commodity):
        return wrong_commodity
    return ""


def _sell_wrong_buy_cargo(ctx: _HaulCtx, wrong_commodity: str) -> RoutineResult:
    ctx.runtime.announce_fn(AnnouncementId.SELLING_CARGO, commodity_name=wrong_commodity)
    return _sell_cargo_target(ctx, wrong_commodity)


def _sell_cargo_target(ctx: _HaulCtx, target: str) -> RoutineResult:
    runtime = ctx.runtime
    return market_sell(
        runtime.controls,
        runtime.watcher,
        market_path=runtime.market_path,
        target=target,
        amount="MAX",
        step_delay_s=runtime.timing.step_delay_s,
        max_hold_s=runtime.timing.max_hold_s,
        buy_hold_segments=runtime.market.buy_hold_segments,
        sell_quantity_restore_taps=runtime.market.sell_quantity_restore_taps,
        sell_quantity_restore_tap_delay_s=runtime.market.sell_quantity_restore_tap_delay_s,
        trade_timeout_s=runtime.timing.trade_timeout_s,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
        announce_fn=runtime.announce_fn,
        critical_level_multiplier=runtime.market.critical_level_multiplier,
    )


def _should_stop_before_station_1_buy(
    phase: Phase,
    stop_requested_fn: Callable[[], bool] | None,
) -> bool:
    return phase == Phase.AT_STATION_1_BUY and stop_requested_fn is not None and stop_requested_fn()


def _stopped_routine_result(reason: str) -> RoutineResult:
    return RoutineResult(
        action="haul_loop",
        dispatch=ActionDispatchResult(
            action="haul_loop",
            status="ok",
            reason=reason,
        ),
    )


def _error_routine_result(reason: str) -> RoutineResult:
    return RoutineResult(
        action="haul_loop",
        dispatch=ActionDispatchResult(
            action="haul_loop",
            status="error",
            reason=reason,
        ),
    )


def _undock_and_route(
    ctx: _HaulCtx,
    *,
    current_leg: StationLeg,
    destination_system: str,
    next_phase: Phase,
) -> tuple[RoutineResult, Phase]:
    return (
        undock_and_route_to_system(
            ctx.runtime,
            current_label=current_leg.label,
            current_system=current_leg.system,
            destination_system=destination_system,
            routine_name="haul",
        ),
        next_phase,
    )


def _depart_system(
    ctx: _HaulCtx,
    *,
    current_leg: StationLeg,
    destination_system: str,
    next_phase: Phase,
) -> tuple[RoutineResult | None, Phase]:
    return (
        depart_system_to_route(
            ctx.runtime,
            current_label=current_leg.label,
            current_system=current_leg.system,
            destination_system=destination_system,
            routine_name="haul",
        ),
        next_phase,
    )


def _run_transit(
    ctx: _HaulCtx,
    *,
    destination_leg: StationLeg,
    next_phase: Phase,
) -> tuple[RoutineResult, Phase]:
    return (
        transit_to_station(
            ctx.runtime,
            destination=destination_leg,
            destination_label=destination_leg.label,
            routine_name="haul",
        ),
        next_phase,
    )


def _run_station_1_sell(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_market_sell(ctx, leg=ctx.station_1, next_phase=Phase.AT_STATION_1_BUY)


def _run_station_1_buy(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_market_buy(ctx, leg=ctx.station_1, next_phase=Phase.UNDOCK_STATION_1)


def _run_undock_station_1(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _undock_and_route(
        ctx,
        current_leg=ctx.station_1,
        destination_system=ctx.station_2.system,
        next_phase=Phase.TRANSIT_TO_STATION_2,
    )


def _run_depart_station_1_system(ctx: _HaulCtx) -> tuple[RoutineResult | None, Phase]:
    return _depart_system(
        ctx,
        current_leg=ctx.station_1,
        destination_system=ctx.station_2.system,
        next_phase=Phase.TRANSIT_TO_STATION_2,
    )


def _run_transit_to_station_2(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_transit(ctx, destination_leg=ctx.station_2, next_phase=Phase.AT_STATION_2_SELL)


def _run_station_2_sell(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_market_sell(ctx, leg=ctx.station_2, next_phase=Phase.AT_STATION_2_BUY)


def _run_station_2_buy(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_market_buy(ctx, leg=ctx.station_2, next_phase=Phase.UNDOCK_STATION_2)


def _run_undock_station_2(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _undock_and_route(
        ctx,
        current_leg=ctx.station_2,
        destination_system=ctx.station_1.system,
        next_phase=Phase.TRANSIT_TO_STATION_1,
    )


def _run_depart_station_2_system(ctx: _HaulCtx) -> tuple[RoutineResult | None, Phase]:
    return _depart_system(
        ctx,
        current_leg=ctx.station_2,
        destination_system=ctx.station_1.system,
        next_phase=Phase.TRANSIT_TO_STATION_1,
    )


def _run_transit_to_station_1(ctx: _HaulCtx) -> tuple[RoutineResult, Phase]:
    return _run_transit(ctx, destination_leg=ctx.station_1, next_phase=Phase.AT_STATION_1_SELL)


_PHASE_RUNNERS: dict[Phase, Callable[[_HaulCtx], tuple[RoutineResult | None, Phase]]] = {
    Phase.AT_STATION_1_SELL: _run_station_1_sell,
    Phase.AT_STATION_1_BUY: _run_station_1_buy,
    Phase.UNDOCK_STATION_1: _run_undock_station_1,
    Phase.DEPART_STATION_1_SYSTEM: _run_depart_station_1_system,
    Phase.TRANSIT_TO_STATION_2: _run_transit_to_station_2,
    Phase.AT_STATION_2_SELL: _run_station_2_sell,
    Phase.AT_STATION_2_BUY: _run_station_2_buy,
    Phase.UNDOCK_STATION_2: _run_undock_station_2,
    Phase.DEPART_STATION_2_SYSTEM: _run_depart_station_2_system,
    Phase.TRANSIT_TO_STATION_1: _run_transit_to_station_1,
}


def haul_loop_two_way(
    runtime: HaulRuntime,
    *,
    route: TwoWayHaulRoute,
    iterations: int = 0,
    start_phase: Phase | None = None,
    stop_requested_fn: Callable[[], bool] | None = None,
    pause_requested_fn: Callable[[], bool] | None = None,
    pause_fn: Callable[[Phase], None] | None = None,
    phase_updated_fn: Callable[[Phase], None] | None = None,
) -> RoutineResult:
    if iterations < 0:
        raise ValueError("iterations must be non-negative (0 = infinite)")
    if not route.station_1.station or not route.station_2.station:
        raise RuntimeError("station_1 and station_2 are required")
    if not route.station_1.buy_commodity and not route.station_2.buy_commodity:
        raise RuntimeError("at least one of station_1_buying or station_2_buying is required")
    if route.station_1.station == route.station_2.station:
        raise RuntimeError("station_1 and station_2 must differ")
    if (
        route.station_1.buy_commodity
        and route.station_2.buy_commodity
        and route.station_1.buy_commodity == route.station_2.buy_commodity
    ):
        raise RuntimeError("station_1_buying and station_2_buying must differ")

    ctx = _HaulCtx(
        runtime=runtime,
        station_1=route.station_1,
        station_2=route.station_2,
    )

    resolved_start_phase = start_phase or _detect_start_phase(
        runtime.journal_dir,
        station_1=ctx.station_1,
        station_2=ctx.station_2,
        progress_fn=runtime.progress_fn,
    )
    if resolved_start_phase != Phase.AT_STATION_1_SELL:
        runtime.progress_fn(f"Resuming from phase: {resolved_start_phase.name}")

    last_result: RoutineResult | None = None
    iteration = 0
    first_cycle = True
    while iterations == 0 or iteration < iterations:
        iteration += 1
        iter_label = f" of {iterations}" if iterations > 0 else ""
        runtime.progress_fn(f"=== Two-way haul iteration {iteration}{iter_label} ===")
        phase = resolved_start_phase if first_cycle else Phase.AT_STATION_1_SELL
        first_cycle = False

        while True:
            if phase_updated_fn is not None:
                phase_updated_fn(phase)
            if (
                phase in {Phase.AT_STATION_1_BUY, Phase.AT_STATION_2_BUY}
                and pause_requested_fn is not None
                and pause_requested_fn()
            ):
                station_index = 1 if phase == Phase.AT_STATION_1_BUY else 2
                runtime.progress_fn(f"Pause requested at station {station_index}; waiting for resume.")
                if pause_fn is not None:
                    pause_fn(phase)
            if _should_stop_before_station_1_buy(phase, stop_requested_fn):
                runtime.progress_fn("Stop requested at station 1; halting before station 1 buy.")
                return last_result or _stopped_routine_result("stopped before station 1 buy")
            result, next_phase = _PHASE_RUNNERS[phase](ctx)
            if result is not None:
                last_result = result
                if _is_manual_landing_result(result):
                    return result
                if result.dispatch.status != "ok":
                    return result
            if (
                phase == Phase.AT_STATION_1_SELL
                and stop_requested_fn is not None
                and stop_requested_fn()
            ):
                runtime.progress_fn("Stop requested at cycle boundary; halting before station 1 buy.")
                return last_result or _stopped_routine_result("stopped at station 1 cycle boundary")
            if phase == Phase.TRANSIT_TO_STATION_1:
                break
            phase = next_phase

        runtime.progress_fn(f"Iteration {iteration} complete.")

    assert last_result is not None
    return last_result
