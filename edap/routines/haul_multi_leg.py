from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from edap.actions import ActionDispatchResult
from edap.multi_leg_haul import CargoTransfer, MultiLegHaulDefinition, RouteStop, build_route_stops
from edap.routines._base import RoutineResult
from edap.routines.haul_support import (
    HaulRuntime,
    read_cargo_json,
    sellable_cargo,
)
from edap.routines.market import market_buy, market_sell
from edap.routines.transit import (
    depart_system_to_route,
    is_manual_landing_result,
    read_market_station,
    read_ship_position,
    transit_to_station,
    undock_and_route_to_system,
    wait_for_arrival_or_approach_event,
)
from edap.tts import AnnouncementId


class Phase(Enum):
    SELL = auto()
    BUY = auto()
    UNDOCK = auto()
    DEPART_SYSTEM = auto()
    TRANSIT = auto()
    COMPLETE = auto()


@dataclass
class _Ctx:
    runtime: HaulRuntime
    definition: MultiLegHaulDefinition
    stops: tuple[RouteStop, ...]


_read_cargo_json = read_cargo_json
_read_market_station = read_market_station
_wait_for_arrival_or_approach_event = wait_for_arrival_or_approach_event


def _inventory_count(inventory: list[dict], commodity: str) -> int:
    total = 0
    commodity_lower = commodity.lower()
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        if (
            str(item.get("Name", "")).lower() == commodity_lower
            or str(item.get("Name_Localised", "")).lower() == commodity_lower
        ):
            total += int(count)
    return total


def _has_all_cargo(inventory: list[dict], cargo: tuple[CargoTransfer, ...]) -> bool:
    if not cargo:
        return True
    return all(_inventory_count(inventory, item.commodity) >= item.amount for item in cargo)


def _has_any_cargo(inventory: list[dict], cargo: tuple[CargoTransfer, ...]) -> bool:
    return any(_inventory_count(inventory, item.commodity) > 0 for item in cargo)


def _read_ship_position(journal_dir: Path) -> tuple[str, str, str]:
    position = read_ship_position(journal_dir)
    return position.status, position.station, position.system


def _detect_start_state(ctx: _Ctx) -> tuple[int, Phase]:
    runtime = ctx.runtime
    inventory = _read_cargo_json(runtime.journal_dir)
    ship_status, current_station, current_system = _read_ship_position(runtime.journal_dir)
    current_station_lower = current_station.lower()
    current_system_lower = current_system.lower()

    runtime.progress_fn(
        "Multi-leg phase detect: "
        f"status={ship_status}, station={current_station!r}, system={current_system!r}"
    )

    for stop in ctx.stops:
        if stop.endpoint.station and current_station_lower == stop.endpoint.station.lower():
            if _has_any_cargo(inventory, stop.inbound):
                return stop.index, Phase.SELL
            if stop.outbound and _has_all_cargo(inventory, stop.outbound):
                return stop.index, Phase.UNDOCK
            if stop.outbound:
                return stop.index, Phase.BUY
            return stop.index, Phase.COMPLETE

    for leg in ctx.definition.legs:
        if _has_all_cargo(inventory, leg.cargo):
            source_index = leg.index - 1
            if current_system_lower and current_system_lower == leg.source.system.lower():
                return source_index, Phase.DEPART_SYSTEM if ship_status == "normal_space" else Phase.UNDOCK
            return source_index, Phase.TRANSIT

    return 0, Phase.BUY if ctx.stops and ctx.stops[0].outbound else Phase.COMPLETE


def _run_sell(ctx: _Ctx, stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    if not stop.inbound or not sellable_cargo(_read_cargo_json(runtime.journal_dir)):
        return RoutineResult(action="market_sell", dispatch=ActionDispatchResult(action="market_sell", status="ok", reason="nothing to sell"))
    for cargo in stop.inbound:
        available = _inventory_count(_read_cargo_json(runtime.journal_dir), cargo.commodity)
        if available <= 0:
            runtime.progress_fn(f"{cargo.commodity} already absent at {stop.label} - skipping sell.")
            continue
        runtime.progress_fn(f"Selling {cargo.amount}t {cargo.commodity} at {stop.label}...")
        runtime.announce_fn(AnnouncementId.SELLING_CARGO, commodity_name=cargo.commodity)
        result = market_sell(
            runtime.controls,
            runtime.watcher,
            market_path=runtime.market_path,
            target=cargo.commodity,
            amount=str(min(available, cargo.amount)),
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
            return result
        if runtime.timing.post_sell_settle_s > 0:
            runtime.sleeper(runtime.timing.post_sell_settle_s)
    return RoutineResult(action="market_sell", dispatch=ActionDispatchResult(action="market_sell", status="ok"))


def _run_buy(ctx: _Ctx, stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    if not stop.outbound:
        return RoutineResult(action="market_buy", dispatch=ActionDispatchResult(action="market_buy", status="ok", reason="no outbound cargo"))
    for cargo in stop.outbound:
        already_loaded = _inventory_count(_read_cargo_json(runtime.journal_dir), cargo.commodity)
        remaining = max(0, cargo.amount - already_loaded)
        if remaining <= 0:
            runtime.progress_fn(f"{cargo.commodity} already loaded for departure from {stop.label} - skipping buy.")
            continue
        runtime.progress_fn(f"Buying {remaining}t {cargo.commodity} at {stop.label}...")
        runtime.announce_fn(AnnouncementId.BUYING_CARGO, commodity_name=cargo.commodity)
        result = market_buy(
            runtime.controls,
            runtime.watcher,
            market_path=runtime.market_path,
            target=cargo.commodity,
            amount=str(remaining),
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
        if result.dispatch.status != "ok":
            return result
    return RoutineResult(action="market_buy", dispatch=ActionDispatchResult(action="market_buy", status="ok"))


def _undock_and_route(ctx: _Ctx, stop: RouteStop, next_stop: RouteStop) -> RoutineResult:
    return undock_and_route_to_system(
        ctx.runtime,
        current_label=stop.label,
        current_system=stop.endpoint.system,
        destination_system=next_stop.endpoint.system,
        routine_name="multi-leg haul",
    )


def _depart_system(ctx: _Ctx, stop: RouteStop, next_stop: RouteStop) -> RoutineResult:
    return depart_system_to_route(
        ctx.runtime,
        current_label=stop.label,
        current_system=stop.endpoint.system,
        destination_system=next_stop.endpoint.system,
        routine_name="multi-leg haul",
    )


def _run_transit(ctx: _Ctx, next_stop: RouteStop) -> RoutineResult:
    return transit_to_station(
        ctx.runtime,
        destination=next_stop.endpoint,
        destination_label=next_stop.label,
        routine_name="multi-leg haul",
    )


def multi_leg_haul(
    runtime: HaulRuntime,
    *,
    definition: MultiLegHaulDefinition,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> RoutineResult:
    stops = build_route_stops(definition)
    if not stops:
        raise ValueError("Multi-leg haul definition has no stops")
    ctx = _Ctx(runtime=runtime, definition=definition, stops=stops)

    stop_index, phase = _detect_start_state(ctx)
    if phase != Phase.BUY or stop_index != 0:
        runtime.progress_fn(f"Resuming multi-leg haul from stop {stop_index + 1} phase {phase.name}")
    last_result = RoutineResult(action="multi_leg_haul", dispatch=ActionDispatchResult(action="multi_leg_haul", status="ok"))

    while stop_index < len(stops):
        stop = stops[stop_index]
        next_stop = stops[stop_index + 1] if stop_index + 1 < len(stops) else None
        if phase == Phase.COMPLETE:
            return last_result
        if stop_requested_fn is not None and stop_requested_fn() and phase in {Phase.BUY, Phase.UNDOCK, Phase.DEPART_SYSTEM}:
            runtime.progress_fn(f"Stop requested at {stop.label}; halting before departure.")
            return last_result
        if phase == Phase.SELL:
            last_result = _run_sell(ctx, stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.BUY if stop.outbound else Phase.COMPLETE
            continue
        if phase == Phase.BUY:
            last_result = _run_buy(ctx, stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.UNDOCK if next_stop is not None else Phase.COMPLETE
            continue
        if phase == Phase.UNDOCK:
            if next_stop is None:
                return last_result
            last_result = _undock_and_route(ctx, stop, next_stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.TRANSIT
            continue
        if phase == Phase.DEPART_SYSTEM:
            if next_stop is None:
                return last_result
            last_result = _depart_system(ctx, stop, next_stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.TRANSIT
            continue
        if phase == Phase.TRANSIT:
            if next_stop is None:
                return last_result
            last_result = _run_transit(ctx, next_stop)
            if is_manual_landing_result(last_result):
                return last_result
            if last_result.dispatch.status != "ok":
                return last_result
            stop_index += 1
            phase = Phase.SELL
            continue
    return last_result
